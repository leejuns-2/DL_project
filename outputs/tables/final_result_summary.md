# Final Result Summary

## Project Status

The project pipeline has been completed through the expanded Report-to-Market workflow:

1. Stock data collection
2. Climate data collection
3. News collection
4. FinBERT sentiment extraction
5. Weekly time-series alignment
6. Cross-correlation analysis
7. Rolling correlation analysis
8. Final visualizations
9. Result interpretation
10. PDF report evidence retrieval
11. Few-shot report signal generation
12. Report signal to stock-return linking

## Data Summary

| Dataset | File | Coverage / Size | Status |
|---|---|---:|---|
| Stock weekly returns | `data/processed/stock_returns_weekly.csv` | 312 weeks, 2019-01-11 to 2024-12-27 | Complete |
| Climate weekly TAI | `data/processed/climate_weekly_tai.csv` | 311 weeks, 2019-01-18 to 2024-12-27 | Complete |
| Raw news headlines | `data/raw/news/news_headlines_raw.csv` | 3,340 articles, 2019-01-05 to 2024-12-14 | Partial but usable |
| Weekly news sentiment | `data/processed/news_sentiment_weekly.csv` | 100 observed news weeks | Complete for collected weeks |
| Aligned weekly panel | `data/processed/aligned_weekly_panel.csv` | 312 weeks | Complete |
| PDF report signals | `data/processed/reports/report_signals.csv` | 5 reports | Complete |
| Report-stock link | `data/processed/reports/report_stock_link.csv` | 5 reports | Complete |

## Hypothesis Results

| Hypothesis | Result | Evidence |
|---|---|---|
| H1: TAI leads news sentiment by 1-2 weeks | Not supported | Best observed TAI -> NSS_ADJ relation was lag +2, `r=-0.1208`, `p=0.2360`, not significant. |
| H2: NSS_ADJ leads positive ET_SPREAD movement | Not supported | Best NSS_ADJ -> ET_SPREAD relation was lag +4, `r=-0.1891`, `p=0.0622`, weak and negative. |
| H3: Relationships strengthen around event periods | Partially supported descriptively | Rolling correlation varied over time, with stronger negative values around 2022 H2 and early 2023. This is descriptive rather than causal. |

## Key Correlation Findings

| Signal -> Target | Best Lag | r | p-value | Interpretation |
|---|---:|---:|---:|---|
| TAI -> NSS | +2 | -0.1072 | 0.2936 | No statistically meaningful relationship |
| TAI -> NSS_ADJ | +2 | -0.1208 | 0.2360 | No statistically meaningful relationship |
| NSS_ADJ -> ET_SPREAD | +4 | -0.1891 | 0.0622 | Weak, not significant, opposite to H2 direction |
| NSS_ADJ -> NEE | +2 | -0.1809 | 0.0731 | Weak, not significant |
| NSS_ADJ -> XOM | +4 | 0.2161 | 0.0326 | Weak but statistically significant |
| NSS_ADJ -> ETN | +3 | 0.1995 | 0.0477 | Weak but statistically significant |

## Rolling Correlation Summary

Rolling correlation was computed between `NSS_ADJ` and `ET_SPREAD`.

| Metric | Value |
|---|---:|
| Number of rolling observations | 89 |
| Date range | 2021-10-08 to 2024-12-20 |
| Mean rolling correlation | -0.1216 |
| Minimum rolling correlation | -0.4627 |
| Maximum rolling correlation | 0.2378 |

The strongest absolute rolling correlations were negative and appeared around early 2023 and parts of 2022 H2.

## Interpretation

The results do not provide strong evidence that climate anomaly or FinBERT-based energy news sentiment predicts the clean-versus-fossil energy return spread. However, the project successfully demonstrates the main course concept: using a frozen Foundation Model to transform unstructured news headlines into a numerical signal, then integrating that signal with climate and financial time-series data.

The more defensible conclusion is:

> FinBERT-derived energy news sentiment can be connected to market and climate time series, but in this dataset the strongest relationships are weak, event-dependent, and more visible in company-level reactions than in the ICLN-XLE spread.

## Limitations

- GDELT rate limits caused incomplete weekly news coverage.
- News sentiment is based on collected headline weeks only.
- FinBERT is a financial sentiment model, not a model fine-tuned specifically for climate or energy policy news.
- Correlation does not imply causality.
- Weekly aggregation smooths short-term market reactions.

## Presentation Message

This project should be presented as a relationship-analysis pipeline, not a prediction system.

The key Foundation Model connection:

> FinBERT was used as a frozen Foundation Model to convert energy-related news headlines into weekly numerical sentiment signals. These signals were then aligned with climate anomaly and stock-return data to analyze lagged relationships.

Expanded Foundation Model message:

> The final version also includes a PDF-to-market-signal pipeline. Energy reports are converted to text, relevant evidence paragraphs are retrieved, and a general-purpose Transformer embedding model is used in a few-shot setting to score renewable opportunity, fossil pressure, grid infrastructure, and climate risk. These report-level scores are then linked to downstream ETF and company returns.
