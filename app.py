import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from report_signal_pipeline import (  # noqa: E402
    EmbeddingModel,
    FEW_SHOT_EXAMPLES,
    ReportMeta,
    extract_pdf_text_from_path,
    few_shot_scores,
    make_extractive_summaries,
    retrieve_evidence,
    split_paragraphs,
)
from config import FIGURES_DIR, PROCESSED_DIR, STOCK_WEEKLY_PATH  # noqa: E402

UPLOAD_DIR = ROOT / "outputs" / "uploads"
MARKET_COLUMNS = ["ET_SPREAD", "ICLN", "XLE", "NEE", "XOM", "ETN"]
ALLOWED_FIGURES = {
    "fig1_timeseries.png",
    "fig2_lag_heatmap.png",
    "fig3_rolling_corr.png",
    "fig4_company_sensitivity.png",
    "fig5_report_signals.png",
}

THEME_KOREAN = {
    "renewable_opportunity": "재생에너지 기회",
    "fossil_pressure": "화석연료 전환 압력",
    "grid_infrastructure": "전력망/전기화",
    "climate_risk": "기후 리스크",
}

_embedder: EmbeddingModel | None = None


def get_embedder() -> EmbeddingModel:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingModel()
    return _embedder


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_embedder()
    yield


app = FastAPI(title="Energy Report-to-Market Signal Analyzer", lifespan=lifespan)


def _compute_returns(scores: pd.DataFrame, horizons: list[int]) -> dict:
    if not STOCK_WEEKLY_PATH.exists():
        return {}
    stock = pd.read_csv(STOCK_WEEKLY_PATH, index_col=0, parse_dates=True).sort_index()
    if not set(MARKET_COLUMNS).issubset(stock.columns):
        return {}

    score = scores.iloc[0]
    report_date = pd.Timestamp(score["date"])
    result: dict = {"report_date": str(score["date"])}

    prior = stock[stock.index <= report_date].tail(4)
    if len(prior) == 4:
        for col, val in ((1 + prior[MARKET_COLUMNS]).prod() - 1).items():
            result[f"pre_4w_{col}"] = round(float(val), 4)

    for h in horizons:
        future = stock[stock.index > report_date].head(h)
        if len(future) != h:
            continue
        for col, val in ((1 + future[MARKET_COLUMNS]).prod() - 1).items():
            result[f"forward_{h}w_{col}"] = round(float(val), 4)

    return result


def _interpret_evidence(theme: str, paragraph: str) -> str:
    text = paragraph.lower()
    signals = []

    keyword_groups = [
        (["solar", "wind", "renewable", "clean energy", "capacity"], "재생에너지 확대 또는 청정에너지 투자"),
        (["oil", "gas", "fossil", "methane", "carbon", "emissions"], "화석연료 산업의 배출 감축 또는 전환 압력"),
        (["grid", "transmission", "distribution", "electricity", "electrification", "power"], "전력망, 송배전, 전기화 인프라"),
        (["climate", "weather", "heat", "drought", "risk", "resilience"], "기후 변화와 물리적 리스크"),
        (["investment", "demand", "policy", "regulation", "cost"], "투자, 수요, 정책 변화"),
    ]
    for keywords, label in keyword_groups:
        if any(keyword in text for keyword in keywords):
            signals.append(label)

    if not signals:
        signals.append("에너지 전환 관련 표현")

    theme_label = THEME_KOREAN.get(theme, theme)
    signal_text = ", ".join(dict.fromkeys(signals[:3]))
    return (
        f"이 문단은 {signal_text} 요소를 포함하고 있어 "
        f"`{theme_label}` 신호의 근거로 선택되었습니다. "
        "즉, 문서 안에서 해당 시장 테마와 연결될 수 있는 내용으로 해석할 수 있습니다."
    )


@app.post("/api/analyze")
async def analyze_pdf(
    file: UploadFile = File(...),
    title: str = Form("Uploaded Energy Report"),
    issuer: str = Form("User Upload"),
    report_date: str = Form("2024-01-01"),
    max_pages: int = Form(80),
    top_k: int = Form(10),
    horizons: str = Form("1,4,8"),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF 파일만 업로드할 수 있습니다.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name.replace(" ", "_")
    pdf_path = UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}_{safe_name}"
    pdf_path.write_bytes(await file.read())

    horizon_list = [int(h.strip()) for h in horizons.split(",") if h.strip().isdigit()]

    try:
        report = ReportMeta(
            report_id="uploaded_pdf",
            title=title,
            date=report_date,
            issuer=issuer,
            path=str(pdf_path),
            source_url="user_upload",
        )
        pages = extract_pdf_text_from_path(pdf_path, max_pages=max_pages)
        paragraphs = split_paragraphs(report, pages)
        if not paragraphs:
            raise ValueError("PDF에서 분석 가능한 문단을 추출하지 못했습니다.")

        paragraphs_df = pd.DataFrame(paragraphs)
        evidence = retrieve_evidence(paragraphs_df, top_k=top_k)
        if evidence.empty:
            raise ValueError("에너지 전환 관련 근거 문단을 찾지 못했습니다.")

        embedder = get_embedder()
        scores = few_shot_scores(evidence, embedder)
        summaries = make_extractive_summaries(evidence, scores, sentences_per_report=5)

        s = scores.iloc[0].to_dict()
        theme_scores = {
            "renewable_opportunity": round(s["renewable_opportunity"], 4),
            "fossil_pressure": round(s["fossil_pressure"], 4),
            "grid_infrastructure": round(s["grid_infrastructure"], 4),
            "climate_risk": round(s["climate_risk"], 4),
            "transition_signal": round(s["transition_signal"], 4),
            "asset_hint": s["asset_hint"],
        }

        sorted_themes = sorted(
            [(k, theme_scores[k]) for k in ["renewable_opportunity", "fossil_pressure", "grid_infrastructure", "climate_risk"]],
            key=lambda x: x[1],
            reverse=True,
        )
        margin = sorted_themes[0][1] - sorted_themes[1][1]
        confidence_level = "높음" if margin >= 0.04 else ("보통" if margin >= 0.015 else "낮음")

        evidence_by_theme = {
            theme: [
                {
                    "page": int(r["page"]),
                    "rank": int(r["rank"]),
                    "score": round(float(r["retrieval_score"]), 4),
                    "paragraph": r["paragraph"],
                    "interpretation": _interpret_evidence(theme, r["paragraph"]),
                }
                for _, r in evidence[evidence["theme"] == theme]
                .sort_values("retrieval_score", ascending=False)
                .head(top_k)
                .iterrows()
            ]
            for theme in FEW_SHOT_EXAMPLES
        }

        return JSONResponse(
            {
                "status": "success",
                "scores": theme_scores,
                "confidence": {
                    "level": confidence_level,
                    "margin": round(margin, 4),
                    "top_theme": sorted_themes[0][0],
                },
                "summary": {
                    "korean": summaries.iloc[0]["plain_korean_explanation"],
                    "bullets": summaries.iloc[0]["simple_summary"],
                },
                "evidence": evidence_by_theme,
                "returns": _compute_returns(scores, horizon_list),
                "stats": {
                    "pages": len(pages),
                    "paragraphs": len(paragraphs_df),
                    "evidence_count": len(evidence),
                },
            }
        )

    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"분석 중 오류가 발생했습니다: {e}")
    finally:
        pdf_path.unlink(missing_ok=True)


@app.get("/api/dashboard")
async def get_dashboard():
    signals, stock_link = [], []
    signals_path = PROCESSED_DIR / "reports" / "report_signals.csv"
    link_path = PROCESSED_DIR / "reports" / "report_stock_link.csv"
    if signals_path.exists():
        signals = pd.read_csv(signals_path).round(4).to_dict(orient="records")
    if link_path.exists():
        stock_link = pd.read_csv(link_path).round(4).to_dict(orient="records")
    return JSONResponse({"signals": signals, "stock_link": stock_link})


@app.get("/api/figures/{name}")
async def get_figure(name: str):
    if name not in ALLOWED_FIGURES:
        raise HTTPException(404, "Figure not found")
    fig_path = FIGURES_DIR / name
    if not fig_path.exists():
        raise HTTPException(404, "Figure not found")
    return FileResponse(fig_path, media_type="image/png")


app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


@app.get("/{full_path:path}")
async def catch_all():
    return FileResponse(str(ROOT / "static" / "index.html"))
