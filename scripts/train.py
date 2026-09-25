"""Train the final leakage-safe model on all labelled orders."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.modeling import save_artifact, train_artifact


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "return_risk_model.joblib")
    args = parser.parse_args()

    artifact = train_artifact(args.raw_dir)
    artifact.metadata["training_file_sha256"] = sha256(args.raw_dir / "train.csv")
    save_artifact(artifact, args.output)

    metadata_path = args.output.with_name("model_metadata.json")
    metadata_path.write_text(
        json.dumps(artifact.metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Saved model: {args.output}")
    print(f"Saved metadata: {metadata_path}")
    print(json.dumps(artifact.metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
