"""Evaluation helpers for the 50-document development catalog.

The catalog informed development decisions, so its deterministic subgroups are
diagnostic slices rather than an independent validation/test split.
"""

from __future__ import annotations

import zlib

import numpy as np
import pandas as pd


def development_group_for_report(report_id: str, diagnostic_ratio: float = 0.28) -> str:
    """Assign a stable diagnostic subgroup without implying held-out status."""
    if not 0.0 <= diagnostic_ratio <= 1.0:
        raise ValueError("diagnostic_ratio must be between 0 and 1")
    bucket = zlib.crc32(str(report_id).encode("utf-8")) % 100
    return (
        "development_diagnostic"
        if bucket < int(diagnostic_ratio * 100)
        else "development_main"
    )


def summarize_development_results(
    result: pd.DataFrame, matched_col: str = "matched"
) -> pd.DataFrame:
    """Summarize agreement and coverage for development-catalog slices."""
    rows: list[dict[str, object]] = []
    if result.empty or matched_col not in result.columns:
        return pd.DataFrame(rows)

    groups = [("all_development", result)]
    if "split" in result.columns:
        groups.extend((split, group) for split, group in result.groupby("split"))

    for split, group in groups:
        available = (
            group[group["predicted_hint"] != "missing_pdf"]
            if "predicted_hint" in group
            else group
        )
        if available.empty:
            rows.append(
                {"split": split, "n": 0, "agreement": np.nan, "coverage": 0.0}
            )
            continue
        rows.append(
            {
                "split": split,
                "n": int(len(available)),
                "agreement": float(available[matched_col].astype(bool).mean()),
                "coverage": float(len(available) / len(group)) if len(group) else 0.0,
                "low_relevance_rate": (
                    float((available["ood_decision"] != "in_domain").mean())
                    if "ood_decision" in available.columns
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)
