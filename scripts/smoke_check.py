import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import app  # noqa: E402
from report_signal_pipeline import (  # noqa: E402
    EmbeddingModel,
    ReportMeta,
    infer_signal_profile,
    event_window_stock_returns,
    extract_pdf_text_from_path,
    retrieve_evidence,
    score_evidence_with_few_shot_learning,
    split_paragraphs,
    summarize_validation_results,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"ok - {message}")


def check_event_returns():
    scores = pd.DataFrame(
        [{"report_id": "smoke", "title": "Smoke", "date": "2023-10-24", "asset_hint": "ICLN/NEE", "transition_signal": 1.0}]
    )
    result = event_window_stock_returns(scores)
    check(not result.empty, "event window returns are generated")
    check("post_4w_abnormal_ICLN" in result.columns, "abnormal return column exists")


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
        print("skip - sample PDF not found")
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
            {"split": "validation", "predicted_hint": "ICLN/NEE", "matched": True, "ood_decision": "in_domain"},
            {"split": "test", "predicted_hint": "ETN", "matched": False, "ood_decision": "low_relevance"},
        ]
    )
    metrics = summarize_validation_results(sample)
    check({"all", "validation", "test"}.issubset(set(metrics["split"])), "split metrics include all groups")


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


def main():
    check(app.app.title == "Energy Report-to-Market Signal Analyzer", "FastAPI app imports")
    check_event_returns()
    embedder = EmbeddingModel()
    check_ood_guard(embedder)
    check_sample_pdf(embedder)
    check_validation_metrics()
    check_mixed_signal_profile()
    print("smoke check complete")


if __name__ == "__main__":
    main()
