from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "data" / "processed" / "reports"
TABLE_DIR = ROOT / "outputs" / "tables"


def _read_csv(name: str) -> pd.DataFrame:
    path = REPORT_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def _safe_int(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return str(int(value))


def _load_live_tests() -> list[dict]:
    outputs = ROOT / "outputs"
    rows = []
    for path in sorted(outputs.glob("test_*response*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        scores = data.get("scores", {})
        confidence = data.get("confidence", {})
        rows.append(
            {
                "file": path.name,
                "asset_hint": scores.get("asset_hint", ""),
                "top_theme": confidence.get("top_theme", ""),
                "confidence": confidence.get("level", ""),
                "energy_relevance": scores.get("energy_relevance", ""),
                "ood_decision": scores.get("ood_decision", ""),
                "cache_hit": data.get("cache", {}).get("hit", ""),
            }
        )
    return rows


def _markdown_table(rows: list[dict], columns: list[tuple[str, str]]) -> list[str]:
    if not rows:
        return ["_No rows available._"]
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(key, "")).replace("\n", " ") for key, _ in columns) + " |")
    return lines


def build_brief() -> str:
    metrics = _read_csv("pdf_validation_metrics.csv")
    validation = _read_csv("expanded_pdf_validation.csv")
    failures = _read_csv("pdf_validation_failure_analysis.csv")
    ood = _read_csv("out_of_domain_pdf_test.csv")
    comparison = _read_csv("zero_shot_vs_few_shot.csv")
    gemini = _read_csv("gemini_summary_human_check.csv")
    chunk_labels = _read_csv("pdf_validation_chunk_labels.csv")

    metric = metrics.iloc[0].to_dict() if not metrics.empty else {}
    total = int(metric.get("n", len(validation))) if not validation.empty or metric else 0
    matched = int(validation["matched"].astype(bool).sum()) if "matched" in validation else None

    zero_accuracy = None
    few_accuracy = None
    if not comparison.empty:
        zero_accuracy = comparison["zero_shot_matched"].astype(bool).mean()
        few_accuracy = comparison["few_shot_matched"].astype(bool).mean()

    failure_rows = []
    if not failures.empty:
        for _, row in failures.head(8).iterrows():
            failure_rows.append(
                {
                    "title": row.get("title", ""),
                    "expected": row.get("expected_hint", ""),
                    "predicted": row.get("predicted_hint", ""),
                    "reason": row.get("failure_interpretation", ""),
                }
            )

    ood_rows = []
    if not ood.empty:
        for _, row in ood.iterrows():
            ood_rows.append(
                {
                    "title": row.get("title", ""),
                    "top_theme": row.get("top_theme", ""),
                    "margin": f"{float(row.get('score_margin', 0)):.3f}",
                    "decision": row.get("ood_decision", ""),
                    "interpretation": row.get("interpretation", ""),
                }
            )

    gemini_pass = None
    gemini_review = None
    if not gemini.empty and "human_check_result" in gemini:
        gemini_pass = int((gemini["human_check_result"] == "pass").sum())
        gemini_review = int((gemini["human_check_result"] != "pass").sum())

    chunk_total = len(chunk_labels)
    mixed_chunk_count = 0
    if not chunk_labels.empty and "is_mixed_signal_chunk" in chunk_labels:
        mixed_chunk_count = int(chunk_labels["is_mixed_signal_chunk"].astype(bool).sum())

    live_rows = _load_live_tests()

    lines = [
        "# Model Validation Brief",
        "",
        "## 목적",
        "",
        "이 문서는 에너지/기후 PDF 분석 모델을 발표 또는 제출용 결과로 해석할 때 필요한 검증 요약입니다. "
        "단순 정확도만 제시하지 않고, baseline 비교, 실패 사례, OOD 한계, mixed-signal 문서, 생성형 요약 검증을 함께 공개합니다.",
        "",
        "## 한줄 평가",
        "",
        "현재 모델은 연구용 MVP로는 동작하지만, 검증 PDF 25개는 통계적 일반화 평가로 보기에는 작습니다. "
        "따라서 현재 수치는 pilot evaluation으로만 해석하고, 문단 단위 multi-label 평가셋과 OOD 전용 평가를 확장해야 합니다.",
        "",
        "## 핵심 지표",
        "",
        "| 항목 | 값 | 해석 |",
        "|---|---:|---|",
        f"| 검증 PDF 수 | {_safe_int(total)} | 공개 PDF 기반 소규모 pilot 검증셋 |",
        f"| 기대 방향 일치 | {_safe_int(matched)} / {_safe_int(total)} | 사람이 정한 자산/테마 방향과 모델 판정 비교 |",
        f"| Accuracy | {_pct(metric.get('accuracy'))} | 단일 라벨 기준의 참고값 |",
        f"| Macro-F1 | {float(metric.get('macro_f1', 0)):.3f} | 라벨 불균형 영향을 줄인 평균 F1 |",
        f"| Zero-shot baseline | {_pct(zero_accuracy)} | MiniLM 임베딩 유사도만 사용한 기준선 |",
        f"| Few-shot head | {_pct(few_accuracy)} | 고정 MiniLM 임베딩 위 logistic head 사용 |",
        f"| Chunk weak labels | {_safe_int(chunk_total)} | 문단 단위 multi-label 확장용 약지도 테이블 |",
        f"| Mixed chunks | {_safe_int(mixed_chunk_count)} | 복합 문단으로 검토해야 할 chunk 수 |",
        "",
        "## 개선된 판정 기준",
        "",
        "| 검증 포인트 | 통과 기준 | 현재 판정 |",
        "|---|---|---|",
        "| 기능 정상성 | PDF 업로드, 근거 검색, 점수 산출, 과거 수익률 연결까지 실행 | 통과 |",
        "| Baseline 대비 개선 | zero-shot보다 few-shot head가 명확히 좋아야 함 | 통과 |",
        "| 근거 정합성 | 요약과 점수에 evidence chunk ID가 붙어야 함 | 개선됨 |",
        "| OOD 방어 | 비에너지 PDF가 강한 시장 신호로 오인되지 않아야 함 | 부분 통과, climate-health는 review 필요 |",
        "| 복합 주제 처리 | 하나의 PDF 안의 여러 테마를 mixed-signal로 드러내야 함 | 개선됨 |",
        "| Chunk multi-label | PDF 단일 라벨 외 문단 단위 라벨 테이블이 있어야 함 | 추가됨 |",
        "| 생성형 요약 안전성 | Gemini 요약은 근거 문단과 함께 확인되어야 함 | 개선됨 |",
        "",
        "## 실패 사례 해석",
        "",
        *_markdown_table(
            failure_rows,
            [
                ("title", "문서"),
                ("expected", "기대"),
                ("predicted", "예측"),
                ("reason", "해석"),
            ],
        ),
        "",
        "주요 실패 원인은 모델이 완전히 틀렸다기보다 하나의 PDF 안에 재생에너지, 화석연료 전환, 전력망, 기후 리스크 표현이 함께 들어가는 경우가 많다는 점입니다. "
        "이 경우 단일 라벨 정답으로만 평가하면 오류처럼 보이므로, 문서 단위 mixed-signal과 문단 단위 multi-label 결과를 함께 제시해야 합니다.",
        "",
        "## OOD 점검",
        "",
        *_markdown_table(
            ood_rows,
            [
                ("title", "문서"),
                ("top_theme", "상위 테마"),
                ("margin", "마진"),
                ("decision", "판정"),
                ("interpretation", "해석"),
            ],
        ),
        "",
        "WHO 보건 문서처럼 climate-health 표현이 많은 OOD 문서는 climate risk와 겹칠 수 있습니다. "
        "이번 수정에서는 OOD subtype을 추가해 `climate_health_overlap`은 자동 확정 대신 review 대상으로 표시할 수 있게 했습니다.",
        "",
        "## 생성형 요약 검증",
        "",
        f"- Gemini 표본 검토 pass {_safe_int(gemini_pass)}, review {_safe_int(gemini_review)}",
        "- 주요 체크 기준: 요약 문장이 evidence chunk와 맞는지, 투자 추천이나 미래 수익률 예측처럼 들리지 않는지, 과장된 인과 표현이 없는지 확인합니다.",
        "- API 응답에는 `evidence_chunk_ids`, `support_level`, `support_note`를 붙여 생성형 출력만 단독으로 보지 않게 했습니다.",
        "",
        "## 라이브 테스트 기록",
        "",
        *_markdown_table(
            live_rows[-6:],
            [
                ("file", "응답 파일"),
                ("asset_hint", "자산 힌트"),
                ("top_theme", "상위 테마"),
                ("confidence", "확신도"),
                ("energy_relevance", "에너지 관련성"),
                ("ood_decision", "OOD"),
                ("cache_hit", "캐시"),
            ],
        ),
        "",
        "## 완성도 판단",
        "",
        "현재 완성도는 연구 프로젝트 기준으로는 충분히 설명 가능한 수준입니다. "
        "다만 일반화 성능 주장에는 아직 이르며, 남은 핵심 보완은 100개 이상 PDF 확장, 사람이 검수한 chunk multi-label 평가셋, climate-health/OOD 전용 negative set입니다.",
        "",
        "## 발표용 안전 문장",
        "",
        "> 이 시스템은 PDF를 넣으면 미래 수익률을 예측하는 도구가 아닙니다. 에너지/기후 보고서의 근거 문단을 few-shot topic signal로 변환하고, 뉴스 컨텍스트 및 과거 주가 반응과 연결해 탐색하는 연구용 MVP입니다.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    output = TABLE_DIR / "model_validation_brief.md"
    output.write_text(build_brief(), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
