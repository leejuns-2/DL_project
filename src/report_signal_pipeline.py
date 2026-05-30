import re
import zlib
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
MARKET_RETURN_COLUMNS = ["ICLN", "XLE", "NEE", "XOM", "ETN"]
EVENT_WINDOWS = {
    "pre_4w": (-4, 0),
    "post_1w": (0, 1),
    "post_4w": (0, 4),
    "post_8w": (0, 8),
}

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

THEME_KEYS = list(THEME_QUERIES)
ENERGY_RELEVANCE_KEYWORDS = {
    "energy",
    "electricity",
    "power",
    "grid",
    "transmission",
    "renewable",
    "solar",
    "wind",
    "oil",
    "gas",
    "fossil",
    "carbon",
    "emissions",
    "climate",
    "methane",
    "electrification",
    "utility",
    "fuel",
}


SCORING_REFERENCE_EXAMPLES = {
    "renewable_opportunity": [
        "Solar and wind capacity additions are expected to accelerate due to policy support and falling costs.",
        "Clean energy investment creates growth opportunities for renewable power developers and utilities.",
        "Renewable electricity deployment expands as countries increase energy transition targets.",
        "Photovoltaic and offshore wind projects are receiving record investment as levelized costs fall below fossil alternatives.",
        "Governments are setting ambitious renewable portfolio standards to accelerate the energy transition.",
        "Battery storage paired with solar generation is increasingly cost-competitive with peaker plants.",
        "Utility-scale renewable auctions are oversubscribed as institutional investors allocate to clean energy.",
        "Green hydrogen production from electrolysis is scaling up as renewable electricity costs decline.",
    ],
    "fossil_pressure": [
        "Oil and gas producers face transition pressure from emissions regulation and declining fossil fuel demand.",
        "Methane reduction, carbon pricing, and climate policy increase risks for fossil fuel assets.",
        "Fossil fuel companies must reduce emissions to remain aligned with net zero pathways.",
        "Stranded asset risk is rising as financial institutions restrict lending to new coal and oil projects.",
        "Carbon border adjustment mechanisms are increasing competitive pressure on fossil fuel-intensive industries.",
        "Institutional divestment campaigns are reducing capital access for oil and gas companies.",
        "Declining renewable costs are undermining the long-term economic viability of fossil fuel power plants.",
        "Natural gas demand faces structural decline as heat pumps and electric vehicles displace combustion equipment.",
    ],
    "grid_infrastructure": [
        "Transmission bottlenecks and grid expansion needs are delaying renewable energy deployment.",
        "Electrification and data center demand increase investment needs for power management infrastructure.",
        "Power grids require modernization to support electric vehicles, heat pumps, and renewable generation.",
        "Electricity demand growth requires investment in generation, transmission, distribution, and power system flexibility.",
        "Power system reliability depends on grid upgrades, storage, demand response, and network infrastructure.",
        "Rising electricity consumption from cooling, industry, and data centers creates opportunities for electrical equipment suppliers.",
        "Smart grid technologies, advanced metering, and digital substations are required for modern power systems.",
        "Interconnection queues for new renewable projects highlight transmission and substation infrastructure bottlenecks.",
        "Microgrids, distributed energy resources, and virtual power plants are reshaping power distribution architecture.",
    ],
    "climate_risk": [
        "Extreme weather, heat waves, droughts, and physical climate risks affect energy systems.",
        "Climate change increases operational risks for infrastructure, utilities, and energy supply.",
        "Adaptation and resilience are required as climate hazards become more frequent.",
        "Physical climate risks including flooding, wildfires, and sea level rise are affecting infrastructure assets.",
        "Climate scenario analysis is becoming mandatory for financial institutions to assess portfolio risk.",
        "Transition risk from carbon pricing and stranded assets is material for energy-intensive sectors.",
        "Heat stress, water scarcity, and supply chain disruption are emerging as material climate-related financial risks.",
        "TCFD disclosures reveal that companies in high-emission sectors face growing liability and regulatory risk.",
    ],
}


FEW_SHOT_NEGATIVE_EXAMPLES = [
    "The report focuses on general macroeconomic conditions without discussing energy systems.",
    "The company describes accounting policies and administrative matters with no climate signal.",
    "The document lists governance procedures that are unrelated to energy transition investment.",
    "The section contains historical financial statements without operational or policy evidence.",
    "This chapter describes human resources policies, employee benefits, and workforce diversity programs.",
    "The document outlines legal proceedings, patent disputes, and intellectual property litigation.",
    "The section covers marketing strategies, brand positioning, and customer acquisition costs.",
    "Revenue recognition policies and depreciation schedules are discussed in the notes to financial statements.",
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
    {
        "report_id": "iea_electricity_grids_2023",
        "title": "IEA Electricity Grids and Secure Energy Transitions",
        "date": "2023-10-17",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_Electricity_Grids_Secure_Energy_Transitions_2023.pdf",
        "expected_hint": "ETN",
    },
    {
        "report_id": "iea_weo_2022",
        "title": "IEA World Energy Outlook 2022",
        "date": "2022-10-27",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_World_Energy_Outlook_2022.pdf",
        "expected_hint": "ICLN/NEE",
    },
    {
        "report_id": "iea_electricity_2024",
        "title": "IEA Electricity 2024",
        "date": "2024-01-24",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_Electricity_2024.pdf",
        "expected_hint": "ETN",
    },
    {
        "report_id": "iea_power_sector_2021",
        "title": "IEA Secure Energy Transitions in the Power Sector",
        "date": "2021-10-27",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_Secure_Energy_Transitions_Power_Sector_2021.pdf",
        "expected_hint": "ETN",
    },
    {
        "report_id": "iea_oil_2024",
        "title": "IEA Oil 2024",
        "date": "2024-06-12",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_Oil_2024.pdf",
        "expected_hint": "XLE/XOM transition pressure",
    },
    {
        "report_id": "iea_gas_2023",
        "title": "IEA Medium-Term Gas Report 2023",
        "date": "2023-10-10",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_Medium_Term_Gas_Report_2023.pdf",
        "expected_hint": "XLE/XOM transition pressure",
    },
    {
        "report_id": "iea_coal_2023",
        "title": "IEA Coal 2023",
        "date": "2023-12-15",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_Coal_2023.pdf",
        "expected_hint": "XLE/XOM transition pressure",
    },
    {
        "report_id": "iea_global_ev_2023",
        "title": "IEA Global EV Outlook 2023",
        "date": "2023-04-26",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_Global_EV_Outlook_2023.pdf",
        "expected_hint": "ICLN/NEE",
    },
    {
        "report_id": "iea_solar_pv_supply_2022",
        "title": "IEA Solar PV Global Supply Chains 2022",
        "date": "2022-08-01",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_Solar_PV_Global_Supply_Chains_2022.pdf",
        "expected_hint": "ICLN/NEE",
    },
    {
        "report_id": "iea_clean_tech_supply_2022",
        "title": "IEA Securing Clean Energy Technology Supply Chains",
        "date": "2022-07-12",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_Securing_Clean_Energy_Tech_Supply_Chains_2022.pdf",
        "expected_hint": "ICLN/NEE",
    },
    {
        "report_id": "iea_etp_2023",
        "title": "IEA Energy Technology Perspectives 2023",
        "date": "2023-01-12",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_Energy_Technology_Perspectives_2023.pdf",
        "expected_hint": "ICLN/NEE",
    },
    {
        "report_id": "iea_weo_2023_validation",
        "title": "IEA World Energy Outlook 2023",
        "date": "2023-10-24",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_World_Energy_Outlook_2023.pdf",
        "expected_hint": "ICLN/NEE",
    },
    {
        "report_id": "iea_batteries_2024",
        "title": "IEA Batteries and Secure Energy Transitions 2024",
        "date": "2024-04-25",
        "issuer": "IEA",
        "path": "data/sample_pdfs/IEA_Batteries_Secure_Energy_Transitions_2024.pdf",
        "expected_hint": "ETN",
    },
    {
        "report_id": "eia_electric_power_annual_2023",
        "title": "EIA Electric Power Annual 2023",
        "date": "2024-11-07",
        "issuer": "EIA",
        "path": "data/sample_pdfs/EIA_Electric_Power_Annual_2023.pdf",
        "expected_hint": "ETN",
    },
    {
        "report_id": "exxon_acs_2024",
        "title": "ExxonMobil Advancing Climate Solutions 2024",
        "date": "2024-04-08",
        "issuer": "ExxonMobil",
        "path": "data/sample_pdfs/ExxonMobil_Advancing_Climate_Solutions_2024.pdf",
        "expected_hint": "Climate risk",
    },
    {
        "report_id": "exxon_acs_2025",
        "title": "ExxonMobil Advancing Climate Solutions 2025",
        "date": "2025-03-31",
        "issuer": "ExxonMobil",
        "path": "data/sample_pdfs/ExxonMobil_Advancing_Climate_Solutions_2025.pdf",
        "expected_hint": "Climate risk",
    },
    {
        "report_id": "ipcc_ar6_wg3_mitigation",
        "title": "IPCC AR6 WGIII Mitigation Full Report",
        "date": "2022-04-04",
        "issuer": "IPCC",
        "path": "data/sample_pdfs/IPCC_AR6_WGIII_Mitigation_FullReport.pdf",
        "expected_hint": "Climate risk",
    },
]


def validation_split_for_report(report_id, test_ratio=0.28):
    """Stable split so validation/test membership does not change across runs."""
    bucket = zlib.crc32(str(report_id).encode("utf-8")) % 100
    return "test" if bucket < int(test_ratio * 100) else "validation"


def summarize_validation_results(result, matched_col="matched"):
    rows = []
    if result.empty or matched_col not in result.columns:
        return pd.DataFrame(rows)

    groups = [("all", result)]
    if "split" in result.columns:
        groups.extend((split, group) for split, group in result.groupby("split"))

    for split, group in groups:
        available = group[group.get("predicted_hint", "") != "missing_pdf"] if "predicted_hint" in group else group
        if available.empty:
            rows.append({"split": split, "n": 0, "accuracy": np.nan, "coverage": 0.0})
            continue
        rows.append(
            {
                "split": split,
                "n": int(len(available)),
                "accuracy": float(available[matched_col].astype(bool).mean()),
                "coverage": float(len(available) / len(group)) if len(group) else 0.0,
                "low_relevance_rate": (
                    float((available["ood_decision"] != "in_domain").mean())
                    if "ood_decision" in available.columns
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


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


def _minmax(values):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return values
    v_min, v_max = values.min(), values.max()
    if v_max - v_min <= 1e-9:
        return np.zeros_like(values)
    return (values - v_min) / (v_max - v_min)


def _is_low_information_paragraph(text):
    text = str(text)
    if not text.strip():
        return True

    dot_leaders = len(re.findall(r"\.{5,}", text))
    toc_entries = len(re.findall(r"\b\d+(?:\.\d+){1,3}\b[^.!?]{0,140}\.{4,}\s*\d{1,3}\b", text))
    words = re.findall(r"[A-Za-z][A-Za-z-]{2,}", text)
    alpha_chars = len(re.findall(r"[A-Za-z]", text))
    digit_chars = len(re.findall(r"\d", text))
    total_chars = max(len(text), 1)

    if toc_entries >= 2:
        return True
    if dot_leaders >= 3 and len(words) < 90:
        return True
    if dot_leaders >= 2 and digit_chars / total_chars > 0.08 and alpha_chars / total_chars < 0.65:
        return True
    return False


def retrieve_evidence(paragraphs, top_k=10, embedder=None, hybrid=False):
    evidence_rows = []
    for report_id, group in paragraphs.groupby("report_id"):
        candidate_group = group[~group["paragraph"].map(_is_low_information_paragraph)]
        if candidate_group.empty:
            candidate_group = group
        group = candidate_group.reset_index(drop=True)
        texts = group["paragraph"].tolist()
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        matrix = vectorizer.fit_transform(texts)
        paragraph_vectors = embedder.encode(texts) if hybrid and embedder is not None and texts else None

        for theme, query in THEME_QUERIES.items():
            query_vector = vectorizer.transform([query])
            tfidf_scores = cosine_similarity(query_vector, matrix).ravel()
            embedding_scores = np.zeros_like(tfidf_scores)
            if paragraph_vectors is not None:
                query_embedding = embedder.encode([query])
                embedding_scores = cosine_similarity(query_embedding, paragraph_vectors).ravel()

            if paragraph_vectors is not None:
                scores = 0.65 * _minmax(tfidf_scores) + 0.35 * _minmax(embedding_scores)
                retrieval_method = "tfidf_embedding_hybrid"
            else:
                scores = tfidf_scores
                retrieval_method = "tfidf"
            top_indices = scores.argsort()[::-1][:top_k]

            for rank, idx in enumerate(top_indices, start=1):
                row = group.iloc[idx].to_dict()
                row.update(
                    {
                        "theme": theme,
                        "rank": rank,
                        "retrieval_score": float(scores[idx]),
                        "tfidf_score": float(tfidf_scores[idx]),
                        "embedding_score": float(embedding_scores[idx]),
                        "retrieval_method": retrieval_method,
                    }
                )
                evidence_rows.append(row)

    evidence = pd.DataFrame(evidence_rows)
    if evidence.empty:
        return evidence
    evidence = evidence.drop_duplicates(subset=["report_id", "paragraph", "theme"])
    return evidence


class EmbeddingModel:
    def __init__(self, model_name=EMBEDDING_MODEL):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()
        self._topic_classifiers = None

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
    if getattr(embedder, "_topic_classifiers", None) is not None:
        return embedder._topic_classifiers

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

    embedder._topic_classifiers = classifiers
    return classifiers


def estimate_energy_relevance(evidence_group, raw_scores=None):
    if evidence_group.empty:
        return {
            "energy_relevance": 0.0,
            "retrieval_relevance": 0.0,
            "keyword_relevance": 0.0,
            "classifier_relevance": 0.0,
            "ood_decision": "out_of_domain",
        }

    relevance_col = "tfidf_score" if "tfidf_score" in evidence_group.columns else "retrieval_score"
    retrieval_values = evidence_group[relevance_col].astype(float).values
    n_top = max(1, min(8, len(retrieval_values)))
    retrieval_relevance = float(np.sort(retrieval_values)[-n_top:].mean())

    paragraphs = evidence_group.drop_duplicates(subset=["paragraph"])["paragraph"].astype(str).str.lower().tolist()
    keyword_hits = []
    for paragraph in paragraphs:
        tokens = set(re.findall(r"[a-zA-Z]+", paragraph))
        keyword_hits.append(len(tokens & ENERGY_RELEVANCE_KEYWORDS) > 0)
    keyword_relevance = float(np.mean(keyword_hits)) if keyword_hits else 0.0
    classifier_relevance = float(max(raw_scores.values())) if raw_scores else 0.0

    # The components intentionally mix retrieval evidence, surface-domain
    # keywords, and classifier confidence so non-energy PDFs do not get forced
    # into a strong transition label by min-max scaling alone.
    retrieval_component = np.clip(retrieval_relevance / 0.18, 0, 1)
    classifier_component = np.clip((classifier_relevance - 0.35) / 0.25, 0, 1)
    energy_relevance = float(np.clip(0.45 * retrieval_component + 0.35 * keyword_relevance + 0.20 * classifier_component, 0, 1))
    if energy_relevance < 0.35:
        ood_decision = "out_of_domain"
    elif energy_relevance < 0.55:
        ood_decision = "low_relevance"
    else:
        ood_decision = "in_domain"

    return {
        "energy_relevance": energy_relevance,
        "retrieval_relevance": retrieval_relevance,
        "keyword_relevance": keyword_relevance,
        "classifier_relevance": classifier_relevance,
        "ood_decision": ood_decision,
    }


def score_evidence_with_few_shot_learning(evidence, embedder):
    evidence = evidence.reset_index(drop=True)
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
        raw_scores = {}
        for label, classifier in classifiers.items():
            probabilities = classifier.predict_proba(report_vectors)[:, 1]
            n_top = max(1, int(len(probabilities) * 0.30))
            raw_value = float(np.clip(np.sort(probabilities)[-n_top:].mean(), 0, 1))
            raw_scores[label] = raw_value
            row[f"{label}_raw"] = raw_value
            row[label] = raw_value

        raw = np.array([row[k] for k in THEME_KEYS])
        v_min, v_max = raw.min(), raw.max()
        if v_max - v_min > 1e-6:
            scaled = (raw - v_min) / (v_max - v_min)
            for k, v in zip(THEME_KEYS, scaled):
                row[k] = float(v)

        relevance = estimate_energy_relevance(evidence.loc[list(indices)], raw_scores=raw_scores)
        row.update(relevance)
        row["transition_signal"] = (
            row["renewable_opportunity"]
            + row["grid_infrastructure"]
            + row["climate_risk"]
            - row["fossil_pressure"]
        )
        row["transition_signal_raw"] = (
            row["renewable_opportunity_raw"]
            + row["grid_infrastructure_raw"]
            + row["climate_risk_raw"]
            - row["fossil_pressure_raw"]
        )
        row["asset_hint"] = infer_market_theme_hint(row)
        score_rows.append(row)

    return pd.DataFrame(score_rows).sort_values("date")


def score_evidence_with_zero_shot_similarity(evidence):
    """Baseline: aggregate frozen embedding retrieval scores without task-head learning."""
    score_rows = []

    for report_id, group in evidence.groupby("report_id"):
        row = {
            "report_id": report_id,
            "title": group["title"].iloc[0],
            "date": group["date"].iloc[0],
            "issuer": group["issuer"].iloc[0],
            "scoring_method": "zero_shot_embedding_similarity",
        }
        for theme in THEME_KEYS:
            values = group.loc[group["theme"] == theme, "retrieval_score"].astype(float).values
            if len(values) == 0:
                row[theme] = 0.0
                continue
            n_top = max(1, int(len(values) * 0.30))
            row[theme] = float(np.sort(values)[-n_top:].mean())

        raw = np.array([row[k] for k in THEME_KEYS])
        v_min, v_max = raw.min(), raw.max()
        if v_max - v_min > 1e-6:
            scaled = (raw - v_min) / (v_max - v_min)
            for k, v in zip(THEME_KEYS, scaled):
                row[k] = float(v)

        row.update(estimate_energy_relevance(group))
        row["transition_signal"] = (
            row["renewable_opportunity"]
            + row["grid_infrastructure"]
            + row["climate_risk"]
            - row["fossil_pressure"]
        )
        row["asset_hint"] = infer_market_theme_hint(row)
        score_rows.append(row)

    return pd.DataFrame(score_rows).sort_values("date")


def theme_margin(row):
    values = sorted([float(row[k]) for k in THEME_KEYS], reverse=True)
    return values[0] - values[1] if len(values) >= 2 else 0.0



def infer_market_theme_hint(row):
    if row.get("ood_decision") in {"out_of_domain", "low_relevance"}:
        return "Out-of-domain / low energy relevance"

    renewable = row["renewable_opportunity"]
    grid = row["grid_infrastructure"]
    fossil = row["fossil_pressure"]
    climate = row["climate_risk"]
    title = str(row.get("title", "")).lower()

    if climate >= fossil - 0.02 and climate >= max(renewable, grid):
        return "Climate risk"
    if any(keyword in title for keyword in ["coal", "oil", "gas", "fossil"]) and fossil >= renewable - 0.04:
        return "XLE/XOM transition pressure"
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
    relevance = row.get("energy_relevance", None)
    relevance_text = f" 에너지 관련성 점수는 {relevance:.2f}입니다." if relevance is not None else ""
    return (
        "이 보고서는 에너지 전환을 시장 신호로 바꾸기 위해 읽은 자료입니다. "
        f"재생에너지 점수는 {row['renewable_opportunity']:.2f}, "
        f"전력망/전기화 점수는 {row['grid_infrastructure']:.2f}, "
        f"화석연료 압력 점수는 {row['fossil_pressure']:.2f}입니다."
        f"{relevance_text} "
        "쉽게 말해, 보고서 내용을 어떤 산업에 좋은 또는 부담이 되는 신호인지 숫자로 바꾼 결과입니다."
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


def compound_returns(window, columns):
    if window.empty:
        return pd.Series({col: np.nan for col in columns})
    return (1 + window[columns]).prod() - 1


def event_window_stock_returns(scores, windows=None):
    windows = windows or EVENT_WINDOWS
    if not STOCK_WEEKLY_PATH.exists():
        return pd.DataFrame()

    stock = pd.read_csv(STOCK_WEEKLY_PATH, index_col=0, parse_dates=True).sort_index()
    required = [*MARKET_RETURN_COLUMNS, "ET_SPREAD"]
    if not set(required).issubset(stock.columns):
        return pd.DataFrame()

    rows = []
    for _, score in scores.iterrows():
        report_date = pd.Timestamp(score["date"])
        row = {
            "report_id": score.get("report_id"),
            "title": score.get("title"),
            "date": score.get("date"),
            "asset_hint": score.get("asset_hint"),
            "transition_signal": score.get("transition_signal"),
        }
        for label, (start_offset, end_offset) in windows.items():
            if start_offset < 0:
                start = report_date + pd.Timedelta(weeks=start_offset)
                end = report_date
                window = stock[(stock.index > start) & (stock.index <= end)]
            else:
                start = report_date
                end = report_date + pd.Timedelta(weeks=end_offset)
                window = stock[(stock.index > start) & (stock.index <= end)]

            row[f"{label}_n_weeks"] = int(len(window))
            asset_returns = compound_returns(window, MARKET_RETURN_COLUMNS)
            benchmark = float(asset_returns.mean()) if asset_returns.notna().any() else np.nan
            row[f"{label}_benchmark_equal_weight"] = benchmark
            for col, value in asset_returns.items():
                row[f"{label}_{col}"] = float(value) if pd.notna(value) else np.nan
                row[f"{label}_abnormal_{col}"] = float(value - benchmark) if pd.notna(value) and pd.notna(benchmark) else np.nan
            if "ET_SPREAD" in window:
                spread_return = compound_returns(window, ["ET_SPREAD"]).iloc[0]
                row[f"{label}_ET_SPREAD"] = float(spread_return) if pd.notna(spread_return) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def attach_news_context_to_report_scores(scores, window_weeks=4):
    if not NEWS_WEEKLY_PATH.exists():
        result = scores.copy()
        result["news_context_available"] = False
        result["news_window_mean"] = np.nan
        result["news_window_trend"] = np.nan
        result["news_window_std"] = np.nan
        result["news_window_article_count"] = np.nan
        result["news_window_mean_z"] = np.nan
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

    global_mean = float(news[sentiment_col].mean()) if sentiment_col else np.nan
    global_std = float(news[sentiment_col].std(ddof=0)) if sentiment_col else np.nan
    article_col = "article_count" if "article_count" in news.columns else None

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
        row["news_window_std"] = float(window[sentiment_col].std(ddof=0)) if len(window) >= 2 else np.nan
        row["news_window_min"] = float(window[sentiment_col].min()) if not window.empty else np.nan
        row["news_window_max"] = float(window[sentiment_col].max()) if not window.empty else np.nan
        row["news_window_n_weeks"] = int(len(window))
        row["news_window_article_count"] = int(window[article_col].sum()) if article_col and not window.empty else np.nan
        row["news_window_mean_z"] = (
            float((row["news_window_mean"] - global_mean) / global_std)
            if pd.notna(row["news_window_mean"]) and pd.notna(global_std) and global_std > 1e-9
            else np.nan
        )
        if len(window) >= 2:
            row["news_window_trend"] = float(window[sentiment_col].iloc[-1] - window[sentiment_col].iloc[0])
        else:
            row["news_window_trend"] = np.nan
        result_rows.append(row)

    return pd.DataFrame(result_rows)


def validate_sample_pdfs(embedder=None, max_pages=40, top_k=10, hybrid_retrieval=True):
    embedder = embedder or EmbeddingModel()
    rows = []
    for sample in VALIDATION_SAMPLE_PDFS:
        split = validation_split_for_report(sample["report_id"])
        path = Path(sample["path"])
        if not path.exists():
            rows.append(
                {
                    "report_id": sample["report_id"],
                    "title": sample["title"],
                    "split": split,
                    "expected_hint": sample["expected_hint"],
                    "predicted_hint": "missing_pdf",
                    "matched": False,
                    "energy_relevance": 0.0,
                    "ood_decision": "missing_pdf",
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
        evidence = retrieve_evidence(paragraphs, top_k=top_k, embedder=embedder, hybrid=hybrid_retrieval)
        scores = score_evidence_with_few_shot_learning(evidence, embedder)
        predicted = scores.iloc[0]["asset_hint"] if not scores.empty else "no_signal"
        score_row = scores.iloc[0] if not scores.empty else {}
        rows.append(
            {
                "report_id": sample["report_id"],
                "title": sample["title"],
                "split": split,
                "expected_hint": sample["expected_hint"],
                "predicted_hint": predicted,
                "matched": predicted == sample["expected_hint"],
                "energy_relevance": float(score_row.get("energy_relevance", 0.0)),
                "ood_decision": score_row.get("ood_decision", "no_signal"),
                "paragraphs": int(len(paragraphs)),
                "evidence": int(len(evidence)),
            }
        )

    result = pd.DataFrame(rows)
    output = REPORT_PROCESSED_DIR / "expanded_pdf_validation.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    split_metrics = summarize_validation_results(result)
    split_metrics.to_csv(REPORT_PROCESSED_DIR / "pdf_validation_split_metrics.csv", index=False)
    return result


def compare_zero_shot_vs_few_shot(embedder=None, max_pages=40, top_k=10, hybrid_retrieval=True):
    embedder = embedder or EmbeddingModel()
    rows = []

    for sample in VALIDATION_SAMPLE_PDFS:
        split = validation_split_for_report(sample["report_id"])
        path = Path(sample["path"])
        base = {
            "report_id": sample["report_id"],
            "title": sample["title"],
            "split": split,
            "expected_hint": sample["expected_hint"],
        }
        if not path.exists():
            rows.append(
                {
                    **base,
                    "zero_shot_hint": "missing_pdf",
                    "few_shot_hint": "missing_pdf",
                    "zero_shot_matched": False,
                    "few_shot_matched": False,
                    "zero_shot_margin": 0.0,
                    "few_shot_margin": 0.0,
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
        evidence = retrieve_evidence(paragraphs, top_k=top_k, embedder=embedder, hybrid=hybrid_retrieval)
        zero_score = score_evidence_with_zero_shot_similarity(evidence).iloc[0].to_dict()
        few_score = score_evidence_with_few_shot_learning(evidence, embedder).iloc[0].to_dict()

        rows.append(
            {
                **base,
                "zero_shot_hint": zero_score["asset_hint"],
                "few_shot_hint": few_score["asset_hint"],
                "zero_shot_matched": zero_score["asset_hint"] == sample["expected_hint"],
                "few_shot_matched": few_score["asset_hint"] == sample["expected_hint"],
                "zero_shot_margin": float(theme_margin(zero_score)),
                "few_shot_margin": float(theme_margin(few_score)),
                "few_shot_energy_relevance": float(few_score.get("energy_relevance", 0.0)),
                "few_shot_ood_decision": few_score.get("ood_decision", "unknown"),
                "comparison_note": (
                    "zero-shot uses frozen embedding retrieval similarity; "
                    "few-shot uses frozen embeddings plus logistic classifier heads from human examples"
                ),
            }
        )

    result = pd.DataFrame(rows)
    output = REPORT_PROCESSED_DIR / "zero_shot_vs_few_shot.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    if not result.empty:
        metric_rows = []
        for split, group in [("all", result), *result.groupby("split")]:
            available = group[group["few_shot_hint"] != "missing_pdf"]
            if available.empty:
                metric_rows.append({"split": split, "n": 0, "zero_shot_accuracy": np.nan, "few_shot_accuracy": np.nan})
                continue
            metric_rows.append(
                {
                    "split": split,
                    "n": int(len(available)),
                    "zero_shot_accuracy": float(available["zero_shot_matched"].astype(bool).mean()),
                    "few_shot_accuracy": float(available["few_shot_matched"].astype(bool).mean()),
                    "few_shot_low_relevance_rate": float((available["few_shot_ood_decision"] != "in_domain").mean()),
                }
            )
        pd.DataFrame(metric_rows).to_csv(REPORT_PROCESSED_DIR / "zero_shot_vs_few_shot_split_metrics.csv", index=False)
    return result


def write_summary_markdown(scores, summaries, linked):
    output = TABLES_DIR / "report_signal_summary.md"
    lines = [
        "# Report-to-Market Signal Summary",
        "",
        "## 쉬운 설명",
        "",
        "PDF 보고서를 단순 요약하지 않고, 에너지 전환과 관련된 근거 문단을 찾습니다.",
        "사전학습 Transformer 임베딩으로 사람이 만든 예시 문장과 PDF 문단의 유사성을 비교하고, 주제별 점수로 변환합니다.",
        "raw classifier probability와 per-report normalized score를 함께 저장해, 모델 신뢰도와 시각화 점수를 분리합니다.",
        "",
        "## Pre-trained Transformer Embedding 연결",
        "",
        f"- 범용 임베딩 모델: `{EMBEDDING_MODEL}`",
        "- 역할: PDF 문단과 예시 문장의 의미를 벡터로 변환",
        "- Few-shot classifier: MiniLM 임베딩은 고정하고, 소수 라벨 예시로 Logistic Regression 분류 헤드를 학습",
        "- OOD guard: 에너지 관련성이 낮은 문서는 강한 자산 신호로 해석하지 않음",
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

    event_returns = event_window_stock_returns(scores)
    event_returns_path = REPORT_PROCESSED_DIR / "report_event_window_returns.csv"
    event_returns.to_csv(event_returns_path, index=False)

    fig_path = plot_report_signals(scores)
    md_path = write_summary_markdown(scores, summaries, linked)

    print(f"Saved paragraphs: {paragraphs_path}")
    print(f"Saved evidence: {evidence_path}")
    print(f"Saved report signals: {scores_path}")
    print(f"Saved report-news bridge: {news_bridge_path}")
    print(f"Saved report summaries: {summaries_path}")
    print(f"Saved downstream stock link: {linked_path}")
    print(f"Saved event window returns: {event_returns_path}")
    print(f"Saved figure: {fig_path}")
    print(f"Saved markdown summary: {md_path}")

    return scores


if __name__ == "__main__":
    run_report_pipeline()
