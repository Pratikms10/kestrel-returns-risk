"""Leakage-safe feature engineering, training, scoring, and explanations."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


MODEL_VERSION = "kestrel-logistic-2026-09-25-v1"
ACTION_THRESHOLD = 0.15
RETURN_COST_INR = 1150.0
CALL_COST_INR = 45.0
CALL_EFFECTIVENESS = 0.35

UNSAFE_COLUMNS = ("last_service_event_type", "pickup_scheduled_at", "source")

NUMERIC_FEATURES = [
    "discount_pct",
    "qty",
    "promised_delivery_days",
    "customer_prior_orders",
    "customer_prior_returns",
    "prior_return_rate",
    "prior_return_any",
    "log_expected_order_value",
    "warranty_months",
    "product_age_days",
    "note_present",
    "note_length",
    "default_pincode",
    "order_hour_sin",
    "order_hour_cos",
    "order_month_sin",
    "order_month_cos",
]

CATEGORICAL_FEATURES = [
    "sku",
    "family",
    "sales_channel",
    "payment_mode",
    "is_gift",
    "shield_member",
    "city",
    "state",
    "pincode_prefix",
    "order_weekday",
]


def _has_value(value: Any) -> bool:
    """Return True for a real supplied value, including zero, but not NaN."""
    return bool(pd.notna(value) and str(value).strip() != "")


def load_orders(raw_dir: Path, labelled: bool = True) -> pd.DataFrame:
    filename = "train.csv" if labelled else "test_unlabelled.csv"
    return pd.read_csv(raw_dir / filename)


def canonical_orders(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep one canonical CRM row per order before any split or training."""
    if "source" not in frame:
        return frame.drop_duplicates("order_id").copy()
    ranked = frame.assign(_source_rank=frame.source.ne("crm").astype(int))
    return (
        ranked.sort_values(["order_id", "_source_rank"], kind="stable")
        .drop_duplicates("order_id", keep="first")
        .drop(columns="_source_rank")
        .reset_index(drop=True)
    )


def build_transformer(*, dense: bool = False) -> ColumnTransformer:
    numeric = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            (
                "encode",
                OneHotEncoder(
                    handle_unknown="ignore",
                    min_frequency=5,
                    sparse_output=not dense,
                ),
            ),
        ]
    )
    return ColumnTransformer(
        [
            ("num", numeric, NUMERIC_FEATURES),
            ("cat", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
        sparse_threshold=0 if dense else 0.3,
    )


def build_estimator(c_value: float = 0.05) -> Pipeline:
    return Pipeline(
        [
            ("features", build_transformer()),
            ("model", LogisticRegression(C=c_value, max_iter=2000, random_state=42)),
        ]
    )


def engineer_features(
    orders: pd.DataFrame,
    customers: pd.DataFrame,
    products: pd.DataFrame,
) -> tuple[pd.DataFrame, list[list[str]]]:
    """Create only fields that exist before dispatch.

    Raw payment values are deliberately ignored because every October 2025 row
    is 100x wrong. Service/pickup/source columns are deliberately absent.
    """
    frame = orders.copy()
    customer_fields = customers[["customer_id", "city", "state", "shield_member"]].copy()
    product_fields = products[
        ["sku", "family", "list_price_inr", "warranty_months", "launch_date"]
    ].copy()
    known_customers = set(customer_fields.customer_id.astype(str))
    known_products = set(product_fields.sku.astype(str))

    warnings: list[list[str]] = []
    for row in frame.to_dict("records"):
        row_warnings: list[str] = []
        if str(row.get("customer_id")) not in known_customers:
            row_warnings.append("Customer was not found in the supplied reference file; neutral defaults were used.")
        if str(row.get("sku")) not in known_products:
            row_warnings.append("SKU was not found in the supplied product file; fallback product values were used.")
        service_event = row.get("last_service_event_type")
        if _has_value(row.get("pickup_scheduled_at")) or (
            _has_value(service_event) and str(service_event) not in {"NONE", "INSTALL_BOOKED"}
        ):
            row_warnings.append("Post-dispatch service and pickup fields were ignored by design.")
        warnings.append(row_warnings)

    frame["customer_id"] = frame.customer_id.astype(str)
    frame["sku"] = frame.sku.astype(str)
    frame = frame.merge(customer_fields, on="customer_id", how="left", validate="many_to_one")
    frame = frame.merge(product_fields, on="sku", how="left", validate="many_to_one")

    placed = pd.to_datetime(frame.order_placed_at, errors="coerce")
    launched = pd.to_datetime(frame.launch_date, errors="coerce")
    median_price = float(products.list_price_inr.median())
    frame["list_price_inr"] = frame.list_price_inr.fillna(median_price)
    frame["warranty_months"] = frame.warranty_months.fillna(products.warranty_months.median())
    frame["family"] = frame.family.fillna("Unknown")
    frame["shield_member"] = frame.shield_member.fillna("N")
    frame["city"] = frame.city.fillna("Unknown")
    frame["state"] = frame.state.fillna("Unknown")

    expected_value = frame.list_price_inr * frame.qty * (1 - frame.discount_pct / 100)
    frame["prior_return_rate"] = frame.customer_prior_returns / frame.customer_prior_orders.clip(lower=1)
    frame["prior_return_any"] = frame.customer_prior_returns.gt(0).astype(int)
    frame["log_expected_order_value"] = np.log1p(expected_value.clip(lower=0))
    frame["product_age_days"] = (placed.dt.normalize() - launched).dt.days.clip(lower=0).fillna(0)
    frame["delivery_note"] = frame.get("delivery_note", pd.Series(index=frame.index, dtype=object)).fillna("")
    frame["note_present"] = frame.delivery_note.ne("").astype(int)
    frame["note_length"] = frame.delivery_note.str.len().clip(upper=200)
    pincode = frame.delivery_pincode.fillna(0).astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    frame["default_pincode"] = pincode.eq("000000").astype(int)
    frame["pincode_prefix"] = pincode.str[:3]
    frame["order_weekday"] = placed.dt.day_name().fillna("Unknown")
    hour = placed.dt.hour.fillna(0)
    month = placed.dt.month.fillna(1)
    frame["order_hour_sin"] = np.sin(2 * np.pi * hour / 24)
    frame["order_hour_cos"] = np.cos(2 * np.pi * hour / 24)
    frame["order_month_sin"] = np.sin(2 * np.pi * month / 12)
    frame["order_month_cos"] = np.cos(2 * np.pi * month / 12)
    frame["placed_at"] = placed
    return frame, warnings


@dataclass
class RiskArtifact:
    pipeline: Pipeline
    customers: pd.DataFrame
    products: pd.DataFrame
    metadata: dict[str, Any]

    @property
    def threshold(self) -> float:
        return float(self.metadata["action_threshold"])

    def prepare(self, orders: pd.DataFrame) -> tuple[pd.DataFrame, list[list[str]]]:
        return engineer_features(orders, self.customers, self.products)

    def score(self, orders: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame, list[list[str]]]:
        engineered, warnings = self.prepare(orders)
        scores = self.pipeline.predict_proba(engineered)[:, 1]
        return scores, engineered, warnings

    def reasons(self, engineered_row: pd.DataFrame, limit: int = 3) -> list[str]:
        transformer = self.pipeline.named_steps["features"]
        model = self.pipeline.named_steps["model"]
        transformed = transformer.transform(engineered_row)
        vector = transformed.toarray()[0] if hasattr(transformed, "toarray") else np.asarray(transformed)[0]
        names = transformer.get_feature_names_out()
        contributions = dict(zip(names, vector * model.coef_[0], strict=True))

        def total(prefixes: Iterable[str]) -> float:
            return float(
                sum(value for name, value in contributions.items() if any(prefix in name for prefix in prefixes))
            )

        row = engineered_row.iloc[0]
        groups: list[tuple[float, str, str]] = []
        prior_returns = int(row.customer_prior_returns)
        prior_orders = int(row.customer_prior_orders)
        groups.append(
            (
                total(("customer_prior_", "prior_return_")),
                f"Customer has {prior_returns} return(s) across {prior_orders} previous order(s)."
                if prior_returns
                else "No previous customer returns lowered the estimate.",
                "Customer order history is the largest model signal.",
            )
        )
        payment = str(row.payment_mode)
        groups.append(
            (
                total(("payment_mode_",)),
                "Cash-on-delivery orders returned more often in the training period."
                if payment == "cod"
                else f"The {payment.replace('_', ' ')} payment pattern affected the estimate.",
                "This payment mode was associated with lower historical return risk.",
            )
        )
        shield = str(row.shield_member)
        groups.append(
            (
                total(("shield_member_",)),
                "Shield members returned more often historically; use a service-oriented call, not an extended hold."
                if shield == "Y"
                else "Non-Shield membership lowered the estimate.",
                "Non-Shield membership lowered the estimate.",
            )
        )
        family = str(row.family)
        groups.append(
            (
                total(("family_", "sku_", "log_expected_order_value", "warranty_months")),
                f"{family} orders were a stronger historical return segment.",
                f"{family} orders were a lower-risk historical segment.",
            )
        )
        promise = int(row.promised_delivery_days)
        groups.append(
            (
                total(("promised_delivery_days", "default_pincode", "pincode_prefix_", "city_", "state_")),
                f"The {promise}-day delivery promise and address completeness raised the estimate.",
                f"The {promise}-day delivery promise and address completeness lowered the estimate.",
            )
        )
        gift = str(row.is_gift) == "Y"
        discount = float(row.discount_pct)
        groups.append(
            (
                total(("discount_pct", "is_gift_", "sales_channel_", "qty")),
                "Gift status and checkout terms raised the estimate."
                if gift
                else f"Checkout terms, including a {discount:.0f}% discount, raised the estimate.",
                "Checkout terms lowered the estimate.",
            )
        )

        positive = sorted((group for group in groups if group[0] > 0), key=lambda item: item[0], reverse=True)
        negative = sorted((group for group in groups if group[0] <= 0), key=lambda item: item[0])
        result = [group[1] for group in positive[:limit]]
        for group in negative:
            if len(result) >= limit:
                break
            result.append(group[2])
        return result[:limit]


def train_artifact(raw_dir: Path) -> RiskArtifact:
    raw = canonical_orders(load_orders(raw_dir, labelled=True))
    customers = pd.read_csv(raw_dir / "customers.csv")
    products = pd.read_csv(raw_dir / "products.csv")
    engineered, _ = engineer_features(raw, customers, products)
    pipeline = build_estimator(c_value=0.05)
    pipeline.fit(engineered, raw.returned)
    metadata = {
        "model_version": MODEL_VERSION,
        "action_threshold": ACTION_THRESHOLD,
        "training_orders": int(len(raw)),
        "training_return_rate": float(raw.returned.mean()),
        "training_through": str(pd.to_datetime(raw.order_placed_at).max()),
        "return_cost_inr": RETURN_COST_INR,
        "call_cost_inr": CALL_COST_INR,
        "call_effectiveness": CALL_EFFECTIVENESS,
        "paid_inference_cost_inr": 0.0,
        "excluded_columns": list(UNSAFE_COLUMNS) + ["order_value_inr", "signup_date", "customer_id"],
        "runtime_versions": {
            "python": platform.python_version(),
            "numpy": version("numpy"),
            "pandas": version("pandas"),
            "scikit_learn": version("scikit-learn"),
        },
    }
    return RiskArtifact(pipeline, customers, products, metadata)


def save_artifact(artifact: RiskArtifact, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, path, compress=3)


def load_artifact(path: Path) -> RiskArtifact:
    return joblib.load(path)
