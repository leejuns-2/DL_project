import sys
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import app  # noqa: E402
from report_signal_pipeline import (  # noqa: E402
    EmbeddingModel,
    ReportMeta,
    evidence_support_metadata,
    infer_signal_profile,
    event_window_stock_returns,
    extract_pdf_text_from_path,
    label_evidence_chunks,
    retrieve_evidence,
    score_evidence_with_few_shot_learning,
    split_paragraphs,
    summarize_chunk_labels,
)
from evaluation import summarize_development_results  # noqa: E402

RESULTS = []


def check(condition, message):
    if not condition:
        RESULTS.append({"status": "fail", "message": message})
        raise AssertionError(message)
    RESULTS.append({"status": "pass", "message": message})
    print(f"ok - {message}")


def write_smoke_result(status, error=None):
    output_dir = ROOT / "outputs" / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "error": str(error) if error else "",
        "checks": RESULTS,
    }
    json_path = output_dir / "smoke_check_result.json"
    md_path = output_dir / "smoke_check_result.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Smoke Check Result",
        "",
        f"- status: `{status}`",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
    ]
    if error:
        lines.append(f"- error: `{error}`")
    lines.extend(["", "| Status | Check |", "|---|---|"])
    for row in RESULTS:
        lines.append(f"| {row['status']} | {row['message']} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json_path)
    print(md_path)


def check_event_returns():
    scores = pd.DataFrame(
        [{"report_id": "smoke", "title": "Smoke", "date": "2023-10-24", "asset_hint": "ICLN/NEE", "transition_signal": 1.0}]
    )
    result = event_window_stock_returns(scores)
    check(not result.empty, "event window returns are generated")
    check("post_4w_abnormal_ICLN" in result.columns, "abnormal return column exists")


def check_api_routes():
    client = TestClient(app.app)
    dashboard = client.get("/api/dashboard")
    check(dashboard.status_code == 200, "dashboard API returns 200")
    data = dashboard.json()
    check("methodology" in data, "dashboard API includes methodology")
    check(data["methodology"]["base_model"] == "sentence-transformers/all-MiniLM-L6-v2", "dashboard methodology names MiniLM")
    index = client.get("/")
    check(index.status_code == 200, "web app root returns 200")


def check_ood_guard(embedder):
    texts = [
        "This education report reviews classroom attendance, teacher training, curriculum design, student outcomes, and administrative policy.",
        "The document describes public health survey methods, hospital staffing, disease surveillance, and statistical reporting limitations.",
        "This annual review focuses on accounting policies, revenue recognition, employee benefits, legal proceedings, and marketing costs.",
    ] * 4
    paragraphs = pd.DataFrame(
        {
            "report_id": ["ood"] * len(texts),
            "title": ["Education and Health Administration Review"] * len(texts),
            "date": ["2024-01-01"] * len(texts),
            "issuer": ["Test"] * len(texts),
            "page": list(range(1, len(texts) + 1)),
            "paragraph": texts,
        }
    )
    evidence = retrieve_evidence(paragraphs, top_k=4, embedder=embedder, hybrid=True)
    scores = score_evidence_with_few_shot_learning(evidence, embedder)
    decision = scores.iloc[0]["ood_decision"]
    check(decision == "out_of_domain", "non-energy text is marked out_of_domain")


def check_sample_pdf(embedder):
    pdf = ROOT / "data" / "sample_pdfs" / "IEA_Renewables_2023.pdf"
    if not pdf.exists():
        message = "sample energy PDF check requires scripts/download_validation_pdfs.py"
        RESULTS.append({"status": "skip", "message": message})
        print(f"skip - {message}")
        return
    report = ReportMeta("smoke_pdf", "IEA Renewables 2023", "2024-01-11", "IEA", str(pdf), "")
    pages = extract_pdf_text_from_path(pdf, max_pages=8)
    paragraphs = pd.DataFrame(split_paragraphs(report, pages))
    evidence = retrieve_evidence(paragraphs, top_k=5, embedder=embedder, hybrid=True)
    scores = score_evidence_with_few_shot_learning(evidence, embedder)
    check(scores.iloc[0]["ood_decision"] == "in_domain", "energy PDF is marked in_domain")
    check(scores.iloc[0]["energy_relevance"] >= 0.55, "energy relevance clears threshold")


def check_validation_metrics():
    sample = pd.DataFrame(
        [
            {"split": "development_main", "predicted_hint": "ICLN/NEE", "matched": True, "ood_decision": "in_domain"},
            {"split": "development_diagnostic", "predicted_hint": "ETN", "matched": False, "ood_decision": "low_relevance"},
        ]
    )
    metrics = summarize_development_results(sample)
    check(
        {"all_development", "development_main", "development_diagnostic"}.issubset(
            set(metrics["split"])
        ),
        "development metrics include all diagnostic groups",
    )


def check_mixed_signal_profile():
    row = {
        "title": "World Energy Outlook boundary case",
        "renewable_opportunity": 0.93,
        "fossil_pressure": 1.0,
        "grid_infrastructure": 0.0,
        "climate_risk": 0.46,
        "ood_decision": "in_domain",
    }
    profile = infer_signal_profile(row)
    check(profile["mixed_signal"] is True, "close high-confidence themes are marked mixed_signal")
    check("ICLN/NEE" in profile["asset_hint"], "mixed signal keeps renewable component visible")
    check("XLE/XOM" in profile["asset_hint"], "mixed signal keeps fossil component visible")


def check_chunk_multilabel_helpers():
    evidence = pd.DataFrame(
        [
            {
                "report_id": "chunk_smoke",
                "chunk_id": "chunk_smoke_chunk_0001",
                "title": "Chunk Smoke",
                "date": "2024-01-01",
                "issuer": "Test",
                "page": 1,
                "paragraph": "Solar generation needs transmission expansion and grid flexibility.",
                "theme": "renewable_opportunity",
                "retrieval_score": 0.90,
            },
            {
                "report_id": "chunk_smoke",
                "chunk_id": "chunk_smoke_chunk_0001",
                "title": "Chunk Smoke",
                "date": "2024-01-01",
                "issuer": "Test",
                "page": 1,
                "paragraph": "Solar generation needs transmission expansion and grid flexibility.",
                "theme": "grid_infrastructure",
                "retrieval_score": 0.82,
            },
        ]
    )
    labels = label_evidence_chunks(evidence)
    summary = summarize_chunk_labels(labels)
    support = evidence_support_metadata(evidence)
    check(bool(labels.iloc[0]["is_mixed_signal_chunk"]) is True, "chunk weak labels can mark multi-label evidence")
    check(summary["multi_label_chunk_count"] == 1, "chunk label summary counts mixed chunks")
    check(support["evidence_chunk_ids"], "summary support metadata includes evidence chunk ids")


def main():
    try:
        check(app.app.title == "Energy Report-to-Market Signal Analyzer", "FastAPI app imports")
        check_api_routes()
        check_event_returns()
        embedder = EmbeddingModel()
        check_ood_guard(embedder)
        check_sample_pdf(embedder)
        check_validation_metrics()
        check_mixed_signal_profile()
        check_chunk_multilabel_helpers()
    except Exception as exc:
        write_smoke_result("fail", exc)
        raise
    write_smoke_result("pass")
    print("smoke check complete")


if __name__ == "__main__":
    main()
