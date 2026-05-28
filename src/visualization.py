import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from config import ALIGNED_PANEL_PATH, CROSS_CORR_PATH, FIGURES_DIR, TABLES_DIR, ensure_project_dirs

EVENTS = {
    "2022-02-24": "Russia-Ukraine war",
    "2022-08-01": "Europe heat wave",
    "2022-10-01": "Energy crisis peak",
    "2023-06-01": "El Nino begins",
    "2024-01-01": "AI power demand",
}


def setup_style():
    sns.set_theme(style="whitegrid")
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 180,
            "font.family": "DejaVu Sans",
            "axes.grid": True,
            "grid.alpha": 0.25,
        }
    )


def read_inputs():
    panel = pd.read_csv(ALIGNED_PANEL_PATH, index_col=0, parse_dates=True)
    corr = pd.read_csv(CROSS_CORR_PATH)
    rolling_path = TABLES_DIR / "rolling_corr_nss_adj_et_spread.csv"
    rolling = pd.read_csv(rolling_path, index_col=0, parse_dates=True).iloc[:, 0]
    rolling.name = "rolling_corr_26w"
    return panel, corr, rolling


def add_events(ax):
    for date_str, label in EVENTS.items():
        date = pd.Timestamp(date_str)
        ax.axvline(date, color="#9b2226", alpha=0.45, linewidth=0.8, linestyle=":")


def fig1_timeseries(panel):
    fig, axes = plt.subplots(3, 1, figsize=(14, 9.5), sharex=True, constrained_layout=True)

    axes[0].plot(panel.index, panel["TAI"], color="#d97706", linewidth=1.2)
    axes[0].axhline(0, color="#555555", linewidth=0.7, linestyle="--")
    axes[0].set_ylabel("TAI")
    axes[0].set_title("Climate Anomaly, News Sentiment, and Energy Transition Spread", pad=14)

    axes[1].plot(panel.index, panel["NSS_ADJ"], color="#2563eb", linewidth=1.2)
    axes[1].scatter(
        panel.index,
        panel["NSS_ADJ"],
        s=np.clip(panel["NEWS_COUNT"].fillna(0) * 1.6, 6, 48),
        color="#2563eb",
        alpha=0.45,
        edgecolor="none",
    )
    axes[1].axhline(0, color="#555555", linewidth=0.7, linestyle="--")
    axes[1].set_ylabel("NSS_ADJ")

    axes[2].plot(panel.index, panel["ET_SPREAD"], color="#15803d", linewidth=1.2)
    axes[2].fill_between(
        panel.index,
        panel["ET_SPREAD"],
        0,
        where=panel["ET_SPREAD"] >= 0,
        color="#16a34a",
        alpha=0.25,
    )
    axes[2].fill_between(
        panel.index,
        panel["ET_SPREAD"],
        0,
        where=panel["ET_SPREAD"] < 0,
        color="#dc2626",
        alpha=0.2,
    )
    axes[2].axhline(0, color="#555555", linewidth=0.7, linestyle="--")
    axes[2].set_ylabel("ICLN - XLE")

    for ax in axes:
        add_events(ax)
        ax.margins(x=0.01, y=0.12)

    output = FIGURES_DIR / "fig1_timeseries.png"
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def fig2_lag_heatmap(corr):
    subset = corr[
        (corr["signal"].isin(["TAI", "NSS_ADJ"]))
        & (corr["target"].isin(["NSS_ADJ", "ET_SPREAD", "ICLN", "XLE", "NEE", "XOM", "ETN"]))
    ].copy()
    subset["pair"] = subset["signal"] + " -> " + subset["target"]
    pivot = subset.pivot_table(index="pair", columns="lag_weeks", values="r", aggfunc="first")

    fig_height = max(6, 0.52 * len(pivot))
    fig, ax = plt.subplots(figsize=(14, fig_height), constrained_layout=True)
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".2f",
        annot_kws={"fontsize": 8},
        center=0,
        cmap="RdBu_r",
        linewidths=0.4,
        cbar_kws={"label": "Pearson r"},
        ax=ax,
    )
    ax.set_title("Lagged Correlation Heatmap", pad=14)
    ax.set_xlabel("Lag weeks (negative value means the signal comes earlier)", labelpad=10)
    ax.set_ylabel("")
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", labelsize=9)
    output = FIGURES_DIR / "fig2_lag_heatmap.png"
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def fig3_rolling_corr(rolling):
    fig, ax = plt.subplots(figsize=(14, 4.8), constrained_layout=True)
    ax.plot(rolling.index, rolling.values, color="#2563eb", linewidth=1.4)
    ax.axhline(0, color="#555555", linewidth=0.7, linestyle="--")
    ax.fill_between(
        rolling.index,
        rolling.values,
        0,
        where=rolling.values >= 0,
        color="#2563eb",
        alpha=0.18,
    )
    ax.fill_between(
        rolling.index,
        rolling.values,
        0,
        where=rolling.values < 0,
        color="#dc2626",
        alpha=0.15,
    )
    add_events(ax)
    ax.set_title("26-Week Rolling Correlation: NSS_ADJ vs ET_SPREAD", pad=14)
    ax.set_ylabel("Rolling r")
    ax.margins(x=0.01, y=0.18)
    output = FIGURES_DIR / "fig3_rolling_corr.png"
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def fig4_company_sensitivity(corr):
    companies = ["NEE", "XOM", "ETN"]
    rows = []
    for company in companies:
        subset = corr[
            (corr["signal"] == "NSS_ADJ")
            & (corr["target"] == company)
            & corr["r"].notna()
        ].copy()
        if subset.empty:
            continue
        best = subset.reindex(subset["r"].abs().sort_values(ascending=False).index).iloc[0]
        rows.append(best)

    best = pd.DataFrame(rows)
    if best.empty:
        raise RuntimeError("No company sensitivity rows available for Figure 4.")

    best.to_csv(TABLES_DIR / "company_sensitivity_best_lags.csv", index=False)

    colors = {"NEE": "#16a34a", "XOM": "#dc2626", "ETN": "#2563eb"}
    fig, ax = plt.subplots(figsize=(8.5, 5), constrained_layout=True)
    bars = ax.bar(
        best["target"],
        best["r"],
        color=[colors.get(t, "#555555") for t in best["target"]],
        alpha=0.85,
    )
    ax.axhline(0, color="#555555", linewidth=0.8)
    ax.set_ylabel("Best absolute lag correlation r")
    ax.set_title("Company Sensitivity to Adjusted News Sentiment", pad=14)
    ymax = max(0.05, best["r"].max())
    ymin = min(-0.05, best["r"].min())
    ax.set_ylim(ymin - 0.08, ymax + 0.08)

    for bar, (_, row) in zip(bars, best.iterrows()):
        label = f"lag={int(row['lag_weeks'])}, p={row['p_value']:.3f}"
        y = row["r"]
        offset = 0.025 if y >= 0 else -0.035
        va = "bottom" if y >= 0 else "top"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y + offset,
            label,
            ha="center",
            va=va,
            fontsize=8,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 1.8},
        )

    output = FIGURES_DIR / "fig4_company_sensitivity.png"
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def make_figures():
    ensure_project_dirs()
    setup_style()
    panel, corr, rolling = read_inputs()

    outputs = [
        fig1_timeseries(panel),
        fig2_lag_heatmap(corr),
        fig3_rolling_corr(rolling),
        fig4_company_sensitivity(corr),
    ]

    print("Saved figures:")
    for output in outputs:
        print(output)
    return outputs


if __name__ == "__main__":
    make_figures()
