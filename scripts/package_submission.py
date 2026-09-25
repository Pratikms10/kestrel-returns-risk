"""Build the private, confidential handoff ZIP with an integrity manifest."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "Kestrel_Home_Task2_CONFIDENTIAL.zip"
MANIFEST = ROOT / "outputs" / "package_manifest.json"

TOP_LEVEL_FILES = [
    ".env.example",
    ".gitignore",
    "DATA_PRIVACY.md",
    "README.md",
    "pytest.ini",
    "requirements.txt",
    "requirements-dev.txt",
    "submission-form.md",
]
DIRECTORIES = ["app", "artifacts", "data/raw", "docs", "scripts", "tests"]
OUTPUT_FILES = [
    "outputs/predictions.csv",
    "outputs/predictions_summary.json",
    "outputs/evaluation_metrics.json",
    "outputs/service_benchmark.json",
    "outputs/Ritu_Deshpande_Memo.pdf",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def included_files() -> list[Path]:
    paths = [ROOT / name for name in TOP_LEVEL_FILES + OUTPUT_FILES]
    for directory in DIRECTORIES:
        paths.extend(path for path in (ROOT / directory).rglob("*") if path.is_file())
    return sorted(
        {
            path
            for path in paths
            if path.exists()
            and "__pycache__" not in path.parts
            and path.suffix not in {".pyc", ".zip"}
        },
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def main() -> None:
    files = included_files()
    missing = [name for name in TOP_LEVEL_FILES + OUTPUT_FILES if not (ROOT / name).exists()]
    if missing:
        raise FileNotFoundError(f"Required package files are missing: {missing}")

    entries = []
    for path in files:
        data = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": len(data),
                "sha256": sha256_bytes(data),
            }
        )
    manifest = {
        "classification": "CONFIDENTIAL — Kestrel client data",
        "file_count_excluding_manifest": len(entries),
        "files": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.write(MANIFEST, MANIFEST.relative_to(ROOT).as_posix())
    print(f"Saved confidential package: {OUTPUT}")
    print(f"Files: {len(entries) + 1}; ZIP bytes: {OUTPUT.stat().st_size}")


if __name__ == "__main__":
    main()
