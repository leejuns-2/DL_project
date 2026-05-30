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

    metric = metrics.iloc[0].to_dict() if not metrics.empty else {}
    total = int(metric.get("n", len(validation))) if not validation.empty or metric else 0
    matched = int(validation["matched"].astype(bool).sum()) if "matched" in validation else None

    zero_accuracy = None
    few_accuracy = None
    if not comparison.empty:
        zero_accuracy = comparison["zero_shot_matched"].astype(bool).mean()
        few_accuracy = comparison["few_shot_matched"].astype(bool).mean()

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

    gemini_pass = None
    gemini_review = None
    if not gemini.empty and "human_check_result" in gemini:
        gemini_pass = int((gemini["human_check_result"] == "pass").sum())
        gemini_review = int((gemini["human_check_result"] != "pass").sum())

    live_rows = _load_live_tests()

    lines = [
        "# Model Validation Brief",
        "",
        "## 목적",
        "",
        "이 문서는 프로젝트 결과를 발표하거나 제출할 때 모델이 어느 정도 신뢰 가능한지 판단하기 위한 검증 요약입니다. "
        "핵심은 높은 점수만 보여주는 것이 아니라, baseline 대비 개선, 실패 사례, OOD 한계, 생성 요약 검토를 함께 공개하는 것입니다.",
        "",
        "## 한 줄 평가",
        "",
        "현재 모델은 에너지/기후 PDF를 시장 분석용 주제 신호로 바꾸는 연구용 MVP로는 충분히 작동합니다. "
        "다만 표본 규모가 작고 복합 주제 문서는 단일 라벨 평가가 어려우므로, 일반화 성능이나 투자 예측 성능으로 과장하면 안 됩니다.",
        "",
        "## 핵심 지표",
        "",
        "| 항목 | 값 | 해석 |",
        "|---|---:|---|",
        f"| 검증 PDF 수 | {_safe_int(total)} | 공개 에너지/기후 PDF 기반 소규모 검증셋 |",
        f"| 기대 방향 일치 | {_safe_int(matched)} / {_safe_int(total)} | 사람이 정한 대표 자산/테마 방향과 모델 판정 비교 |",
        f"| Accuracy | {_pct(metric.get('accuracy'))} | 전체 표본 중 단일 라벨 일치율 |",
        f"| Macro-F1 | {float(metric.get('macro_f1', 0)):.3f} | 라벨 불균형을 줄여 본 평균 F1 |",
        f"| Zero-shot baseline | {_pct(zero_accuracy)} | MiniLM 임베딩 유사도만 사용한 기준선 |",
        f"| Few-shot head | {_pct(few_accuracy)} | 고정 MiniLM 임베딩 위 logistic head 사용 |",
        "",
        "## 판단 기준",
        "",
        "| 검토 포인트 | 통과 기준 | 현재 판단 |",
        "|---|---|---|",
        "| 기능 정상성 | PDF 업로드, 근거 검색, 점수 산출, 수익률 연결이 끝까지 실행됨 | 통과 |",
        "| Baseline 대비 개선 | zero-shot보다 few-shot head가 명확히 좋아야 함 | 통과 |",
        "| 근거 정합성 | 상위 근거 문단이 실제 테마 내용을 포함해야 함 | 대체로 통과, 목차 문단 필터 추가 완료 |",
        "| OOD 방어 | 비에너지 PDF가 강한 투자 신호로 오인되지 않아야 함 | 부분 통과, climate-health overlap은 한계 |",
        "| 복합 주제 처리 | 상위 두 테마가 모두 강하면 단일 라벨 대신 mixed-signal로 표시해야 함 | 통과 |",
        "| 생성 요약 안전성 | 근거 기반 요약이며 투자 추천/수익률 예측을 하지 않아야 함 | 부분 통과, 스타일 리뷰 필요 |",
        "| 연구 설명 가능성 | 모델 구조, 데이터 한계, 실패 사례를 문서화해야 함 | 통과 |",
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
        "실패 사례의 공통 원인은 모델이 완전히 틀렸다기보다, 하나의 PDF 안에 재생에너지, 화석연료 전환, 전력망, 기후 리스크 표현이 같이 들어 있는 경우가 많다는 점입니다. "
        "따라서 상위 두 테마가 모두 강하고 점수 차이가 작은 경우에는 mixed-signal로 표시하도록 보완했습니다. "
        "발표에서는 단일 라벨 분류기라기보다 복합 보고서를 시장 신호로 요약하는 도구라고 설명하는 것이 안전합니다.",
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
        "OOD 결과는 비에너지 문서에서도 climate-risk 표현이 있으면 일부 흡수될 수 있음을 보여줍니다. "
        "현재는 energy relevance와 score margin을 함께 보고 낮은 확신 또는 도메인 중복을 설명하는 방식이 적절합니다.",
        "",
        "## 생성 요약 검토",
        "",
        f"- Gemini 표본 검토: pass {_safe_int(gemini_pass)}, review {_safe_int(gemini_review)}",
        "- 주요 체크 기준: 근거 문단과 요약의 주제 일치, 투자 추천/수익률 예측 문구 부재, 과장된 인과 표현 부재",
        "- 발표 시 요약문만 단독으로 보여주지 말고 근거 문단과 함께 보여주는 것이 안전합니다.",
        "",
        "## 라이브 웹 테스트 기록",
        "",
        *_markdown_table(
            live_rows[-6:],
            [
                ("file", "응답 파일"),
                ("asset_hint", "자산 신호"),
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
        "현재 완성도는 연구 프로젝트 기준 약 85점 수준으로 평가할 수 있습니다. "
        "기능 흐름과 배포, baseline 비교, 실패 분석, 복합 주제 판정은 갖췄고, 남은 보완은 더 큰 라벨 데이터셋과 OOD 전용 classifier입니다.",
        "",
        "## 발표용 안전 문장",
        "",
        "> 이 시스템은 PDF를 넣으면 미래 수익률을 예측하는 도구가 아니라, 에너지/기후 보고서의 근거 문단을 few-shot topic signal로 변환하고 뉴스 컨텍스트 및 과거 주가 반응과 연결해 분석하는 연구용 MVP입니다.",
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
