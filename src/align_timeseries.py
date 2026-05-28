import pandas as pd

from config import (
    ALIGNED_PANEL_PATH,
    CLIMATE_WEEKLY_PATH,
    COVID_END,
    COVID_START,
    NEWS_WEEKLY_PATH,
    STOCK_WEEKLY_PATH,
    ensure_project_dirs,
)


def read_weekly_csv(path):
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
    df.index.name = "date"
    return df.sort_index()


def build_aligned_panel():
    ensure_project_dirs()

    climate = read_weekly_csv(CLIMATE_WEEKLY_PATH)
    news = read_weekly_csv(NEWS_WEEKLY_PATH)
    stock = read_weekly_csv(STOCK_WEEKLY_PATH)

    required_stock = ["ICLN", "XLE", "NEE", "XOM", "ETN", "ET_SPREAD"]
    required_news = ["NSS", "NEWS_COUNT", "NSS_ADJ"]
    required_climate = ["TAI"]

    missing_stock = set(required_stock) - set(stock.columns)
    missing_news = set(required_news) - set(news.columns)
    missing_climate = set(required_climate) - set(climate.columns)
    if missing_stock or missing_news or missing_climate:
        raise ValueError(
            "Missing columns: "
            f"stock={sorted(missing_stock)}, "
            f"news={sorted(missing_news)}, "
            f"climate={sorted(missing_climate)}"
        )

    panel = pd.concat(
        [
            climate[required_climate],
            news[required_news],
            stock[required_stock],
        ],
        axis=1,
    ).sort_index()

    panel["IS_COVID"] = (
        (panel.index >= pd.Timestamp(COVID_START))
        & (panel.index <= pd.Timestamp(COVID_END))
    )

    panel.to_csv(ALIGNED_PANEL_PATH)
    print(f"Saved aligned weekly panel: {ALIGNED_PANEL_PATH}")
    print(f"Shape: {panel.shape}")
    print(f"Date range: {panel.index.min()} to {panel.index.max()}")
    print("Missing values:")
    print(panel.isna().sum())
    return panel


if __name__ == "__main__":
    build_aligned_panel()
