"""Reproduce model selection, the untouched temporal holdout, and risk controls."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline

from app.modeling import (
    ACTION_THRESHOLD,
    CALL_COST_INR,
    CALL_EFFECTIVENESS,
    RETURN_COST_INR,
    build_estimator,
    build_transformer,
    canonical_orders,
    engineer_features,
)


ROOT = Path(__file__).resolve().parents[1]


def candidate_models() -> dict[str, Pipeline]:
    candidates = {f"logistic_C{c}": build_estimator(c) for c in (0.05, 0.1, 0.3, 1.0)}
    candidates["hist_gradient_boosting"] = Pipeline(
        [
            ("features", build_transformer(dense=True)),
            (
                "model",
                HistGradientBoostingClassifier(
                    learning_rate=0.05,
                    max_iter=250,
                    max_leaf_nodes=15,
                    min_samples_leaf=40,
                    l2_regularization=1.0,
                    random_state=42,
                ),
            ),
        ]
    )
    candidates["extra_trees"] = Pipeline(
        [
            ("features", build_transformer()),
            (
                "model",
                ExtraTreesClassifier(
                    n_estimators=350,
                    max_features=0.7,
                    min_samples_leaf=15,
                    n_jobs=-1,
                    random_state=42,
                ),
            ),
        ]
    )
    return candidates


def probability_metrics(y_true: pd.Series, scores: np.ndarray) -> dict[str, float]:
    return {
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "average_precision": float(average_precision_score(y_true, scores)),
        "brier_score": float(brier_score_loss(y_true, scores)),
        "log_loss": float(log_loss(y_true, scores)),
    }


def bootstrap_auc_interval(y_true: np.ndarray, scores: np.ndarray, repeats: int = 500) -> list[float]:
    rng = np.random.default_rng(42)
    values: list[float] = []
    for _ in range(repeats):
        sample = rng.integers(0, len(y_true), len(y_true))
        sampled_y = y_true[sample]
        if np.unique(sampled_y).size == 2:
            values.append(float(roc_auc_score(sampled_y, scores[sample])))
    return [float(value) for value in np.quantile(values, [0.025, 0.975])]


def threshold_metrics(y_true: pd.Series, scores: np.ndarray, threshold: float) -> dict[str, Any]:
    actual = y_true.to_numpy(dtype=int)
    predicted = scores >= threshold
    tn, fp, fn, tp = confusion_matrix(actual, predicted, labels=[0, 1]).ravel()
    calls = int(predicted.sum())
    gross_avoided = float(tp * CALL_EFFECTIVENESS * RETURN_COST_INR)
    call_cost = float(calls * CALL_COST_INR)
    return {
        "threshold": threshold,
        "flagged_orders": calls,
        "flagged_rate": float(predicted.mean()),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_negatives": int(tn),
        "precision": float(precision_score(actual, predicted, zero_division=0)),
        "recall": float(recall_score(actual, predicted, zero_division=0)),
        "accuracy": float(accuracy_score(actual, predicted)),
        "call_cost_inr": call_cost,
        "gross_avoided_return_cost_inr": gross_avoided,
        "estimated_net_benefit_inr": gross_avoided - call_cost,
    }


def calibration_metrics(y_true: pd.Series, scores: np.ndarray) -> dict[str, Any]:
    scored = pd.DataFrame({"actual": y_true.to_numpy(dtype=int), "score": scores})
    scored["bucket"] = pd.qcut(scored.score, 10, labels=False, duplicates="drop")
    buckets = (
        scored.groupby("bucket", observed=True)
        .agg(
            orders=("actual", "size"),
            minimum_score=("score", "min"),
            maximum_score=("score", "max"),
            mean_predicted_risk=("score", "mean"),
            observed_return_rate=("actual", "mean"),
        )
        .reset_index()
    )
    buckets["absolute_gap"] = (
        buckets.mean_predicted_risk - buckets.observed_return_rate
    ).abs()
    expected_calibration_error = float(
        (buckets.orders / len(scored) * buckets.absolute_gap).sum()
    )
    flagged = scored.score.ge(ACTION_THRESHOLD)
    return {
        "overall_mean_predicted_risk": float(scored.score.mean()),
        "overall_observed_return_rate": float(scored.actual.mean()),
        "flagged_mean_predicted_risk": float(scored.loc[flagged, "score"].mean()),
        "flagged_observed_return_rate": float(scored.loc[flagged, "actual"].mean()),
        "unflagged_mean_predicted_risk": float(scored.loc[~flagged, "score"].mean()),
        "unflagged_observed_return_rate": float(scored.loc[~flagged, "actual"].mean()),
        "quantile_expected_calibration_error": expected_calibration_error,
        "deciles": buckets.to_dict("records"),
    }


def slice_metrics(holdout: pd.DataFrame, scores: np.ndarray, column: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scored = holdout.assign(_score=scores)
    for value, segment in scored.groupby(column, dropna=False):
        y = segment.returned.astype(int)
        predicted = segment._score.to_numpy() >= ACTION_THRESHOLD
        result: dict[str, Any] = {
            "value": str(value),
            "orders": int(len(segment)),
            "return_rate": float(y.mean()),
            "average_score": float(segment._score.mean()),
            "recall": float(recall_score(y, predicted, zero_division=0)),
            "precision": float(precision_score(y, predicted, zero_division=0)),
        }
        if y.nunique() == 2:
            result["roc_auc"] = float(roc_auc_score(y, segment._score))
        rows.append(result)
    return sorted(rows, key=lambda row: row["orders"], reverse=True)


def leaky_probe_auc(
    development: pd.DataFrame,
    holdout: pd.DataFrame,
    engineered_development: pd.DataFrame,
    engineered_holdout: pd.DataFrame,
) -> float:
    """Quantify why post-outcome service fields were discarded."""
    train = engineered_development.copy()
    valid = engineered_holdout.copy()
    for target, raw in ((train, development), (valid, holdout)):
        target["pickup_present_LEAK"] = raw.pickup_scheduled_at.fillna("").ne("").astype(int).to_numpy()
        target["service_reverse_pickup_LEAK"] = raw.last_service_event_type.eq("REVERSE_PICKUP").astype(int).to_numpy()
    transformer = build_transformer()
    from app.modeling import NUMERIC_FEATURES

    original_numeric = list(NUMERIC_FEATURES)
    # This separate local transformer makes the leakage demonstration explicit;
    # the production feature list remains unchanged.
    transformer.transformers[0] = (
        "num",
        transformer.transformers[0][1],
        original_numeric + ["pickup_present_LEAK", "service_reverse_pickup_LEAK"],
    )
    estimator = Pipeline(
        [
            ("features", transformer),
            ("model", LogisticRegression(C=0.05, max_iter=2000, random_state=42)),
        ]
    )
    estimator.fit(train, development.returned)
    return float(roc_auc_score(holdout.returned, estimator.predict_proba(valid)[:, 1]))


def data_audit(raw: pd.DataFrame, customers: pd.DataFrame, products: pd.DataFrame) -> dict[str, Any]:
    canonical = canonical_orders(raw)
    placed = pd.to_datetime(canonical.order_placed_at)
    october = canonical[placed.dt.to_period("M") == pd.Period("2025-10")].merge(
        products[["sku", "list_price_inr"]], on="sku", how="left", validate="many_to_one"
    )
    expected = october.list_price_inr * october.qty * (1 - october.discount_pct / 100)
    ratio = october.order_value_inr / expected
    joined = canonical.merge(
        customers[["customer_id", "signup_date"]], on="customer_id", how="left", validate="many_to_one"
    )
    future_signup = pd.to_datetime(joined.signup_date) > pd.to_datetime(joined.order_placed_at)
    return {
        "raw_rows": int(len(raw)),
        "canonical_orders": int(len(canonical)),
        "duplicate_rows_removed": int(len(raw) - len(canonical)),
        "return_rate": float(canonical.returned.mean()),
        "all_non_return_accuracy": float(1 - canonical.returned.mean()),
        "october_2025_orders": int(len(october)),
        "october_raw_value_ratio_median": float(ratio.median()),
        "signup_after_order_rows": int(future_signup.sum()),
        "reverse_pickup_rows": int(canonical.last_service_event_type.eq("REVERSE_PICKUP").sum()),
        "reverse_pickup_return_rate": float(
            canonical.loc[canonical.last_service_event_type.eq("REVERSE_PICKUP"), "returned"].mean()
        ),
    }


def evaluate(raw_dir: Path) -> dict[str, Any]:
    raw = pd.read_csv(raw_dir / "train.csv")
    orders = canonical_orders(raw)
    customers = pd.read_csv(raw_dir / "customers.csv")
    products = pd.read_csv(raw_dir / "products.csv")
    engineered, _ = engineer_features(orders, customers, products)
    placed = pd.to_datetime(orders.order_placed_at)

    folds = [
        ("2025_q4", placed < "2025-10-01", placed.between("2025-10-01", "2025-12-31 23:59:59")),
        ("2026_q1", placed < "2026-01-01", placed.between("2026-01-01", "2026-03-31 23:59:59")),
    ]
    candidate_rows: list[dict[str, Any]] = []
    for name, candidate in candidate_models().items():
        for fold_name, train_mask, valid_mask in folds:
            estimator = clone(candidate)
            estimator.fit(engineered.loc[train_mask], orders.loc[train_mask, "returned"])
            scores = estimator.predict_proba(engineered.loc[valid_mask])[:, 1]
            candidate_rows.append(
                {
                    "candidate": name,
                    "fold": fold_name,
                    "train_orders": int(train_mask.sum()),
                    "validation_orders": int(valid_mask.sum()),
                    **probability_metrics(orders.loc[valid_mask, "returned"], scores),
                }
            )

    candidate_frame = pd.DataFrame(candidate_rows)
    averages = (
        candidate_frame.groupby("candidate")[["roc_auc", "average_precision", "brier_score", "log_loss"]]
        .mean()
        .sort_values("roc_auc", ascending=False)
        .reset_index()
    )
    selected = str(averages.iloc[0].candidate)
    if selected != "logistic_C0.05":
        raise RuntimeError(f"Selection drifted to {selected}; review before updating the production model.")

    development_mask = placed < "2026-04-01"
    holdout_mask = placed >= "2026-04-01"
    development = orders.loc[development_mask].reset_index(drop=True)
    holdout = orders.loc[holdout_mask].reset_index(drop=True)
    engineered_development = engineered.loc[development_mask].reset_index(drop=True)
    engineered_holdout = engineered.loc[holdout_mask].reset_index(drop=True)
    final_estimator = build_estimator(0.05)
    final_estimator.fit(engineered_development, development.returned)

    started = time.perf_counter()
    scores = final_estimator.predict_proba(engineered_holdout)[:, 1]
    batch_latency_ms = (time.perf_counter() - started) * 1000
    metrics = probability_metrics(holdout.returned, scores)
    metrics["roc_auc_95pct_bootstrap_interval"] = bootstrap_auc_interval(
        holdout.returned.to_numpy(dtype=int), scores
    )

    top_count = math.ceil(len(holdout) * 0.10)
    top_indices = np.argsort(scores)[::-1][:top_count]
    top_capture = float(holdout.returned.to_numpy()[top_indices].sum() / holdout.returned.sum())
    top_fraction = top_count / len(holdout)
    decision = threshold_metrics(holdout.returned, scores, ACTION_THRESHOLD)
    scale = 700 / len(holdout)
    monthly = {
        "orders": 700,
        "estimated_calls": decision["flagged_orders"] * scale,
        "estimated_call_cost_inr": decision["call_cost_inr"] * scale,
        "estimated_returns_in_called_queue": decision["true_positives"] * scale,
        "estimated_returns_prevented": decision["true_positives"] * CALL_EFFECTIVENESS * scale,
        "estimated_gross_avoided_return_cost_inr": decision["gross_avoided_return_cost_inr"] * scale,
        "estimated_net_benefit_inr": decision["estimated_net_benefit_inr"] * scale,
        "paid_model_cost_inr": 0.0,
    }

    return {
        "evaluation_design": {
            "selection_folds": ["2025 Q4", "2026 Q1"],
            "untouched_holdout": "2026-04-01 through 2026-06-30",
            "holdout_orders": int(len(holdout)),
            "holdout_returns": int(holdout.returned.sum()),
            "holdout_return_rate": float(holdout.returned.mean()),
            "selected_model": selected,
            "threshold_selected_before_holdout": ACTION_THRESHOLD,
            "policy_breakeven_probability": CALL_COST_INR / (CALL_EFFECTIVENESS * RETURN_COST_INR),
        },
        "data_audit": data_audit(raw, customers, products),
        "candidate_fold_results": candidate_rows,
        "candidate_average_results": averages.to_dict("records"),
        "holdout_probability_metrics": metrics,
        "holdout_calibration": calibration_metrics(holdout.returned, scores),
        "holdout_operating_point": decision,
        "top_decile": {
            "orders": top_count,
            "order_fraction": top_fraction,
            "return_capture": top_capture,
            "lift_over_random": top_capture / top_fraction,
        },
        "monthly_backtest_projection": monthly,
        "slices": {
            "shield_member": slice_metrics(engineered_holdout.assign(returned=holdout.returned), scores, "shield_member"),
            "payment_mode": slice_metrics(engineered_holdout.assign(returned=holdout.returned), scores, "payment_mode"),
            "family": slice_metrics(engineered_holdout.assign(returned=holdout.returned), scores, "family"),
        },
        "leakage_probe": {
            "holdout_roc_auc_with_post_outcome_fields": leaky_probe_auc(
                development,
                holdout,
                engineered_development,
                engineered_holdout,
            ),
            "decision": "Rejected: service and pickup fields are populated after dispatch/return.",
        },
        "performance": {
            "holdout_batch_latency_ms": batch_latency_ms,
            "holdout_latency_ms_per_order": batch_latency_ms / len(holdout),
            "paid_inference_cost_inr_per_order": 0.0,
        },
        "limitations": [
            "The 35% call effectiveness figure is a historical pilot estimate, not a randomized causal estimate.",
            "Customer history counters are not monotonic for every repeated customer and require upstream repair.",
            "Shield status is a current customer snapshot rather than a guaranteed as-of-order value.",
            "The hidden test labels are unavailable, so hidden-set performance remains an estimate.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "evaluation_metrics.json")
    args = parser.parse_args()
    result = evaluate(args.raw_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
