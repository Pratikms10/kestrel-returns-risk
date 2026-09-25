"""FastAPI service and local employee screen."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.modeling import CALL_COST_INR, CALL_EFFECTIVENESS, RETURN_COST_INR, RiskArtifact, load_artifact
from app.schemas import Economics, HealthResponse, OrderInput, PredictionResponse


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "artifacts" / "return_risk_model.joblib"
STATIC_DIR = Path(__file__).with_name("static")


def _load_model(path: Path = MODEL_PATH) -> tuple[RiskArtifact | None, str | None]:
    try:
        return load_artifact(path), None
    except Exception as exc:
        return None, f"Model is unavailable ({type(exc).__name__}). Run: python scripts/train.py"


def _event_logger() -> logging.Logger:
    logger = logging.getLogger("kestrel.predictions")
    if logger.handlers:
        return logger
    logger.setLevel(os.getenv("KESTREL_LOG_LEVEL", "INFO"))
    log_path = ROOT / os.getenv("KESTREL_LOG_PATH", "logs/predictions.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


artifact, load_error = _load_model()
event_logger = _event_logger()
app = FastAPI(
    title="Kestrel Returns Risk",
    version="1.0.0",
    description="Offline pre-dispatch return-risk score with readable reasons and call economics.",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    if artifact is None:
        return HealthResponse(status="not_ready", model_version=None, detail=load_error or "Model unavailable")
    return HealthResponse(
        status="ready",
        model_version=str(artifact.metadata["model_version"]),
        detail="Local model loaded; paid inference cost is INR 0.",
    )


@app.post("/predict", response_model=PredictionResponse)
def predict(order: OrderInput) -> PredictionResponse:
    if artifact is None:
        raise HTTPException(status_code=503, detail=load_error or "Model unavailable; run the training command.")
    started = time.perf_counter()
    request_id = str(uuid4())
    frame = pd.DataFrame([order.model_dump(mode="json")])
    scores, engineered, warnings = artifact.score(frame)
    score = float(scores[0])
    action = "same_day_confirmation_call" if score >= artifact.threshold else "dispatch_normally"
    avoided = score * CALL_EFFECTIVENESS * RETURN_COST_INR
    net = avoided - CALL_COST_INR
    guidance = (
        "Complete a service-oriented confirmation call and release within 24 hours; do not use an extended automatic hold."
        if action == "same_day_confirmation_call"
        else "No confirmation call is recommended at this threshold; continue normal dispatch checks."
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    event = {
        "event": "return_risk_prediction",
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "order_hash": hashlib.sha256(order.order_id.encode("utf-8")).hexdigest()[:12],
        "model_version": artifact.metadata["model_version"],
        "score": round(score, 6),
        "action": action,
        "latency_ms": round(elapsed_ms, 3),
        "warning_count": len(warnings[0]),
        "paid_inference_cost_inr": 0.0,
    }
    event_logger.info(json.dumps(event, separators=(",", ":")))
    return PredictionResponse(
        request_id=request_id,
        order_id=order.order_id,
        return_risk=round(score, 6),
        action=action,
        action_threshold=artifact.threshold,
        reasons=artifact.reasons(engineered.iloc[[0]]),
        economics=Economics(
            call_cost_inr=CALL_COST_INR,
            expected_avoided_return_cost_inr=round(avoided, 2),
            expected_net_benefit_inr=round(net, 2),
            assumptions="35% of otherwise occurring returns prevented; INR 1,150 handling cost per return.",
        ),
        guidance=guidance,
        warnings=warnings[0],
        model_version=str(artifact.metadata["model_version"]),
        paid_inference_cost_inr=0.0,
    )
