from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.modeling import load_artifact, save_artifact, train_artifact


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MODEL = ROOT / "artifacts" / "return_risk_model.joblib"


@pytest.fixture(scope="session")
def artifact():
    if not MODEL.exists():
        save_artifact(train_artifact(RAW), MODEL)
    return load_artifact(MODEL)


@pytest.fixture()
def order_record() -> dict[str, object]:
    row = pd.read_csv(RAW / "test_unlabelled.csv").iloc[0].to_dict()
    for key, value in list(row.items()):
        if pd.isna(value):
            row[key] = None
    row["delivery_pincode"] = str(int(float(row["delivery_pincode"]))).zfill(6)
    return row
