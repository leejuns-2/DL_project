import pandas as pd
import requests

from config import CLIMATE_WEEKLY_PATH, END_DATE, RAW_DIR, ensure_project_dirs


def collect_climate(lat=45, lon=10, start="20190101", end="20241231"):
    ensure_project_dirs()

    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=T2M&community=RE&longitude={lon}&latitude={lat}"
        f"&start={start}&end={end}&format=JSON"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()["properties"]["parameter"]["T2M"]
    df = pd.DataFrame.from_dict(data, orient="index", columns=["T2M"])
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df = df.sort_index()

    df["T2M_30d_mean"] = df["T2M"].rolling(30, min_periods=15).mean()
    df["TAI"] = df["T2M"] - df["T2M_30d_mean"]

    df.to_csv(RAW_DIR / "climate" / "climate_daily_tai.csv")

    weekly = df[["TAI"]].resample("W-FRI").mean().dropna(subset=["TAI"])
    weekly = weekly.loc[weekly.index <= END_DATE]
    weekly.to_csv(CLIMATE_WEEKLY_PATH)

    print(f"Saved weekly climate data: {CLIMATE_WEEKLY_PATH}")
    print(weekly.tail())
    return weekly


if __name__ == "__main__":
    collect_climate()
