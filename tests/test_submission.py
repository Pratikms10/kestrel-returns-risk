from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_predictions_exactly_match_sample_shape() -> None:
    predictions = pd.read_csv(ROOT / "outputs" / "predictions.csv")
    sample = pd.read_csv(ROOT / "data" / "raw" / "sample_submission.csv")
    assert list(predictions.columns) == ["order_id", "score"]
    assert len(predictions) == len(sample)
    assert predictions.order_id.tolist() == sample.order_id.tolist()
    assert predictions.order_id.is_unique
    assert predictions.score.notna().all()
    assert predictions.score.between(0, 1).all()
