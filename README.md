# EuroFoods S.A. — FP&A Performance Dashboard

An agency-grade **Streamlit** application that replicates and extends the Power BI
dashboard from the Session 5 case-study brief. It analyses two years of EuroFoods
sales (Jan 2023 – Dec 2024) across 3 countries, 4 categories, 4 channels and 20
products, and projects Q1 2025.

![Data as of December 2024](https://img.shields.io/badge/Data%20as%20of-December%202024-0891B2)

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Make sure the workbook sits next to app.py
#    (case_study_eurofoods.xlsx — included in this repo)

# 3. Launch
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## What's inside

A 4-page dashboard with **global slicers** (Country / Year / Quarter / Category /
Segment) in the sidebar:

| Page | Highlights |
|---|---|
| **Executive Summary** | KPI cards (Revenue, Gross Margin, Margin %, YoY); Revenue by country *actual vs budget*; monthly revenue overlay 2023 vs 2024; segment donut. |
| **Category Deep-Dive** | Revenue category × country (stacked); 24-month margin-% lines with target reference; margin matrix with conditional formatting; Top-10 products; products below target margin. |
| **Budget Variance** | Budget → Actual waterfall by category; quarterly variance by country; Country × Category matrix (Actual / Budget / Variance € / Var %); price-vs-volume bridge. |
| **Forecast & What-If** | Growth slider (−10% → +20%); Jan–Mar 2025 projection (central / optimistic / pessimistic); per-segment scenario simulator; back-solve for the €2.5M 2025 target. |

## Project structure

```
.
├── app.py                  # Streamlit app: routing, pages, charts
├── src/
│   ├── data.py             # Star schema: load workbook, monthly aggregation, variance bridge
│   ├── metrics.py          # Measures: KPIs, YoY, variance, forecast, scenarios
│   └── theme.py            # Palette, Plotly template, number formatting, KPI-card CSS
├── case_study_eurofoods.xlsx
├── data_profile.md         # Step 0 — data profiling report (types, keys, anomalies)
├── findings.md             # Step 4 — written answers to the 11 analytical questions
├── requirements.txt
└── README.md
```

## Data model (star schema)

- **Fact** — `Transactions` (weekly grain, already in EUR).
- **Dimensions** — `Products`, `Customers`, `Calendar` (Jan 2023 → Mar 2025, built in code).
- **Budget fact** — monthly targets at Country × Category grain.

**Critical step:** the weekly fact table is aggregated to the **monthly** grain
`(Year, Month, Country, Category)` so it can be joined to the Budget on
`(YearMonth, Country, Category)`. The price/volume variance bridge satisfies the
exact identity `Price variance + Volume variance = Revenue variance`.

**Currency:** Revenue is **already in EUR** for all three countries (verified in
`data_profile.md`), so **no FX conversion** is applied. `FX_Rates` is loaded for
reference only.

## Visual standard

- **Plotly** for every chart, custom template + CSS KPI cards.
- Palette — Teal `#0891B2` (actual), Amber `#F59E0B` (budget), Red `#EF4444`
  (unfavourable), Green `#10B981` (favourable).
- Formatting — `€#,##0`, `0.0%`, signed variances; data labels suppressed on
  charts with >10 points; persistent **"Data as of: December 2024"** badge.
- Data is cached with `@st.cache_data`.

## Notes

- The Segment slicer does not apply on the **Budget Variance** page — Budget has
  no segment dimension (Country × Category × Month only). The page flags this.
- Forecast periods (Jan–Mar 2025) carry no actuals and are modelled from 2024
  seasonality times the growth assumption.
