import hashlib
import json
import platform
import sys
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
    "data/processed/reports/report_stock_link.csv",
    "data/processed/reports/report_news_bridge.csv",
    "data/processed/reports/expanded_pdf_validation.csv",
    "data/processed/reports/validation_pdf_catalog.csv",
    "data/processed/reports/sample_pdf_manifest.csv",
    "data/processed/reports/zero_shot_vs_few_shot.csv",
    "data/processed/reports/pdf_validation_metrics.csv",
    "data/processed/reports/pdf_validation_split_metrics.csv",
    "data/processed/reports/pdf_validation_confusion_matrix.csv",
    "data/processed/reports/pdf_validation_chunk_labels.csv",
    "data/processed/reports/pdf_validation_label_rationale.csv",
    "data/processed/reports/pdf_validation_failure_analysis.csv",
    "data/processed/reports/out_of_domain_pdf_test.csv",
    "data/processed/reports/gemini_summary_human_check.csv",
    "data/processed/reports/zero_shot_vs_few_shot_split_metrics.csv",
    "data/processed/reports/actual_climate_news_lag_corr.csv",
    "data/processed/reports/actual_news_stock_best_lag.csv",
    "outputs/tables/model_validation_brief.md",
    "outputs/tables/final_result_summary.md",
    "outputs/tables/project_quality_audit.md",
    "outputs/tables/pdf_generalization_validation.md",
    "outputs/tables/smoke_check_result.json",
    "outputs/tables/smoke_check_result.md",
    "outputs/reports/Energy_Report_Signal_Analyzer_report_style_FINAL.pptx",
    "outputs/reports/Report_to_Market_Context_Analyzer_Project_Report_KR.docx",
    "outputs/reports/Report_to_Market_Context_Analyzer_Project_Report_KR.pdf",
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
    sample_pdf_dir = ROOT / "data" / "sample_pdfs"
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project": "Energy Report-to-Market Signal Analyzer",
        "python": sys.version,
        "platform": platform.platform(),
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "scoring": "Frozen MiniLM embeddings + small-sample supervised logistic linear probes",
        "retrieval": "TF-IDF + embedding hybrid retrieval",
        "validation_summary": {
            "pilot_pdf_count": 50,
            "pilot_few_shot_matches": 36,
            "development_top1_agreement": 0.72,
            "pilot_macro_f1": 0.658,
            "zero_shot_matches": 17,
            "few_shot_matches": 36,
            "catalog_pdf_count": 50,
            "interpretation": "Pilot evaluation only; not a generalization estimate.",
        },
        "sample_pdf_inventory": {
            "directory": "data/sample_pdfs",
            "exists": sample_pdf_dir.exists(),
            "pdf_count": len(list(sample_pdf_dir.glob("*.pdf"))) if sample_pdf_dir.exists() else 0,
        },
        "files": [file_record(path) for path in TRACKED_PATHS],
    }
    output = ROOT / "outputs" / "tables" / "repro_manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
