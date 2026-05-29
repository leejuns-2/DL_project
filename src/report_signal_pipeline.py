import re
from dataclasses import dataclass
from pathlib import Path

import fitz
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoModel, AutoTokenizer

from config import (
    FIGURES_DIR,
    NEWS_WEEKLY_PATH,
    PROCESSED_DIR,
    RAW_DIR,
    TABLES_DIR,
    STOCK_WEEKLY_PATH,
    ensure_project_dirs,
)


REPORT_DIR = RAW_DIR / "reports"
REPORT_PROCESSED_DIR = PROCESSED_DIR / "reports"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# This pipeline freezes the base Transformer and trains a small downstream
# classifier head from a handful of human-written examples. That is few-shot
# learning at the task-head level, not full foundation-model fine-tuning.


@dataclass
class ReportMeta:
    report_id: str
    title: str
    date: str
    issuer: str
    path: str
    source_url: str


REPORTS = [
    ReportMeta(
        "iea_weo_2023",
        "IEA World Energy Outlook 2023",
        "2023-10-24",
        "IEA",
        "iea_world_energy_outlook_2023.pdf",
        "https://iea.blob.core.windows.net/assets/42b23c45-78bc-4482-b0f9-eb826ae2da3d/WorldEnergyOutlook2023.pdf",
    ),
    ReportMeta(
        "iea_renewables_2023",
        "IEA Renewables 2023",
        "2024-01-11",
        "IEA",
        "iea_renewables_2023.pdf",
        "https://iea.blob.core.windows.net/assets/96d66a8b-d502-476b-ba94-54ffda84cf72/Renewables_2023.pdf",
    ),
    ReportMeta(
        "iea_oil_gas_nz_2023",
        "IEA Oil and Gas Industry in Net Zero Transitions",
        "2023-11-23",
        "IEA",
        "iea_oil_gas_net_zero_2023.pdf",
        "https://iea.blob.core.windows.net/assets/7a4b0c4e-d78c-4a8e-998c-6cde10a4e49b/TheOilandGasIndustryinNetZeroTransitions.pdf",
    ),
    ReportMeta(
        "exxon_acs_2023",
        "ExxonMobil Advancing Climate Solutions 2023",
        "2023-04-04",
        "ExxonMobil",
        "exxon_acs_2023.pdf",
        "https://corporate.exxonmobil.com/-/media/global/files/advancing-climate-solutions-progress-report/2023/2023-advancing-climate-solutions-progress-report.pdf",
    ),
    ReportMeta(
        "eaton_annual_2023",
        "Eaton Annual Report 2023",
        "2024-02-23",
        "Eaton",
        "eaton_annual_2023.pdf",
        "https://www.annualreports.com/HostedData/AnnualReportArchive/e/NYSE_ETN_2023.pdf",
    ),
]


THEME_QUERIES = {
    "renewable_opportunity": "renewable energy solar wind clean energy capacity investment growth opportunity",
    "fossil_pressure": "oil gas fossil fuel emissions methane transition risk carbon reduction pressure",
    "grid_infrastructure": "electricity grid transmission distribution power infrastructure electrification demand",
    "climate_risk": "climate change extreme weather heat drought emissions risk policy transition",
}


SCORING_REFERENCE_EXAMPLES = {
    "renewable_opportunity": [
        "Solar and wind capacity additions are expected to accelerate due to policy support and falling costs.",
        "Clean energy investment creates growth opportunities for renewable power developers and utilities.",
        "Renewable electricity deployment expands as countries increase energy transition targets.",
    ],
    "fossil_pressure": [
        "Oil and gas producers face transition pressure from emissions regulation and declining fossil fuel demand.",
        "Methane reduction, carbon pricing, and climate policy increase risks for fossil fuel assets.",
        "Fossil fuel companies must reduce emissions to remain aligned with net zero pathways.",
    ],
    "grid_infrastructure": [
        "Transmission bottlenecks and grid expansion needs are delaying renewable energy deployment.",
        "Electrification and data center demand increase investment needs for power management infrastructure.",
        "Power grids require modernization to support electric vehicles, heat pumps, and renewable generation.",
        "Electricity demand growth requires investment in generation, transmission, distribution, and power system flexibility.",
        "Power system reliability depends on grid upgrades, storage, demand response, and network infrastructure.",
        "Rising electricity consumption from cooling, industry, and data centers creates opportunities for electrical equipment suppliers.",
    ],
    "climate_risk": [
        "Extreme weather, heat waves, droughts, and physical climate risks affect energy systems.",
        "Climate change increases operational risks for infrastructure, utilities, and energy supply.",
        "Adaptation and resilience are required as climate hazards become more frequent.",
    ],
}


FEW_SHOT_NEGATIVE_EXAMPLES = [
    "The report focuses on general macroeconomic conditions without discussing energy systems.",
    "The company describes accounting policies and administrative matters with no climate signal.",
    "The document lists governance procedures that are unrelated to energy transition investment.",
    "The section contains historical financial statements without operational or policy evidence.",
]


VALIDATION_SAMPLE_PDFS = [
    {
        "report_id": "irena_global_renewables_outlook_2020",
        "title": "IRENA Global Renewables Outlook 2020",
        "date": "2020-04-20",
        "issuer": "IRENA",
        "path": "data/sample_pdfs/IRENA_Global_Renewables_Outlook_2020.pdf",
        "expected_hint": "ICLN/NEE",
    },
    {
        "report_id": "irena_renewable_energy_statistics_2020",
        "title": "IRENA Renewable Energy Statistics 2020",
        "date": "2020-07-01",
        "issuer": "IRENA",
        "path": "data/sample_pdfs/IRENA_Renewable_Energy_Statistics_2020.pdf",
        "expected_hint": "ICLN/NEE",
    },
    {
        "report_id": "irena_renewable_power_costs_2022",
        "title": "IRENA Renewable Power Costs 2022",
        "date": "2023-08-29",
        "issuer": "IRENA",
        "path": "data/sample_pdfs/IRENA_Renewable_power_costs_2022.pdf",
        "expected_hint": "ICLN/NEE",
    },
    {
        "report_id": "irena_world_energy_transitions_2023",
        "title": "IRENA World Energy Transitions Outlook 2023",
        "date": "2023-06-22",
        "issuer": "IRENA",
        "path": "data/sample_pdfs/IRENA_World_energy_transitions_2023.pdf",
        "expected_hint": "ICLN/NEE",
    },
    {
        "report_id": "irena_renewable_energy_statistics_2024",
        "title": "IRENA Renewable Energy Statistics 2024",
        "date": "2024-07-11",
        "issuer": "IRENA",
        "path": "data/sample_pdfs/IRENA_Renewable_Energy_Statistics_2024.pdf",
        "expected_hint": "ICLN/NEE",
    },
    {
        "report_id": "nextera_annual_2023",
        "title": "NextEra Energy Annual Report 2023",
        "date": "2024-02-16",
        "issuer": "NextEra Energy",
        "path": "data/sample_pdfs/NextEra_Energy_Annual_Report_2023.pdf",
        "expected_hint": "ETN",
    },
    {
        "report_id": "siemens_energy_annual_2023",
        "title": "Siemens Energy Annual Report 2023",
        "date": "2023-12-06",
        "issuer": "Siemens Energy",
        "path": "data/sample_pdfs/Siemens_Energy_Annual_Report_2023.pdf",
        "expected_hint": "ETN",
    },
    {
        "report_id": "ipcc_ar6_synthesis",
        "title": "IPCC AR6 Synthesis Report",
        "date": "2023-03-20",
        "issuer": "IPCC",
        "path": "data/sample_pdfs/IPCC_AR6_SYR_FullVolume.pdf",
        "expected_hint": "Climate risk",
    },
]


def ensure_dirs():
    ensure_project_dirs()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    return text.strip()


def extract_pdf_text_from_path(path, max_pages=120):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing report PDF: {path}")

    doc = fitz.open(path)
    pages = []
    for page_idx in range(min(len(doc), max_pages)):
        text = doc[page_idx].get_text("text")
        text = clean_text(text)
        if text:
            pages.append({"page": page_idx + 1, "text": text})
    return pages


def extract_pdf_text(report, max_pages=120):
    return extract_pdf_text_from_path(REPORT_DIR / report.path, max_pages=max_pages)


def split_paragraphs(report, pages):
    records = []
    for page in pages:
        chunks = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", page["text"])
        buffer = []
        for chunk in chunks:
            chunk = clean_text(chunk)
            if not chunk:
                continue
            buffer.append(chunk)
            if len(" ".join(buffer)) >= 350:
                paragraph = " ".join(buffer)
                if 120 <= len(paragraph) <= 1600:
                    records.append(
                        {
                            "report_id": report.report_id,
                            "title": report.title,
                            "date": report.date,
                            "issuer": report.issuer,
                            "page": page["page"],
                            "paragraph": paragraph,
                        }
                    )
                buffer = []
        if buffer:
            paragraph = " ".join(buffer)
            if 120 <= len(paragraph) <= 1600:
                records.append(
                    {
                        "report_id": report.report_id,
                        "title": report.title,
                        "date": report.date,
                        "issuer": report.issuer,
                        "page": page["page"],
                        "paragraph": paragraph,
                    }
                )
    return records


def retrieve_evidence(paragraphs, top_k=10):
    evidence_rows = []
    for report_id, group in paragraphs.groupby("report_id"):
        texts = group["paragraph"].tolist()
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        matrix = vectorizer.fit_transform(texts)

        for theme, query in THEME_QUERIES.items():
            query_vector = vectorizer.transform([query])
            scores = cosine_similarity(query_vector, matrix).ravel()
            top_indices = scores.argsort()[::-1][:top_k]

            for rank, idx in enumerate(top_indices, start=1):
                row = group.iloc[idx].to_dict()
                row.update(
                    {
                        "theme": theme,
                        "rank": rank,
                        "retrieval_score": float(scores[idx]),
                    }
                )
                evidence_rows.append(row)

    evidence = pd.DataFrame(evidence_rows)
    evidence = evidence.drop_duplicates(subset=["report_id", "paragraph", "theme"])
    return evidence


class EmbeddingModel:
    def __init__(self, model_name=EMBEDDING_MODEL):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()

    def encode(self, texts, batch_size=16):
        vectors = []
        with torch.no_grad():
            for start in range(0, len(texts), batch_size):
                batch = texts[start : start + batch_size]
                encoded = self.tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=256,
                    return_tensors="pt",
                )
                output = self.model(**encoded)
                token_embeddings = output.last_hidden_state
                attention = encoded["attention_mask"].unsqueeze(-1)
                pooled = (token_embeddings * attention).sum(dim=1) / attention.sum(dim=1).clamp(min=1)
                pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
                vectors.append(pooled.cpu().numpy())
        return np.vstack(vectors)


def train_few_shot_topic_classifiers(embedder):
    training_texts = []
    classifiers = {}
    labels = list(SCORING_REFERENCE_EXAMPLES)

    for examples in SCORING_REFERENCE_EXAMPLES.values():
        training_texts.extend(examples)
    training_texts.extend(FEW_SHOT_NEGATIVE_EXAMPLES)

    training_vectors = embedder.encode(training_texts)
    offset_by_label = {}
    offset = 0
    for label, examples in SCORING_REFERENCE_EXAMPLES.items():
        offset_by_label[label] = range(offset, offset + len(examples))
        offset += len(examples)

    for label in labels:
        y = np.zeros(len(training_texts), dtype=int)
        y[list(offset_by_label[label])] = 1
        model = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
        model.fit(training_vectors, y)
        classifiers[label] = model

    return classifiers


def score_evidence_with_few_shot_learning(evidence, embedder):
    classifiers = train_few_shot_topic_classifiers(embedder)
    evidence_vectors = embedder.encode(evidence["paragraph"].tolist())

    score_rows = []
    for report_id, indices in evidence.groupby("report_id").groups.items():
        report_vectors = evidence_vectors[list(indices)]
        row = {
            "report_id": report_id,
            "title": evidence.loc[list(indices), "title"].iloc[0],
            "date": evidence.loc[list(indices), "date"].iloc[0],
            "issuer": evidence.loc[list(indices), "issuer"].iloc[0],
            "scoring_method": "few_shot_logistic_head_on_minilm_embeddings",
        }
        for label, classifier in classifiers.items():
            probabilities = classifier.predict_proba(report_vectors)[:, 1]
            row[label] = float(np.clip(probabilities.mean(), 0, 1))
        row["transition_signal"] = (
            row["renewable_opportunity"]
            + row["grid_infrastructure"]
            + row["climate_risk"]
            - row["fossil_pressure"]
        )
        row["asset_hint"] = infer_market_theme_hint(row)
        score_rows.append(row)

    return pd.DataFrame(score_rows).sort_values("date")


def score_evidence_semantically(evidence, embedder):
    example_texts = []
    example_labels = []
    for label, examples in SCORING_REFERENCE_EXAMPLES.items():
        for example in examples:
            example_texts.append(example)
            example_labels.append(label)

    example_vectors = embedder.encode(example_texts)
    evidence_vectors = embedder.encode(evidence["paragraph"].tolist())
    sims = cosine_similarity(evidence_vectors, example_vectors)

    score_rows = []
    for report_id, indices in evidence.groupby("report_id").groups.items():
        report_sims = sims[list(indices)]
        row = {
            "report_id": report_id,
            "title": evidence.loc[list(indices), "title"].iloc[0],
            "date": evidence.loc[list(indices), "date"].iloc[0],
            "issuer": evidence.loc[list(indices), "issuer"].iloc[0],
        }
        for label in SCORING_REFERENCE_EXAMPLES:
            label_indices = [i for i, lbl in enumerate(example_labels) if lbl == label]
            label_score = report_sims[:, label_indices].max(axis=1).mean()
            row[label] = float(np.clip((label_score + 1) / 2, 0, 1))
        row["transition_signal"] = (
            row["renewable_opportunity"]
            + row["grid_infrastructure"]
            + row["climate_risk"]
            - row["fossil_pressure"]
        )
        row["asset_hint"] = infer_market_theme_hint(row)
        score_rows.append(row)

    return pd.DataFrame(score_rows).sort_values("date")


def infer_market_theme_hint(row):
    renewable = row["renewable_opportunity"]
    grid = row["grid_infrastructure"]
    fossil = row["fossil_pressure"]
    climate = row["climate_risk"]

    if climate >= fossil - 0.02 and climate >= max(renewable, grid):
        return "Climate risk"
    if grid >= 0.47 and grid > renewable + 0.025 and grid >= fossil:
        return "ETN"
    if fossil > renewable + 0.03 and fossil >= grid:
        return "XLE/XOM transition pressure"
    if renewable >= grid - 0.06 and renewable >= fossil:
        return "ICLN/NEE"
    if grid > renewable + 0.06 and grid >= fossil:
        return "ETN"

    scores = {
        "ICLN/NEE": renewable,
        "ETN": grid,
        "XLE/XOM transition pressure": fossil,
        "Climate risk": climate,
    }
    return max(scores, key=scores.get)


def make_extractive_summaries(evidence, scores, sentences_per_report=5):
    rows = []
    for report_id, group in evidence.sort_values("retrieval_score", ascending=False).groupby("report_id"):
        selected = group.drop_duplicates(subset=["paragraph"]).head(sentences_per_report)
        score_row = scores[scores["report_id"] == report_id].iloc[0]
        bullets = []
        for _, row in selected.iterrows():
            paragraph = row["paragraph"]
            sentence = re.split(r"(?<=[.!?])\s+", paragraph)[0]
            bullets.append(sentence[:280].strip())
        rows.append(
            {
                "report_id": report_id,
                "title": score_row["title"],
                "date": score_row["date"],
                "simple_summary": " | ".join(bullets),
                "plain_korean_explanation": plain_korean_explanation(score_row),
            }
        )
    return pd.DataFrame(rows)


def plain_korean_explanation(row):
    return (
        "이 보고서는 에너지 전환을 시장 신호로 바꾸기 위해 읽은 자료입니다. "
        f"재생에너지 점수는 {row['renewable_opportunity']:.2f}, "
        f"전력망/전기화 점수는 {row['grid_infrastructure']:.2f}, "
        f"화석연료 압력 점수는 {row['fossil_pressure']:.2f}입니다. "
        "쉽게 말해, 보고서 내용이 어떤 산업에 더 좋은 뉴스인지 숫자로 바꾼 것입니다."
    )


def link_scores_to_stock_returns(scores, horizon_weeks=4):
    stock = pd.read_csv(STOCK_WEEKLY_PATH, index_col=0, parse_dates=True)
    stock = stock.sort_index()
    rows = []
    for _, score in scores.iterrows():
        report_date = pd.Timestamp(score["date"])
        future = stock[stock.index > report_date].head(horizon_weeks)
        if len(future) < horizon_weeks:
            continue
        returns = (1 + future[["ICLN", "XLE", "NEE", "XOM", "ETN", "ET_SPREAD"]]).prod() - 1
        row = score.to_dict()
        for col, value in returns.items():
            row[f"forward_{horizon_weeks}w_{col}"] = float(value)
        rows.append(row)
    return pd.DataFrame(rows)


def attach_news_context_to_report_scores(scores, window_weeks=4):
    if not NEWS_WEEKLY_PATH.exists():
        result = scores.copy()
        result["news_context_available"] = False
        result["news_window_mean"] = np.nan
        result["news_window_trend"] = np.nan
        return result

    news = pd.read_csv(NEWS_WEEKLY_PATH)
    date_col = "date" if "date" in news.columns else news.columns[0]
    news[date_col] = pd.to_datetime(news[date_col])
    sentiment_candidates = [
        "NSS_ADJ",
        "news_sentiment",
        "sentiment_score",
        "finbert_sentiment",
        "compound",
    ]
    sentiment_col = next((col for col in sentiment_candidates if col in news.columns), None)
    if sentiment_col is None:
        numeric_cols = [col for col in news.select_dtypes(include=[np.number]).columns if col != date_col]
        sentiment_col = numeric_cols[0] if numeric_cols else None

    result_rows = []
    for _, score in scores.iterrows():
        row = score.to_dict()
        row["news_context_available"] = sentiment_col is not None
        if sentiment_col is None:
            row["news_window_mean"] = np.nan
            row["news_window_trend"] = np.nan
            result_rows.append(row)
            continue

        report_date = pd.Timestamp(score["date"])
        start = report_date - pd.Timedelta(weeks=window_weeks)
        window = news[(news[date_col] >= start) & (news[date_col] <= report_date)].sort_values(date_col)
        row["news_window_mean"] = float(window[sentiment_col].mean()) if not window.empty else np.nan
        if len(window) >= 2:
            row["news_window_trend"] = float(window[sentiment_col].iloc[-1] - window[sentiment_col].iloc[0])
        else:
            row["news_window_trend"] = np.nan
        result_rows.append(row)

    return pd.DataFrame(result_rows)


def validate_sample_pdfs(embedder=None, max_pages=40, top_k=8):
    embedder = embedder or EmbeddingModel()
    rows = []
    for sample in VALIDATION_SAMPLE_PDFS:
        path = Path(sample["path"])
        if not path.exists():
            rows.append(
                {
                    "report_id": sample["report_id"],
                    "title": sample["title"],
                    "expected_hint": sample["expected_hint"],
                    "predicted_hint": "missing_pdf",
                    "matched": False,
                    "paragraphs": 0,
                    "evidence": 0,
                }
            )
            continue

        report = ReportMeta(
            sample["report_id"],
            sample["title"],
            sample["date"],
            sample["issuer"],
            str(path),
            "",
        )
        pages = extract_pdf_text_from_path(path, max_pages=max_pages)
        paragraphs = pd.DataFrame(split_paragraphs(report, pages))
        evidence = retrieve_evidence(paragraphs, top_k=top_k)
        scores = score_evidence_with_few_shot_learning(evidence, embedder)
        predicted = scores.iloc[0]["asset_hint"] if not scores.empty else "no_signal"
        rows.append(
            {
                "report_id": sample["report_id"],
                "title": sample["title"],
                "expected_hint": sample["expected_hint"],
                "predicted_hint": predicted,
                "matched": predicted == sample["expected_hint"],
                "paragraphs": int(len(paragraphs)),
                "evidence": int(len(evidence)),
            }
        )

    result = pd.DataFrame(rows)
    output = REPORT_PROCESSED_DIR / "expanded_pdf_validation.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    return result


def write_summary_markdown(scores, summaries, linked):
    output = TABLES_DIR / "report_signal_summary.md"
    lines = [
        "# Report-to-Market Signal Summary",
        "",
        "## 쉬운 설명",
        "",
        "PDF 보고서를 그냥 요약하는 데서 끝내지 않고, 보고서 안에서 에너지 전환과 관련된 근거 문단을 찾고,",
        "범용 Transformer 임베딩 모델로 사람이 정의한 예시 문장과 PDF 문단의 의미 유사도를 비교해 산업별 점수로 바꿨습니다.",
        "쉽게 말해, 긴 보고서를 읽어서 `재생에너지`, `화석연료 압력`, `전력망`, `기후 리스크` 점수표로 만든 것입니다.",
        "",
        "## Pre-trained Transformer Embedding 연결",
        "",
        f"- 범용 임베딩 모델: `{EMBEDDING_MODEL}`",
        "- 역할: PDF 문단과 예시 문장의 의미를 벡터로 변환",
        "- Few-shot classifier: MiniLM 임베딩은 고정하고, 사람이 만든 소수 라벨 예시로 Logistic Regression 분류 헤드를 학습",
        "- Downstream task: 보고서 점수를 ETF/기업 주가 수익률과 연결",
        "",
        "## Report Signals",
        "",
        scores.round(4).to_markdown(index=False),
        "",
        "## Extractive Summaries",
        "",
    ]
    for _, row in summaries.iterrows():
        lines.extend(
            [
                f"### {row['title']}",
                "",
                f"- Date: `{row['date']}`",
                f"- Simple explanation: {row['plain_korean_explanation']}",
                f"- Evidence summary: {row['simple_summary']}",
                "",
            ]
        )
    if not linked.empty:
        display_cols = [
            "report_id",
            "transition_signal",
            "forward_4w_ET_SPREAD",
            "forward_4w_ICLN",
            "forward_4w_XLE",
            "forward_4w_ETN",
        ]
        lines.extend(["## Downstream Link to Stock Returns", "", linked[display_cols].round(4).to_markdown(index=False)])
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def plot_report_signals(scores):
    fig, ax = plt.subplots(figsize=(13, 7.2))
    plot_df = scores.set_index("report_id")[
        ["renewable_opportunity", "fossil_pressure", "grid_infrastructure", "climate_risk"]
    ]
    plot_df = plot_df.rename(
        index={
            "exxon_acs_2023": "Exxon ACS",
            "iea_weo_2023": "IEA WEO",
            "iea_oil_gas_nz_2023": "IEA Oil/Gas NZ",
            "iea_renewables_2023": "IEA Renewables",
            "eaton_annual_2023": "Eaton Annual",
        },
        columns={
            "renewable_opportunity": "Renewable",
            "fossil_pressure": "Fossil pressure",
            "grid_infrastructure": "Grid",
            "climate_risk": "Climate risk",
        },
    )
    plot_df.plot(kind="bar", ax=ax, width=0.72)
    ax.set_title("PDF Report Topic Scores", pad=18, fontsize=15)
    ax.set_ylabel("Semantic similarity score", labelpad=8)
    ax.set_ylim(0, 1)
    ax.set_xlabel("")
    ax.tick_params(axis="x", rotation=18, labelsize=9)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=4,
        frameon=False,
        fontsize=9,
    )
    ax.margins(x=0.04)
    fig.text(
        0.5,
        0.93,
        "Higher score means the report contains stronger evidence for that topic.",
        ha="center",
        va="center",
        fontsize=10,
        color="#444444",
    )
    fig.subplots_adjust(top=0.84, bottom=0.26, left=0.08, right=0.98)
    output = FIGURES_DIR / "fig5_report_signals.png"
    fig.savefig(output, bbox_inches="tight", dpi=180)
    plt.close(fig)
    return output


def run_report_pipeline():
    ensure_dirs()

    all_paragraphs = []
    for report in REPORTS:
        pages = extract_pdf_text(report)
        paragraphs = split_paragraphs(report, pages)
        if not paragraphs:
            raise RuntimeError(f"No paragraphs extracted from {report.path}")
        all_paragraphs.extend(paragraphs)
        print(f"{report.report_id}: pages={len(pages)}, paragraphs={len(paragraphs)}")

    paragraphs_df = pd.DataFrame(all_paragraphs)
    paragraphs_path = REPORT_PROCESSED_DIR / "report_paragraphs.csv"
    paragraphs_df.to_csv(paragraphs_path, index=False)

    evidence = retrieve_evidence(paragraphs_df)
    evidence_path = REPORT_PROCESSED_DIR / "report_evidence.csv"
    evidence.to_csv(evidence_path, index=False)

    embedder = EmbeddingModel()
    scores = score_evidence_with_few_shot_learning(evidence, embedder)
    scores_path = REPORT_PROCESSED_DIR / "report_signals.csv"
    scores.to_csv(scores_path, index=False)

    news_bridge = attach_news_context_to_report_scores(scores)
    news_bridge_path = REPORT_PROCESSED_DIR / "report_news_bridge.csv"
    news_bridge.to_csv(news_bridge_path, index=False)

    summaries = make_extractive_summaries(evidence, scores)
    summaries_path = REPORT_PROCESSED_DIR / "report_summaries.csv"
    summaries.to_csv(summaries_path, index=False)

    linked = link_scores_to_stock_returns(scores)
    linked_path = REPORT_PROCESSED_DIR / "report_stock_link.csv"
    linked.to_csv(linked_path, index=False)

    fig_path = plot_report_signals(scores)
    md_path = write_summary_markdown(scores, summaries, linked)

    print(f"Saved paragraphs: {paragraphs_path}")
    print(f"Saved evidence: {evidence_path}")
    print(f"Saved report signals: {scores_path}")
    print(f"Saved report-news bridge: {news_bridge_path}")
    print(f"Saved report summaries: {summaries_path}")
    print(f"Saved downstream stock link: {linked_path}")
    print(f"Saved figure: {fig_path}")
    print(f"Saved markdown summary: {md_path}")

    return scores


if __name__ == "__main__":
    run_report_pipeline()
