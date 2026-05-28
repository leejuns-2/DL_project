import argparse
import json
import time
import pandas as pd
import requests

from config import NEWS_RAW_PATH, RAW_DIR, ensure_project_dirs

KEYWORDS = [
    '"renewable energy"',
    '"solar energy"',
    '"wind power"',
    '"climate change"',
    '"carbon tax"',
    '"energy crisis"',
    '"fossil fuel"',
    '"oil price"',
    '"natural gas"',
    '"power grid"',
    '"electricity demand"',
]


def date_ranges(start="2019-01-01", end="2024-12-31", freq="W-FRI"):
    start_ts = pd.Timestamp(start)
    final_end = pd.Timestamp(end)
    starts = pd.date_range(start=start_ts, end=final_end, freq=freq)

    previous = start_ts
    for range_end in starts:
        if range_end < start_ts:
            continue
        yield previous, min(range_end, final_end)
        previous = range_end + pd.Timedelta(days=1)

    if previous <= final_end:
        yield previous, final_end


def build_query():
    keyword_query = " OR ".join(KEYWORDS)
    return f"({keyword_query}) sourcelang:english"


def fetch_gdelt_range(range_start, range_end, max_records=30, retries=2):
    start_dt = range_start.strftime("%Y%m%d000000")
    end_dt = range_end.strftime("%Y%m%d235959")
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": build_query(),
        "mode": "artlist",
        "format": "json",
        "sort": "datedesc",
        "maxrecords": max_records,
        "STARTDATETIME": start_dt,
        "ENDDATETIME": end_dt,
    }

    headers = {"User-Agent": "energy-climate-sentiment-research/0.1"}

    for attempt in range(1, retries + 1):
        response = requests.get(url, params=params, timeout=15, headers=headers)
        if response.status_code == 429 and attempt < retries:
            wait_seconds = 20 * attempt
            print(f"[warning] rate limited; waiting {wait_seconds}s")
            time.sleep(wait_seconds)
            continue
        response.raise_for_status()
        break

    payload = json.loads(response.text, strict=False)
    articles = payload.get("articles", [])

    rows = []
    for article in articles:
        title = article.get("title")
        seen_date = article.get("seendate")
        if not title or not seen_date:
            continue

        rows.append(
            {
                "date": pd.to_datetime(seen_date, errors="coerce"),
                "title": title,
                "url": article.get("url"),
                "domain": article.get("domain"),
                "source_country": article.get("sourcecountry"),
                "language": article.get("language"),
            }
        )

    return pd.DataFrame(rows)


def load_cached_weekly(cache_dir):
    frames = []
    for path in sorted(cache_dir.glob("gdelt_*.csv")):
        df = pd.read_csv(path, parse_dates=["date"])
        if not df.empty:
            frames.append(df)
    return frames


def save_combined_news(frames, end=None):
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=["date", "title"])
    combined["date"] = pd.to_datetime(combined["date"], utc=True, errors="coerce")
    combined = combined.dropna(subset=["date"])
    if end is not None:
        end_ts = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
        combined = combined[combined["date"] < end_ts]
    combined = combined.drop_duplicates(subset=["date", "title", "url"])
    combined = combined.sort_values("date")
    combined.to_csv(NEWS_RAW_PATH, index=False)

    print(f"Saved raw news data: {NEWS_RAW_PATH}")
    print(f"Rows: {len(combined)}")
    print(f"Date range: {combined['date'].min()} to {combined['date'].max()}")
    return combined


def collect_gdelt_news(
    start="2019-01-01",
    end="2024-12-31",
    sleep_seconds=5,
    freq="W-FRI",
    max_records=30,
    rebuild_only=False,
):
    ensure_project_dirs()

    frames = []
    cache_dir = RAW_DIR / "news" / "weekly"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if rebuild_only:
        cached_frames = load_cached_weekly(cache_dir)
        if not cached_frames:
            raise RuntimeError("No cached GDELT news data was found.")
        return save_combined_news(cached_frames, end=end)

    for range_start, range_end in date_ranges(start, end, freq=freq):
        label = f"{range_start:%Y%m%d}_{range_end:%Y%m%d}"
        cache_path = cache_dir / f"gdelt_{label}.csv"

        if cache_path.exists():
            df = pd.read_csv(cache_path, parse_dates=["date"])
            if not df.empty:
                print(f"[info] {label}: loaded cached {len(df)} articles")
                frames.append(df)
            continue

        try:
            df = fetch_gdelt_range(range_start, range_end, max_records=max_records)
        except Exception as exc:
            print(f"[warning] GDELT fetch failed for {label}: {exc}")
            time.sleep(sleep_seconds)
            continue

        if df.empty:
            print(f"[info] {label}: 0 articles")
            time.sleep(sleep_seconds)
            continue

        df["query_start"] = range_start
        df["query_end"] = range_end
        df.to_csv(cache_path, index=False)
        print(f"[info] {label}: {len(df)} articles")
        frames.append(df)
        time.sleep(sleep_seconds)

    if not frames:
        cached_frames = load_cached_weekly(cache_dir)
        if cached_frames:
            print("[info] no new data collected; rebuilding combined file from cache")
            return save_combined_news(cached_frames, end=end)
        raise RuntimeError("No GDELT news data was collected.")

    cached_frames = load_cached_weekly(cache_dir)
    return save_combined_news(cached_frames, end=end)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2019-01-01")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--sleep", type=float, default=5)
    parser.add_argument("--freq", default="W-FRI")
    parser.add_argument("--max-records", type=int, default=30)
    parser.add_argument("--rebuild-only", action="store_true")
    args = parser.parse_args()

    collect_gdelt_news(
        start=args.start,
        end=args.end,
        sleep_seconds=args.sleep,
        freq=args.freq,
        max_records=args.max_records,
        rebuild_only=args.rebuild_only,
    )
