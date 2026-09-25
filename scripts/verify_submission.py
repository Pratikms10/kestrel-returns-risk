"""Fail closed if any required deliverable, metric, or package invariant is wrong."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUTPUTS = ROOT / "outputs"
PACKAGE = OUTPUTS / "Kestrel_Home_Task2_CONFIDENTIAL.zip"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_predictions() -> None:
    sample = pd.read_csv(RAW / "sample_submission.csv")
    predictions = pd.read_csv(OUTPUTS / "predictions.csv")
    require(list(predictions.columns) == ["order_id", "score"], "Wrong predictions columns")
    require(predictions.order_id.tolist() == sample.order_id.tolist(), "Order IDs/order differ from sample")
    require(predictions.order_id.is_unique, "Duplicate prediction order_id")
    require(predictions.score.notna().all(), "Missing prediction score")
    require(predictions.score.between(0, 1).all(), "Score outside [0,1]")


def verify_evidence() -> None:
    evidence = json.loads((OUTPUTS / "evaluation_metrics.json").read_text(encoding="utf-8"))
    require(evidence["evaluation_design"]["selected_model"] == "logistic_C0.05", "Model drift")
    auc = evidence["holdout_probability_metrics"]["roc_auc"]
    require(0.75 <= auc <= 0.82, "Unexpected holdout AUC")
    calibration = evidence["holdout_calibration"]
    require(calibration["quantile_expected_calibration_error"] < 0.02, "Calibration drift")
    require(
        abs(calibration["flagged_mean_predicted_risk"] - calibration["flagged_observed_return_rate"]) < 0.03,
        "Flagged-queue calibration drift",
    )
    require(evidence["leakage_probe"]["holdout_roc_auc_with_post_outcome_fields"] > 0.98, "Leakage sentinel changed")
    require(evidence["holdout_operating_point"]["recall"] == 0.6, "Operating point changed")
    require(evidence["performance"]["paid_inference_cost_inr_per_order"] == 0, "Paid model call found")


def verify_memo() -> None:
    memo = PdfReader(str(OUTPUTS / "Ritu_Deshpande_Memo.pdf"))
    require(len(memo.pages) == 1, "Ritu memo must be exactly one page")
    text = memo.pages[0].extract_text() or ""
    for phrase in ("₹11,821", "15%+ return risk", "WHAT TO DO NEXT WEEK"):
        require(phrase in text, f"Memo is missing: {phrase}")


def verify_package() -> None:
    require(PACKAGE.exists(), "Confidential package ZIP is missing")
    with zipfile.ZipFile(PACKAGE) as archive:
        names = set(archive.namelist())
        required = {
            "README.md",
            "submission-form.md",
            "artifacts/return_risk_model.joblib",
            "data/raw/train.csv",
            "data/raw/test_unlabelled.csv",
            "outputs/predictions.csv",
            "outputs/Ritu_Deshpande_Memo.pdf",
            "outputs/package_manifest.json",
        }
        require(required <= names, f"Package missing: {sorted(required - names)}")
        forbidden = [name for name in names if ".venv/" in name or "__pycache__" in name or name.startswith("logs/") or name.startswith("work/")]
        require(not forbidden, f"Package contains local-only files: {forbidden[:5]}")
        manifest = json.loads(archive.read("outputs/package_manifest.json"))
        for entry in manifest["files"]:
            data = archive.read(entry["path"])
            require(len(data) == entry["bytes"], f"Size mismatch: {entry['path']}")
            require(hashlib.sha256(data).hexdigest() == entry["sha256"], f"Hash mismatch: {entry['path']}")

        with tempfile.TemporaryDirectory(prefix="kestrel-verify-") as temporary:
            archive.extractall(temporary)
            command = [
                sys.executable,
                "-c",
                (
                    "from fastapi.testclient import TestClient; "
                    "from app.main import app; "
                    "r=TestClient(app).get('/health'); "
                    "assert r.status_code==200 and r.json()['status']=='ready'; "
                    "print(r.json()['model_version'])"
                ),
            ]
            completed = subprocess.run(
                command,
                cwd=temporary,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=60,
                check=False,
            )
            require(completed.returncode == 0, f"Clean extraction smoke test failed: {completed.stderr}")


def main() -> None:
    verify_predictions()
    verify_evidence()
    verify_memo()
    verify_package()
    print("PASS: predictions, evidence, one-page memo, manifest, and clean-package startup verified.")


if __name__ == "__main__":
    main()
