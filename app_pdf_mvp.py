from datetime import date
from pathlib import Path
import sys
import uuid

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from report_signal_pipeline import (  # noqa: E402
    EmbeddingModel,
    ReportMeta,
    extract_pdf_text_from_path,
    few_shot_scores,
    link_to_stock_returns,
    make_extractive_summaries,
    retrieve_evidence,
    split_paragraphs,
)


UPLOAD_DIR = ROOT / "outputs" / "uploads"

THEME_LABELS = {
    "renewable_opportunity": "재생에너지 기회",
    "fossil_pressure": "화석연료 압력",
    "grid_infrastructure": "전력망/전기화",
    "climate_risk": "기후 리스크",
}


@st.cache_resource(show_spinner=False)
def load_embedder():
    return EmbeddingModel()


def save_uploaded_file(uploaded_file):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name.replace(" ", "_")
    output = UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}_{safe_name}"
    output.write_bytes(uploaded_file.getbuffer())
    return output


def run_uploaded_pdf_pipeline(pdf_path, title, issuer, report_date, max_pages, top_k):
    report = ReportMeta(
        report_id="uploaded_pdf",
        title=title,
        date=str(report_date),
        issuer=issuer,
        path=str(pdf_path),
        source_url="user_upload",
    )

    pages = extract_pdf_text_from_path(pdf_path, max_pages=max_pages)
    paragraphs = split_paragraphs(report, pages)
    if not paragraphs:
        raise RuntimeError("PDF에서 분석 가능한 문단을 추출하지 못했습니다.")

    paragraphs_df = pd.DataFrame(paragraphs)
    evidence = retrieve_evidence(paragraphs_df, top_k=top_k)
    if evidence.empty:
        raise RuntimeError("에너지 전환 관련 근거 문단을 찾지 못했습니다.")

    embedder = load_embedder()
    scores = few_shot_scores(evidence, embedder)
    summaries = make_extractive_summaries(evidence, scores, sentences_per_report=5)

    linked = pd.DataFrame()
    try:
        linked = link_to_stock_returns(scores, horizon_weeks=4)
    except Exception:
        linked = pd.DataFrame()

    return pages, paragraphs_df, evidence, scores, summaries, linked


def render_score_cards(score):
    cols = st.columns(5)
    metrics = [
        ("재생에너지", score["renewable_opportunity"]),
        ("화석연료 압력", score["fossil_pressure"]),
        ("전력망/전기화", score["grid_infrastructure"]),
        ("기후 리스크", score["climate_risk"]),
        ("전환 신호", score["transition_signal"]),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, f"{value:.3f}")


def main():
    st.set_page_config(
        page_title="PDF Report-to-Market Signal MVP",
        page_icon="📄",
        layout="wide",
    )

    st.title("PDF Report-to-Market Signal MVP")
    st.caption(
        "PDF를 업로드하면 텍스트 추출, 근거 문단 검색, Foundation Model 임베딩, few-shot 점수화를 거쳐 시장 신호를 생성합니다."
    )

    with st.sidebar:
        st.header("PDF 입력")
        uploaded_file = st.file_uploader("분석할 PDF", type=["pdf"])
        title = st.text_input("보고서 제목", value="Uploaded Energy Report")
        issuer = st.text_input("발행 기관/기업", value="User Upload")
        report_date = st.date_input("보고서 기준일", value=date(2024, 1, 1))
        max_pages = st.slider("분석할 최대 페이지 수", 10, 200, 80, step=10)
        top_k = st.slider("주제별 근거 문단 수", 3, 20, 10)
        run_button = st.button("PDF 분석 실행", type="primary", use_container_width=True)

    st.subheader("작동 방식")
    st.markdown(
        """
        1. PDF에서 텍스트를 뽑습니다.
        2. 에너지 전환과 관련된 문단을 찾습니다.
        3. `sentence-transformers/all-MiniLM-L6-v2`로 문단 의미를 벡터로 바꿉니다.
        4. few-shot 예시 문장과 비교해 `재생에너지`, `화석연료 압력`, `전력망`, `기후 리스크` 점수를 만듭니다.
        5. 보고서 날짜 이후 4주 주가 수익률과 연결할 수 있으면 함께 보여줍니다.
        """
    )

    if not run_button:
        st.info("왼쪽에서 PDF를 선택하고 `PDF 분석 실행`을 누르면 실제 분석 결과가 표시됩니다.")
        return

    if uploaded_file is None:
        st.error("먼저 PDF 파일을 업로드하세요.")
        return

    pdf_path = save_uploaded_file(uploaded_file)

    try:
        with st.spinner("PDF를 분석하는 중입니다. 첫 실행은 모델 로딩 때문에 시간이 걸릴 수 있습니다."):
            pages, paragraphs, evidence, scores, summaries, linked = run_uploaded_pdf_pipeline(
                pdf_path=pdf_path,
                title=title,
                issuer=issuer,
                report_date=report_date,
                max_pages=max_pages,
                top_k=top_k,
            )
    except Exception as exc:
        st.error(f"분석 중 오류가 발생했습니다: {exc}")
        st.stop()

    score = scores.iloc[0]

    st.success("분석이 완료되었습니다.")
    st.caption(f"저장된 업로드 파일: `{pdf_path}`")

    st.subheader("1. 핵심 점수")
    render_score_cards(score)
    st.write(
        f"가장 강한 자산 힌트는 **{score['asset_hint']}** 입니다. "
        "이 값은 투자 추천이 아니라, 보고서 내용이 어떤 산업 신호와 가장 가까운지 보여주는 분류 결과입니다."
    )

    chart_df = (
        scores[
            [
                "renewable_opportunity",
                "fossil_pressure",
                "grid_infrastructure",
                "climate_risk",
            ]
        ]
        .rename(columns=THEME_LABELS)
        .T
    )
    chart_df.columns = ["점수"]
    st.bar_chart(chart_df)

    st.subheader("2. 쉬운 요약")
    st.write(summaries.iloc[0]["plain_korean_explanation"])
    st.write(summaries.iloc[0]["simple_summary"])

    st.subheader("3. 근거 문단")
    theme_filter = st.selectbox("주제 선택", options=list(THEME_LABELS), format_func=lambda x: THEME_LABELS[x])
    filtered = evidence[evidence["theme"] == theme_filter].sort_values("retrieval_score", ascending=False)
    st.dataframe(
        filtered[["page", "rank", "retrieval_score", "paragraph"]].head(top_k),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("4. 보고서 날짜 이후 4주 수익률 연결")
    if linked.empty:
        st.warning("보고서 날짜 이후 주가 데이터가 부족하거나 날짜 범위 밖이라 4주 수익률을 계산하지 못했습니다.")
    else:
        display_cols = [
            "forward_4w_ET_SPREAD",
            "forward_4w_ICLN",
            "forward_4w_XLE",
            "forward_4w_NEE",
            "forward_4w_XOM",
            "forward_4w_ETN",
        ]
        available_cols = [col for col in display_cols if col in linked.columns]
        st.dataframe(linked[available_cols].round(4), use_container_width=True, hide_index=True)

    st.subheader("5. 처리 현황")
    st.write(f"추출 페이지 수: **{len(pages)}**")
    st.write(f"분석 문단 수: **{len(paragraphs)}**")
    st.write(f"선택된 근거 문단 수: **{len(evidence)}**")


if __name__ == "__main__":
    main()
