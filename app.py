import json
import os
import hashlib
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

from config import FIGURES_DIR, PROCESSED_DIR, STOCK_WEEKLY_PATH  # noqa: E402
from report_signal_pipeline import (  # noqa: E402
    EmbeddingModel,
    EVENT_WINDOWS,
    ReportMeta,
    SCORING_REFERENCE_EXAMPLES,
    attach_news_context_to_report_scores,
    compound_returns,
    evidence_support_metadata,
    extract_pdf_text_from_path,
    label_evidence_chunks,
    make_extractive_summaries,
    retrieve_evidence,
    score_evidence_with_few_shot_learning,
    split_paragraphs,
    summarize_chunk_labels,
)

UPLOAD_DIR = ROOT / "outputs" / "uploads"
ANALYSIS_CACHE_DIR = ROOT / "outputs" / "cache"
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
    "grid_infrastructure": "전력망/전기화 인프라",
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

    market_assets = ["ICLN", "XLE", "NEE", "XOM", "ETN"]
    for label, (start_offset, end_offset) in EVENT_WINDOWS.items():
        if start_offset < 0:
            start = report_date + pd.Timedelta(weeks=start_offset)
            window = stock[(stock.index > start) & (stock.index <= report_date)]
        else:
            end = report_date + pd.Timedelta(weeks=end_offset)
            window = stock[(stock.index > report_date) & (stock.index <= end)]
        if window.empty:
            continue
        asset_returns = compound_returns(window, market_assets)
        benchmark = float(asset_returns.mean())
        result[f"{label}_benchmark_equal_weight"] = round(benchmark, 4)
        result[f"{label}_n_weeks"] = int(len(window))
        for col, value in asset_returns.items():
            result[f"{label}_{col}"] = round(float(value), 4)
            result[f"{label}_abnormal_{col}"] = round(float(value - benchmark), 4)

    return result


def _json_records(df: pd.DataFrame) -> list[dict]:
    clean = df.astype(object).where(pd.notna(df), None)
    return clean.to_dict(orient="records")


def _analysis_cache_key(pdf_bytes: bytes, params: dict) -> str:
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    params_digest = hashlib.sha256(json.dumps(params, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"{digest[:24]}_{params_digest}"


def _read_analysis_cache(cache_key: str) -> dict | None:
    path = ANALYSIS_CACHE_DIR / f"{cache_key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_analysis_cache(cache_key: str, payload: dict) -> None:
    ANALYSIS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = ANALYSIS_CACHE_DIR / f"{cache_key}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _interpret_evidence(theme: str, paragraph: str) -> str:
    text = paragraph.lower()
    signals = []
    keyword_groups = [
        (["solar", "wind", "renewable", "clean energy", "capacity"], "재생에너지 확대 또는 청정에너지 투자"),
        (["oil", "gas", "fossil", "methane", "carbon", "emissions"], "화석연료 산업의 배출 감축 또는 전환 압력"),
        (["grid", "transmission", "distribution", "electricity", "electrification", "power"], "전력망 확장 또는 전기화 인프라"),
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
        "문서 안에서 해당 시장 테마와 연결될 수 있는 내용으로 해석할 수 있습니다."
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

    context = _evidence_context(evidence, limit=6, chars=550)
    messages = [
        {"role": "system", "content": "You are a cautious energy-market research assistant."},
        {
            "role": "user",
            "content": (
                "다음 PDF 근거를 바탕으로 에너지 전환, 뉴스 분위기, 주가 downstream 연결 관점에서 "
                "한국어로 3문장 이내로 요약해 주세요. 투자 추천이나 미래 수익률 예측처럼 말하지 마세요.\n\n"
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
        f"- {row['theme']} {row.get('chunk_id', 'p.' + str(row['page']))}: {row['paragraph'][:chars]}"
        for _, row in evidence.sort_values("retrieval_score", ascending=False).head(limit).iterrows()
    )


def _run_gemini_summary(api_key: str, model: str, title: str, evidence: pd.DataFrame) -> dict:
    context = _evidence_context(evidence, limit=8, chars=700)
    prompt = (
        "Summarize the following PDF evidence in Korean within 3-5 sentences. "
        "Connect it to energy transition, news-sentiment context, and downstream stock-return analysis. "
        "Use cautious research wording. Do not provide investment advice or future return predictions. "
        "Only use claims supported by the evidence chunks shown below. If evidence is weak or mixed, say so explicitly.\n\n"
        f"Report title: {title}\nEvidence:\n{context}"
    )
    thinking_config = {}
    if model.startswith("gemini-3"):
        thinking_config["thinkingLevel"] = os.getenv("GEMINI_THINKING_LEVEL", "high")
    elif model.startswith("gemini-2.5"):
        thinking_config["thinkingBudget"] = int(os.getenv("GEMINI_THINKING_BUDGET", "1024"))

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": (
                        "You are a cautious energy-market research assistant. "
                        "Explain model outputs as research signals, not investment recommendations. "
                        "Do not add facts that are absent from the provided evidence chunks."
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
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
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
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    api_url = os.getenv("GENAI_API_URL")
    api_key = os.getenv("GENAI_API_KEY")
    model = os.getenv("GENAI_MODEL", "large-generative-model")
    local_model = os.getenv("LOCAL_GENAI_MODEL")
    if gemini_key and (provider in {"", "gemini", "google"} or not api_url):
        result = _run_gemini_summary(gemini_key, gemini_model, title, evidence)
        result.update(evidence_support_metadata(evidence))
        return result
    if not api_url or not api_key:
        if local_model:
            result = _run_local_genai(local_model, title, evidence)
            result.update(evidence_support_metadata(evidence))
            return result
        return {
            "enabled": False,
            "model": gemini_model,
            "summary": "",
            "note": "Set GEMINI_API_KEY, GENAI_API_URL/GENAI_API_KEY, or LOCAL_GENAI_MODEL to enable generative summaries.",
            **evidence_support_metadata(evidence),
        }

    context = _evidence_context(evidence, limit=8, chars=700)
    prompt = (
        "You are an energy-market research assistant. Summarize how this PDF evidence connects "
        "to renewable energy, fossil transition pressure, grid infrastructure, climate risk, "
        "news sentiment, and downstream stock-return analysis. Keep the answer cautious and do "
        "not make investment recommendations.\n\n"
        f"Report title: {title}\nEvidence:\n{context}"
    )
    request = urllib.request.Request(
        api_url,
        data=json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": "Use cautious research language."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 500,
            }
        ).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        result = {"enabled": True, "model": model, "summary": content.strip(), "note": ""}
        result.update(evidence_support_metadata(evidence))
        return result
    except Exception as exc:
        result = {"enabled": False, "model": model, "summary": "", "note": f"Generative model call failed: {exc}"}
        result.update(evidence_support_metadata(evidence))
        return result


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
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF 파일만 업로드할 수 있습니다.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name.replace(" ", "_")
    pdf_path = UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}_{safe_name}"
    pdf_bytes = await file.read()
    horizon_list = [int(h.strip()) for h in horizons.split(",") if h.strip().isdigit()]
    cache_params = {
        "title": title,
        "issuer": issuer,
        "report_date": report_date,
        "max_pages": max_pages,
        "top_k": top_k,
        "horizons": horizon_list,
        "pipeline_version": "2026-06-02-chunk-multilabel-ood-evidence-v4",
    }
    cache_key = _analysis_cache_key(pdf_bytes, cache_params)
    cached = _read_analysis_cache(cache_key)
    if cached is not None:
        cached["cache"] = {"hit": True, "key": cache_key}
        return JSONResponse(cached)

    pdf_path.write_bytes(pdf_bytes)

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
        embedder = get_embedder()
        evidence = retrieve_evidence(paragraphs_df, top_k=top_k, embedder=embedder, hybrid=True)
        if evidence.empty:
            raise ValueError("에너지 전환 관련 근거 문단을 찾지 못했습니다.")

        scores = score_evidence_with_few_shot_learning(evidence, embedder)
        chunk_labels = label_evidence_chunks(evidence)
        chunk_label_summary = summarize_chunk_labels(chunk_labels)
        summaries = make_extractive_summaries(evidence, scores, sentences_per_report=5)

        s = scores.iloc[0].to_dict()
        theme_scores = {
            "renewable_opportunity": round(s["renewable_opportunity"], 4),
            "fossil_pressure": round(s["fossil_pressure"], 4),
            "grid_infrastructure": round(s["grid_infrastructure"], 4),
            "climate_risk": round(s["climate_risk"], 4),
            "transition_signal": round(s["transition_signal"], 4),
            "asset_hint": s["asset_hint"],
            "energy_relevance": round(s["energy_relevance"], 4),
            "ood_decision": s["ood_decision"],
            "ood_subtype": s.get("ood_subtype", "unknown"),
        }
        raw_scores = {
            "renewable_opportunity": round(s["renewable_opportunity_raw"], 4),
            "fossil_pressure": round(s["fossil_pressure_raw"], 4),
            "grid_infrastructure": round(s["grid_infrastructure_raw"], 4),
            "climate_risk": round(s["climate_risk_raw"], 4),
            "transition_signal": round(s["transition_signal_raw"], 4),
        }
        sorted_themes = sorted(
            [(k, theme_scores[k]) for k in THEME_KOREAN],
            key=lambda x: x[1],
            reverse=True,
        )
        margin = sorted_themes[0][1] - sorted_themes[1][1]
        theme_scores.update(
            {
                "top_theme": s.get("top_theme", sorted_themes[0][0]),
                "second_theme": s.get("second_theme", sorted_themes[1][0]),
                "score_margin": round(float(s.get("score_margin", margin)), 4),
                "mixed_signal": bool(s.get("mixed_signal", False)),
                "mixed_components": s.get("mixed_components", ""),
            }
        )
        confidence_level = "높음" if margin >= 0.25 else ("보통" if margin >= 0.10 else "낮음")
        if s["ood_decision"] != "in_domain":
            confidence_level = "낮음"

        evidence_by_theme = {
            theme: [
                {
                    "page": int(r["page"]),
                    "rank": int(r["rank"]),
                    "score": round(float(r["retrieval_score"]), 4),
                    "tfidf_score": round(float(r.get("tfidf_score", 0.0)), 4),
                    "embedding_score": round(float(r.get("embedding_score", 0.0)), 4),
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

        payload = {
            "status": "success",
            "methodology": {
                "base_model": "sentence-transformers/all-MiniLM-L6-v2",
                "few_shot_learning": "Frozen MiniLM embeddings + cached logistic regression classifier heads.",
                "retrieval": "TF-IDF + embedding hybrid evidence retrieval.",
                "ood_guard": "Energy relevance score combines retrieval strength, keyword coverage, and raw classifier confidence.",
                "generative_model": "Gemini summary when GEMINI_API_KEY is configured; summaries include evidence chunk IDs for review.",
                "chunk_multilabel": "Retrieved paragraphs are weak-labeled by theme so mixed PDFs can be audited below document level.",
            },
            "scores": theme_scores,
            "raw_scores": raw_scores,
            "confidence": {
                "level": confidence_level,
                "margin": round(float(s.get("score_margin", margin)), 4),
                "top_theme": s.get("top_theme", sorted_themes[0][0]),
                "second_theme": s.get("second_theme", sorted_themes[1][0]),
                "mixed_signal": bool(s.get("mixed_signal", False)),
                "mixed_components": s.get("mixed_components", ""),
                "energy_relevance": round(s["energy_relevance"], 4),
                "ood_decision": s["ood_decision"],
                "ood_subtype": s.get("ood_subtype", "unknown"),
            },
            "summary": {
                "korean": summaries.iloc[0]["plain_korean_explanation"],
                "bullets": summaries.iloc[0]["simple_summary"],
                "evidence_chunk_ids": summaries.iloc[0].get("evidence_chunk_ids", ""),
                "support_level": summaries.iloc[0].get("support_level", ""),
                "support_note": summaries.iloc[0].get("support_note", ""),
                "generative": _optional_generative_summary(title, evidence),
            },
            "evidence": evidence_by_theme,
            "chunk_labels": _json_records(chunk_labels.head(200)),
            "chunk_label_summary": chunk_label_summary,
            "returns": _compute_returns(scores, horizon_list),
            "stats": {
                "pages": len(pages),
                "paragraphs": len(paragraphs_df),
                "evidence_count": len(evidence),
            },
            "cache": {"hit": False, "key": cache_key},
        }
        _write_analysis_cache(cache_key, payload)
        return JSONResponse(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"분석 중 오류가 발생했습니다: {exc}")
    finally:
        pdf_path.unlink(missing_ok=True)


@app.get("/api/dashboard")
async def get_dashboard():
    paths = {
        "signals": PROCESSED_DIR / "reports" / "report_signals.csv",
        "stock_link": PROCESSED_DIR / "reports" / "report_stock_link.csv",
        "news_bridge": PROCESSED_DIR / "reports" / "report_news_bridge.csv",
        "validation": PROCESSED_DIR / "reports" / "expanded_pdf_validation.csv",
        "actual_news_stock": PROCESSED_DIR / "reports" / "actual_news_stock_best_lag.csv",
        "actual_climate_news": PROCESSED_DIR / "reports" / "actual_climate_news_lag_corr.csv",
        "pdf_metrics": PROCESSED_DIR / "reports" / "pdf_validation_metrics.csv",
        "pdf_confusion": PROCESSED_DIR / "reports" / "pdf_validation_confusion_matrix.csv",
        "label_rationale": PROCESSED_DIR / "reports" / "pdf_validation_label_rationale.csv",
        "failure_analysis": PROCESSED_DIR / "reports" / "pdf_validation_failure_analysis.csv",
        "gemini_check": PROCESSED_DIR / "reports" / "gemini_summary_human_check.csv",
        "out_of_domain": PROCESSED_DIR / "reports" / "out_of_domain_pdf_test.csv",
        "zero_shot_vs_few_shot": PROCESSED_DIR / "reports" / "zero_shot_vs_few_shot.csv",
        "pdf_chunk_labels": PROCESSED_DIR / "reports" / "pdf_validation_chunk_labels.csv",
    }
    data = {key: [] for key in paths}
    if paths["signals"].exists():
        signals_df = pd.read_csv(paths["signals"]).round(4)
        data["signals"] = _json_records(signals_df)
        if paths["news_bridge"].exists():
            data["news_bridge"] = _json_records(pd.read_csv(paths["news_bridge"]).round(4))
        else:
            data["news_bridge"] = _json_records(attach_news_context_to_report_scores(signals_df).round(4))

    for key, path in paths.items():
        if key in {"signals", "news_bridge"} or not path.exists():
            continue
        df = pd.read_csv(path)
        if key == "pdf_confusion":
            df = df.reset_index()
        try:
            df = df.round(4)
        except TypeError:
            pass
        data[key] = _json_records(df)

    data["methodology"] = {
        "base_model": "sentence-transformers/all-MiniLM-L6-v2",
        "few_shot_learning": "Frozen Transformer embeddings + few-shot logistic heads.",
        "news_pdf_bridge": "GDELT weekly tone samples are joined to PDF event scores.",
        "generative_model": "Gemini summary with cautious research wording.",
        "chunk_multilabel": "Validation includes paragraph-level weak multi-labels; human multi-label annotation is still required.",
    }
    return JSONResponse(data)


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
async def catch_all(full_path: str):
    return FileResponse(str(ROOT / "static" / "index.html"))
