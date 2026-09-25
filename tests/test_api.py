from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


def test_health_screen_and_prediction(artifact, order_record) -> None:
    from app.main import app

    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ready"
    assert client.get("/").status_code == 200

    response = client.post("/predict", json=order_record)
    assert response.status_code == 200
    body = response.json()
    assert body["order_id"] == order_record["order_id"]
    assert body["action"] in {"same_day_confirmation_call", "dispatch_normally"}
    assert body["reasons"]
    assert body["paid_inference_cost_inr"] == 0


def test_validation_rejects_impossible_history(artifact, order_record) -> None:
    from app.main import app

    bad = dict(order_record)
    bad["customer_prior_orders"] = 1
    bad["customer_prior_returns"] = 2
    response = TestClient(app).post("/predict", json=bad)
    assert response.status_code == 422
    assert "cannot exceed" in response.text


def test_validation_rejects_unknown_fields(artifact, order_record) -> None:
    from app.main import app

    bad = dict(order_record)
    bad["returned"] = 1
    response = TestClient(app).post("/predict", json=bad)
    assert response.status_code == 422
    assert "extra_forbidden" in response.text


def test_missing_model_failure_is_polite(tmp_path: Path) -> None:
    from app.main import _load_model

    model, detail = _load_model(tmp_path / "missing.joblib")
    assert model is None
    assert detail is not None
    assert "Run: python scripts/train.py" in detail


def test_log_excludes_raw_identifiers_and_free_text(artifact, order_record) -> None:
    from app.main import ROOT, app

    record = dict(order_record)
    record["order_id"] = "SECRET-ORDER-ID-FOR-LOG-TEST"
    record["customer_id"] = "SECRET-CUSTOMER-ID-FOR-LOG-TEST"
    record["delivery_note"] = "SECRET DELIVERY INSTRUCTION"
    response = TestClient(app).post("/predict", json=record)
    assert response.status_code == 200
    log_line = (ROOT / "logs" / "predictions.jsonl").read_text(encoding="utf-8").splitlines()[-1]
    event = json.loads(log_line)
    assert event["event"] == "return_risk_prediction"
    assert record["order_id"] not in log_line
    assert record["customer_id"] not in log_line
    assert record["delivery_note"] not in log_line
