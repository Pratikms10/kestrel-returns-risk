"""Measure local endpoint latency without any network or paid API call."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "service_benchmark.json")
    args = parser.parse_args()
    row = pd.read_csv(ROOT / "data" / "raw" / "test_unlabelled.csv").iloc[0].to_dict()
    row = {key: (None if pd.isna(value) else value) for key, value in row.items()}
    row["delivery_pincode"] = str(int(float(row["delivery_pincode"]))).zfill(6)
    client = TestClient(app)
    warmup = client.post("/predict", json=row)
    warmup.raise_for_status()

    timings: list[float] = []
    for _ in range(args.requests):
        started = time.perf_counter()
        response = client.post("/predict", json=row)
        elapsed = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        timings.append(elapsed)

    result = {
        "requests": args.requests,
        "median_latency_ms": float(np.median(timings)),
        "p95_latency_ms": float(np.quantile(timings, 0.95)),
        "maximum_latency_ms": float(np.max(timings)),
        "paid_inference_cost_inr_per_prediction": 0.0,
        "environment": "local FastAPI TestClient; excludes network transit",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
