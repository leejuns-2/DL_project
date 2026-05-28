from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = ROOT_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
TABLES_DIR = OUTPUTS_DIR / "tables"

START_DATE = "2019-01-01"
END_DATE = "2024-12-31"

TICKERS = ["ICLN", "XLE", "NEE", "XOM", "ETN"]
ETF_TICKERS = ["ICLN", "XLE"]
COMPANY_TICKERS = ["NEE", "XOM", "ETN"]

COVID_START = "2020-03-01"
COVID_END = "2021-06-30"

STOCK_WEEKLY_PATH = PROCESSED_DIR / "stock_returns_weekly.csv"
CLIMATE_WEEKLY_PATH = PROCESSED_DIR / "climate_weekly_tai.csv"
NEWS_RAW_PATH = RAW_DIR / "news" / "news_headlines_raw.csv"
NEWS_WEEKLY_PATH = PROCESSED_DIR / "news_sentiment_weekly.csv"
ALIGNED_PANEL_PATH = PROCESSED_DIR / "aligned_weekly_panel.csv"
CROSS_CORR_PATH = TABLES_DIR / "cross_corr_full.csv"


def ensure_project_dirs() -> None:
    for path in [
        RAW_DIR / "climate",
        RAW_DIR / "news",
        RAW_DIR / "stock",
        PROCESSED_DIR,
        FIGURES_DIR,
        TABLES_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
