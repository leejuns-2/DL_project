from pathlib import Path

import pandas as pd
import requests

from config import PROCESSED_DIR, RAW_DIR, TABLES_DIR, ensure_project_dirs
from report_signal_pipeline import (
    EmbeddingModel,
    ReportMeta,
    extract_pdf_text_from_path,
    few_shot_scores,
    retrieve_evidence,
    split_paragraphs,
)


VALIDATION_DIR = RAW_DIR / "validation_reports"
VALIDATION_PROCESSED_DIR = PROCESSED_DIR / "validation_reports"


VALIDATION_REPORTS = [
    {
        "report_id": "iea_renewables_2022",
        "title": "IEA Renewables 2022",
        "date": "2022-12-06",
        "issuer": "IEA",
        "filename": "iea_renewables_2022.pdf",
        "url": "https://iea.blob.core.windows.net/assets/ada7af90-e280-46c4-a577-df2e4fb44254/Renewables2022.pdf",
        "expected_asset_hint": "ICLN/NEE",
    },
    {
        "report_id": "iea_weo_2022",
        "title": "IEA World Energy Outlook 2022",
        "date": "2022-10-27",
        "issuer": "IEA",
        "filename": "iea_world_energy_outlook_2022.pdf",
        "url": "https://iea.blob.core.windows.net/assets/830fe099-5530-48f2-a7c1-11f35d510983/WorldEnergyOutlook2022.pdf",
        "expected_asset_hint": "ICLN/NEE",
    },
    {
        "report_id": "iea_electricity_2024",
        "title": "IEA Electricity 2024",
        "date": "2024-01-24",
        "issuer": "IEA",
        "filename": "iea_electricity_2024.pdf",
        "url": "https://iea.blob.core.windows.net/assets/18f3ed24-4b26-4c83-a3d2-8a1be51c8cc8/Electricity2024-Analysisandforecastto2026.pdf",
        "expected_asset_hint": "ETN",
    },
]


def ensure_dirs():
    ensure_project_dirs()
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATION_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def download_report(item):
    path = VALIDATION_DIR / item["filename"]
    if path.exists() and path.stat().st_size > 100_000:
        return path

    response = requests.get(item["url"], timeout=90)
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def report_meta(item, path):
    return ReportMeta(
        report_id=item["report_id"],
        title=item["title"],
        date=item["date"],
        issuer=item["issuer"],
        path=str(path),
        source_url=item["url"],
    )


def run_validation(max_pages=100, top_k=10):
    ensure_dirs()

    all_paragraphs = []
    expected_rows = []
    for item in VALIDATION_REPORTS:
        path = download_report(item)
        report = report_meta(item, path)
        pages = extract_pdf_text_from_path(path, max_pages=max_pages)
        paragraphs = split_paragraphs(report, pages)
        if not paragraphs:
            raise RuntimeError(f"No paragraphs extracted from {path}")
        all_paragraphs.extend(paragraphs)
        expected_rows.append(
            {
                "report_id": item["report_id"],
                "title": item["title"],
                "expected_asset_hint": item["expected_asset_hint"],
                "source_url": item["url"],
                "pages_extracted": len(pages),
                "paragraphs_extracted": len(paragraphs),
            }
        )
        print(f"{item['report_id']}: pages={len(pages)}, paragraphs={len(paragraphs)}")

    paragraphs_df = pd.DataFrame(all_paragraphs)
    paragraphs_df.to_csv(VALIDATION_PROCESSED_DIR / "validation_report_paragraphs.csv", index=False)

    evidence = retrieve_evidence(paragraphs_df, top_k=top_k)
    evidence.to_csv(VALIDATION_PROCESSED_DIR / "validation_report_evidence.csv", index=False)

    embedder = EmbeddingModel()
    scores = few_shot_scores(evidence, embedder)

    expected = pd.DataFrame(expected_rows)
    result = scores.merge(expected, on=["report_id", "title"], how="left")
    result["asset_hint_correct"] = result["asset_hint"] == result["expected_asset_hint"]
    result["accuracy_note"] = result["asset_hint_correct"].map(
        {True: "expected label matched", False: "expected label not matched"}
    )

    theme_cols = ["renewable_opportunity", "fossil_pressure", "grid_infrastructure", "climate_risk"]
    result["top_theme"] = result[theme_cols].idxmax(axis=1)
    result["top_theme_score"] = result[theme_cols].max(axis=1)
    result["second_theme_score"] = result[theme_cols].apply(lambda row: row.sort_values(ascending=False).iloc[1], axis=1)
    result["score_margin"] = result["top_theme_score"] - result["second_theme_score"]

    result.to_csv(VALIDATION_PROCESSED_DIR / "validation_scores.csv", index=False)

    summary_cols = [
        "title",
        "expected_asset_hint",
        "asset_hint",
        "asset_hint_correct",
        "top_theme",
        "top_theme_score",
        "score_margin",
        "pages_extracted",
        "paragraphs_extracted",
    ]
    summary = result[summary_cols].copy()
    accuracy = summary["asset_hint_correct"].mean()

    lines = [
        "# PDF Generalization Validation",
        "",
        "## 목적",
        "",
        "2023년 리포트가 아닌 자료를 넣었을 때도 few-shot PDF 신호화가 기대한 방향으로 작동하는지 확인했습니다.",
        "",
        "## 검증 기준",
        "",
        "- 사람이 보고 기대 라벨을 먼저 정했습니다.",
        "- 모델이 예측한 `asset_hint`가 기대 라벨과 같으면 맞은 것으로 계산했습니다.",
        "- 표본 수가 작으므로 이 값은 엄밀한 모델 정확도가 아니라 MVP 일반화 점검용 정확도입니다.",
        "",
        f"검증 정확도: `{accuracy:.3f}` ({summary['asset_hint_correct'].sum()} / {len(summary)})",
        "",
        "## 결과",
        "",
        summary.to_markdown(index=False),
        "",
        "## 해석",
        "",
        "- 기대 라벨과 맞으면, 기존 2023년 보고서가 아닌 자료에서도 주제 신호가 같은 방향으로 나온 것입니다.",
        "- 틀린 항목은 모델 오류일 수도 있지만, 보고서가 여러 주제를 동시에 다루기 때문일 수도 있습니다.",
        "- `score_margin`이 작으면 1등 주제와 2등 주제 차이가 작다는 뜻이라 확신도가 낮은 결과로 봐야 합니다.",
    ]
    output = TABLES_DIR / "pdf_generalization_validation.md"
    output.write_text("\n".join(lines), encoding="utf-8")

    print(f"accuracy={accuracy:.3f}")
    print(output)
    return result


if __name__ == "__main__":
    run_validation()
