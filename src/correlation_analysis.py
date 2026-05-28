import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from config import ALIGNED_PANEL_PATH, CROSS_CORR_PATH, TABLES_DIR, ensure_project_dirs


SIGNALS = ["TAI", "NSS", "NSS_ADJ"]
TARGETS = ["NSS", "NSS_ADJ", "ET_SPREAD", "ICLN", "XLE", "NEE", "XOM", "ETN"]
LAGS = range(-4, 5)


def read_panel():
    df = pd.read_csv(ALIGNED_PANEL_PATH, index_col=0, parse_dates=True)
    df.index.name = "date"
    return df.sort_index()


def safe_pearson(x, y):
    if x.nunique(dropna=True) < 2 or y.nunique(dropna=True) < 2:
        return np.nan, np.nan
    return pearsonr(x, y)


def cross_corr_matrix(df, signals=SIGNALS, targets=TARGETS, lags=LAGS, min_n=20):
    records = []
    d = df[~df["IS_COVID"]].copy()

    for signal in signals:
        for target in targets:
            if signal == target:
                continue
            for lag in lags:
                x = d[signal]
                y = d[target].shift(-lag)
                valid = x.notna() & y.notna()
                n = int(valid.sum())

                if n < min_n:
                    records.append(
                        {
                            "signal": signal,
                            "target": target,
                            "lag_weeks": lag,
                            "n": n,
                            "r": np.nan,
                            "p_value": np.nan,
                            "significant": False,
                            "note": f"n < {min_n}",
                        }
                    )
                    continue

                r, p_value = safe_pearson(x[valid], y[valid])
                records.append(
                    {
                        "signal": signal,
                        "target": target,
                        "lag_weeks": lag,
                        "n": n,
                        "r": r,
                        "p_value": p_value,
                        "significant": bool(pd.notna(p_value) and p_value < 0.05),
                        "note": "",
                    }
                )

    return pd.DataFrame(records)


def build_rolling_corr(df):
    rolling = (
        df[["NSS_ADJ", "ET_SPREAD"]]
        .dropna()
        .rolling(26, min_periods=12)
        .corr()
        .unstack()["NSS_ADJ"]["ET_SPREAD"]
        .dropna()
    )
    rolling.name = "rolling_corr_26w"
    return rolling


def run_analysis():
    ensure_project_dirs()
    df = read_panel()

    corr = cross_corr_matrix(df)
    corr.to_csv(CROSS_CORR_PATH, index=False)

    rolling = build_rolling_corr(df)
    rolling_path = TABLES_DIR / "rolling_corr_nss_adj_et_spread.csv"
    rolling.to_csv(rolling_path)

    valid_corr = corr.dropna(subset=["r"])
    print(f"Saved cross-correlation table: {CROSS_CORR_PATH}")
    print(f"Rows: {len(corr)}, valid correlations: {len(valid_corr)}")
    print(f"Saved rolling correlation table: {rolling_path}")
    print(f"Rolling rows: {len(rolling)}")

    key_pairs = [
        ("TAI", "NSS"),
        ("TAI", "NSS_ADJ"),
        ("NSS_ADJ", "ET_SPREAD"),
        ("NSS_ADJ", "NEE"),
        ("NSS_ADJ", "XOM"),
        ("NSS_ADJ", "ETN"),
    ]
    for signal, target in key_pairs:
        subset = valid_corr[
            (valid_corr["signal"] == signal) & (valid_corr["target"] == target)
        ].copy()
        if subset.empty:
            print(f"[info] No valid correlations for {signal} -> {target}")
            continue
        best = subset.reindex(subset["r"].abs().sort_values(ascending=False).index).iloc[0]
        print(
            f"{signal} -> {target}: "
            f"best lag={int(best['lag_weeks'])}, "
            f"r={best['r']:.4f}, p={best['p_value']:.4f}, n={int(best['n'])}"
        )

    return corr, rolling


if __name__ == "__main__":
    run_analysis()
