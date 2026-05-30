import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACKED_PATHS = [
    "app.py",
    "src/report_signal_pipeline.py",
    "src/config.py",
    "requirements.txt",
    "requirements-lock.txt",
    "data/processed/stock_returns_weekly.csv",
    "data/processed/news_sentiment_weekly.csv",
    "data/processed/reports/report_signals.csv",
    "data/processed/reports/expanded_pdf_validation.csv",
    "data/processed/reports/zero_shot_vs_few_shot.csv",
]


def file_record(path):
    full_path = ROOT / path
    if not full_path.exists():
        return {"path": path, "exists": False}
    data = full_path.read_bytes()
    return {
        "path": path,
        "exists": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def main():
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project": "Energy Report-to-Market Signal Analyzer",
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "scoring": "Frozen MiniLM embeddings + few-shot logistic regression heads",
        "retrieval": "TF-IDF + embedding hybrid retrieval",
        "files": [file_record(path) for path in TRACKED_PATHS],
    }
    output = ROOT / "outputs" / "tables" / "repro_manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
