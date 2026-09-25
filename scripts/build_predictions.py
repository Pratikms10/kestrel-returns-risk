"""Create predictions.csv in the supplied sample order and schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from app.modeling import canonical_orders, load_artifact


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--model", type=Path, default=ROOT / "artifacts" / "return_risk_model.joblib")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "predictions.csv")
    args = parser.parse_args()

    artifact = load_artifact(args.model)
    raw_test = pd.read_csv(args.raw_dir / "test_unlabelled.csv")
    test = canonical_orders(raw_test)
    sample = pd.read_csv(args.raw_dir / "sample_submission.csv")
    if list(sample.columns) != ["order_id", "score"]:
        raise ValueError("Unexpected sample_submission.csv columns")
    if sample.order_id.duplicated().any() or test.order_id.duplicated().any():
        raise ValueError("Duplicate order_id remained after canonicalization")
    if set(sample.order_id) != set(test.order_id):
        raise ValueError("Test order IDs do not exactly match the sample submission")

    scores, _, _ = artifact.score(test)
    scored = pd.DataFrame({"order_id": test.order_id, "score": scores})
    submission = sample[["order_id"]].merge(scored, on="order_id", how="left", validate="one_to_one")
    if submission.score.isna().any() or not submission.score.between(0, 1).all():
        raise ValueError("Submission contains a missing or out-of-range score")
    submission["score"] = submission.score.round(8)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    submission.to_csv(args.output, index=False, lineterminator="\n")

    known_customers = set(artifact.customers.customer_id.astype(str))
    known_skus = set(artifact.products.sku.astype(str))
    labelled = canonical_orders(pd.read_csv(args.raw_dir / "train.csv"))
    training_customers = set(labelled.customer_id.astype(str))
    summary = {
        "rows": int(len(submission)),
        "unique_order_ids": int(submission.order_id.nunique()),
        "minimum_score": float(submission.score.min()),
        "mean_score": float(submission.score.mean()),
        "maximum_score": float(submission.score.max()),
        "orders_at_or_above_action_threshold": int((submission.score >= artifact.threshold).sum()),
        "action_rate": float((submission.score >= artifact.threshold).mean()),
        "missing_customer_reference_rate": float((~test.customer_id.astype(str).isin(known_customers)).mean()),
        "missing_sku_reference_rate": float((~test.sku.astype(str).isin(known_skus)).mean()),
        "customer_not_seen_in_training_rate": float(
            (~test.customer_id.astype(str).isin(training_customers)).mean()
        ),
        "model_version": artifact.metadata["model_version"],
        "paid_inference_cost_inr": 0.0,
    }
    summary_path = args.output.with_name("predictions_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Saved {len(submission)} predictions: {args.output}")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
