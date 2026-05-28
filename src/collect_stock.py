import pandas as pd
import yfinance as yf

from config import (
    RAW_DIR,
    START_DATE,
    END_DATE,
    STOCK_WEEKLY_PATH,
    TICKERS,
    ensure_project_dirs,
)


def collect_stock():
    ensure_project_dirs()

    close_frames = []
    for ticker in TICKERS:
        data = yf.download(
            ticker,
            start=START_DATE,
            end=END_DATE,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        if data.empty:
            print(f"[warning] No stock data downloaded for {ticker}")
            continue

        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"][[ticker]]
        else:
            close = data[["Close"]].rename(columns={"Close": ticker})
        close_frames.append(close)

    if not close_frames:
        raise RuntimeError("No stock data was downloaded from yfinance.")

    close = pd.concat(close_frames, axis=1).sort_index()
    close.to_csv(RAW_DIR / "stock" / "stock_daily_prices.csv")

    weekly_close = close.resample("W-FRI").last()
    weekly_returns = weekly_close.pct_change().dropna(how="all")
    weekly_returns = weekly_returns.loc[weekly_returns.index <= END_DATE]

    missing_required = {"ICLN", "XLE"} - set(weekly_returns.columns)
    if missing_required:
        raise RuntimeError(f"Missing required ETF columns: {missing_required}")

    weekly_returns["ET_SPREAD"] = weekly_returns["ICLN"] - weekly_returns["XLE"]
    weekly_returns.to_csv(STOCK_WEEKLY_PATH)

    print(f"Saved weekly stock returns: {STOCK_WEEKLY_PATH}")
    print(weekly_returns.tail())
    return weekly_returns


if __name__ == "__main__":
    collect_stock()
