import numpy as np
import pandas as pd
import torch
from tqdm import tqdm
from transformers import pipeline

from config import NEWS_RAW_PATH, NEWS_WEEKLY_PATH, ensure_project_dirs


class FinBERTExtractor:
    def __init__(self):
        device = 0 if torch.cuda.is_available() else -1
        self.pipe = pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            device=device,
            truncation=True,
            max_length=512,
        )
        print(f"Loaded FinBERT on {'GPU' if device == 0 else 'CPU'}")

    @staticmethod
    def label_to_score(label: str, confidence: float) -> float:
        normalized = label.lower()
        if normalized == "positive":
            return confidence
        if normalized == "negative":
            return -confidence
        return 0.0

    def score_batch(self, texts, batch_size=32):
        scores = []
        clean_texts = [str(text)[:512] for text in texts]

        for i in tqdm(range(0, len(clean_texts), batch_size), desc="FinBERT"):
            batch = clean_texts[i : i + batch_size]
            results = self.pipe(batch)
            for result in results:
                scores.append(
                    self.label_to_score(result["label"], result["score"])
                )

        return scores


def build_weekly_sentiment(
    input_path=NEWS_RAW_PATH,
    output_path=NEWS_WEEKLY_PATH,
    text_col="title",
    date_col="date",
    batch_size=32,
):
    ensure_project_dirs()

    news = pd.read_csv(input_path)
    missing = {text_col, date_col} - set(news.columns)
    if missing:
        raise ValueError(f"Missing required news columns: {sorted(missing)}")

    news = news.dropna(subset=[text_col, date_col]).copy()
    news[date_col] = pd.to_datetime(news[date_col], errors="coerce")
    news = news.dropna(subset=[date_col])

    extractor = FinBERTExtractor()
    news["raw_score"] = extractor.score_batch(news[text_col].tolist(), batch_size)

    weekly = news.set_index(date_col).resample("W-FRI").agg(
        NSS=("raw_score", "mean"),
        NEWS_COUNT=("raw_score", "count"),
    )
    weekly = weekly[weekly["NEWS_COUNT"] > 0]
    weekly["NSS_ADJ"] = weekly["NSS"] * np.log1p(weekly["NEWS_COUNT"])
    weekly.to_csv(output_path)

    print(f"Saved weekly news sentiment: {output_path}")
    print(weekly.tail())
    return weekly


if __name__ == "__main__":
    build_weekly_sentiment()
