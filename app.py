import json
import os
import sys
import urllib.request
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
    ReportMeta,
    SCORING_REFERENCE_EXAMPLES,
    attach_news_context_to_report_scores,
    extract_pdf_text_from_path,
    make_extractive_summaries,
    retrieve_evidence,
    score_evidence_with_few_shot_learning,
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
_local_genai: dict | None = None


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


def _json_records(df: pd.DataFrame) -> list[dict]:
    clean = df.astype(object).where(pd.notna(df), None)
    return clean.to_dict(orient="records")


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


def _load_local_genai(model_id: str) -> dict:
    global _local_genai
    if _local_genai and _local_genai.get("model_id") == model_id:
        return _local_genai

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32, low_cpu_mem_usage=True)
    model.eval()
    _local_genai = {"model_id": model_id, "tokenizer": tokenizer, "model": model}
    return _local_genai


def _run_local_genai(model_id: str, title: str, evidence: pd.DataFrame) -> dict:
    import torch

    bundle = _load_local_genai(model_id)
    tokenizer = bundle["tokenizer"]
    model = bundle["model"]

    context = "\n".join(
        f"- {row['theme']} p.{row['page']}: {row['paragraph'][:550]}"
        for _, row in evidence.sort_values("retrieval_score", ascending=False).head(6).iterrows()
    )
    messages = [
        {"role": "system", "content": "You are a cautious energy-market research assistant."},
        {
            "role": "user",
            "content": (
                "다음 PDF 근거를 바탕으로 에너지 전환, 뉴스 분위기, 주가 downstream 연결 관점에서 "
                "한국어로 3문장 이내로 요약해줘. 투자 추천이나 미래 수익률 예측처럼 말하지 마.\n\n"
                f"보고서 제목: {title}\n근거:\n{context}"
            ),
        },
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt")
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=int(os.getenv("LOCAL_GENAI_MAX_TOKENS", "180")),
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = output[0][inputs.input_ids.shape[-1] :]
    return {
        "enabled": True,
        "provider": "local_huggingface_transformers",
        "model": model_id,
        "summary": tokenizer.decode(generated, skip_special_tokens=True).strip(),
        "note": "",
    }


def _evidence_context(evidence: pd.DataFrame, limit: int, chars: int) -> str:
    return "\n".join(
        f"- {row['theme']} p.{row['page']}: {row['paragraph'][:chars]}"
        for _, row in evidence.sort_values("retrieval_score", ascending=False).head(limit).iterrows()
    )


def _run_gemini_summary(api_key: str, model: str, title: str, evidence: pd.DataFrame) -> dict:
    context = _evidence_context(evidence, limit=8, chars=700)
    prompt = (
        "Summarize the following PDF evidence in Korean within 3-5 sentences. "
        "Connect it to energy transition, news-sentiment context, and downstream stock-return analysis. "
        "Use cautious research wording. Do not provide investment advice or future return predictions.\n\n"
        f"Report title: {title}\nEvidence:\n{context}"
    )
    thinking_config = {}
    thinking_capable = any(model.startswith(p) for p in ("gemini-2.5", "gemini-3"))
    if thinking_capable:
        thinking_config["thinkingBudget"] = int(os.getenv("GEMINI_THINKING_BUDGET", "1024"))

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": (
                        "You are a cautious energy-market research assistant. "
                        "Explain model outputs as research signals, not investment recommendations."
                    )
                }
            ]
        },
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "600")),
            "thinkingConfig": thinking_config,
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts).strip()
        return {
            "enabled": bool(text),
            "provider": "google_gemini",
            "model": model,
            "summary": text,
            "note": "" if text else "Gemini returned no text.",
        }
    except Exception as exc:
        return {
            "enabled": False,
            "provider": "google_gemini",
            "model": model,
            "summary": "",
            "note": f"Gemini call failed: {exc}",
        }


def _optional_generative_summary(title: str, evidence: pd.DataFrame) -> dict:
    provider = os.getenv("GENAI_PROVIDER", "").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    api_url = os.getenv("GENAI_API_URL")
    api_key = os.getenv("GENAI_API_KEY")
    model = os.getenv("GENAI_MODEL", "large-generative-model")
    local_model = os.getenv("LOCAL_GENAI_MODEL")
    if gemini_key and (provider in {"", "gemini", "google"} or not api_url):
        return _run_gemini_summary(gemini_key, gemini_model, title, evidence)
    if not api_url or not api_key:
        if local_model:
            return _run_local_genai(local_model, title, evidence)
        return {
            "enabled": False,
            "model": gemini_model,
            "summary": "",
            "note": "Set GEMINI_API_KEY, GENAI_API_URL/GENAI_API_KEY, or LOCAL_GENAI_MODEL to enable generative summaries.",
        }

    context = _evidence_context(evidence, limit=8, chars=700)
    prompt = (
        "You are an energy-market research assistant. Summarize how this PDF evidence connects "
        "to renewable energy, fossil transition pressure, grid infrastructure, climate risk, "
        "news sentiment, and downstream stock-return analysis. Keep the answer cautious and do "
        "not make investment recommendations.\n\n"
        f"Report title: {title}\nEvidence:\n{context}"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Use cautious research language."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }
    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"enabled": True, "model": model, "summary": content.strip(), "note": ""}
    except Exception as exc:
        return {"enabled": False, "model": model, "summary": "", "note": f"Generative model call failed: {exc}"}


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
        scores = score_evidence_with_few_shot_learning(evidence, embedder)
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
        confidence_level = "높음" if margin >= 0.25 else ("보통" if margin >= 0.10 else "낮음")

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
            for theme in SCORING_REFERENCE_EXAMPLES
        }

        return JSONResponse(
            {
                "status": "success",
                "methodology": {
                    "base_model": "sentence-transformers/all-MiniLM-L6-v2",
                    "few_shot_learning": "Frozen MiniLM embeddings + logistic regression classifier heads (top-30% evidence aggregation, per-report min-max normalization).",
                    "generative_model": "Gemini 2.5 Flash summary when GEMINI_API_KEY is configured; API/local fallbacks are also supported.",
                },
                "scores": theme_scores,
                "confidence": {
                    "level": confidence_level,
                    "margin": round(margin, 4),
                    "top_theme": sorted_themes[0][0],
                },
                "summary": {
                    "korean": summaries.iloc[0]["plain_korean_explanation"],
                    "bullets": summaries.iloc[0]["simple_summary"],
                    "generative": _optional_generative_summary(title, evidence),
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
    signals, stock_link, news_bridge, validation = [], [], [], []
    signals_path = PROCESSED_DIR / "reports" / "report_signals.csv"
    link_path = PROCESSED_DIR / "reports" / "report_stock_link.csv"
    news_bridge_path = PROCESSED_DIR / "reports" / "report_news_bridge.csv"
    validation_path = PROCESSED_DIR / "reports" / "expanded_pdf_validation.csv"
    if signals_path.exists():
        signals_df = pd.read_csv(signals_path).round(4)
        signals = _json_records(signals_df)
        if news_bridge_path.exists():
            news_bridge = _json_records(pd.read_csv(news_bridge_path).round(4))
        else:
            news_bridge = _json_records(attach_news_context_to_report_scores(signals_df).round(4))
    if link_path.exists():
        stock_link = _json_records(pd.read_csv(link_path).round(4))
    if validation_path.exists():
        validation = _json_records(pd.read_csv(validation_path))
    return JSONResponse(
        {
            "signals": signals,
            "stock_link": stock_link,
            "news_bridge": news_bridge,
            "validation": validation,
            "methodology": {
                "base_model": "sentence-transformers/all-MiniLM-L6-v2",
                "few_shot_learning": "Frozen Transformer embeddings + few-shot logistic heads (top-30% aggregation, per-report min-max normalization). Dashboard scores are from the initial pipeline run (pre-normalization).",
                "news_pdf_bridge": "News sentiment is aggregated around each report date and joined to PDF event scores.",
                "generative_model": "Gemini 2.5 Flash summary with cautious research wording.",
            },
        }
    )


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
