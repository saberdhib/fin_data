# Data Profile — `case_study_eurofoods.xlsx`

*Profiling run prior to any modelling. Column names were read directly from the
workbook (not assumed). Generated for the EuroFoods S.A. FP&A case study.*

## 1. Workbook overview

| Sheet | Rows | Cols | Grain | Role |
|---|---|---|---|---|
| `README` | 41 | 3 | — | Documentation / context |
| `Transactions` | 25,200 | 20 | One row per weekly product sale (date × country × customer × SKU) | **Fact table** |
| `Budget` | 288 | 9 | Year × Month × Country × Category (3×4×24 = 288 ✓) | Fact (targets) |
| `Products` | 20 | 7 | One row per SKU | Dimension |
| `Customers` | 36 | 7 | One row per Customer_Name | Dimension |
| `FX_Rates` | 48 | 5 | Year × Month × Currency_Pair (2 pairs × 24 = 48 ✓) | Reference |

## 2. Exact columns

- **Transactions**: `Transaction_ID, Date, Year, Month, Quarter, Week, Country, Region, Customer, Segment, Category, SKU, Product, Volume, Unit_Price, Unit_Cost, Revenue, COGS, Gross_Margin, Margin_Pct`
- **Budget**: `Year, Month, Quarter, Country, Category, Budget_Revenue, Budget_COGS, Budget_Volume, Budget_Gross_Margin`
- **Products**: `SKU, Product_Name, Category, List_Price, Standard_Cost, Target_Margin_Pct, Status`
- **Customers**: `Customer_ID, Customer_Name, Country, Region, Segment, Credit_Terms, Status`
- **FX_Rates**: `Year, Month, Currency_Pair, Rate, Note`

## 3. Keys, grains and join consistency

| Join | Keys | Result |
|---|---|---|
| Transactions → Products | `SKU` | ✅ 20/20 SKUs match. No orphans. |
| Transactions → Customers | `Customer` = `Customer_Name` | ✅ 36/36 match. No orphans. |
| Transactions ↔ Customers attributes | `Country`, `Segment` per customer | ✅ 0 mismatches — every customer's Country/Segment in the fact table agrees with the master. |
| Transactions → Budget | `(Year, Month, Country, Category)` | ✅ Budget grain is **monthly**, transactions are **weekly** → must aggregate the fact to month before joining (see modelling note). |

Dimension domains are perfectly aligned across sheets:
- **Countries** (3): France, Germany, UK
- **Regions** (3): Western Europe (FR), Central Europe (DE), Northern Europe (UK)
- **Categories** (4): Beverages, Fresh Produce, Dry Goods, Frozen Food
- **Segments / channels** (4): Hypermarket, Supermarket, Convenience, Online

## 4. Date coverage

- **Transactions**: 2023-01-02 → 2024-12-30, weekly. Years {2023, 2024}, all 12 months present. **No data beyond Dec 2024.**
- **Budget**: 2023-01 → 2024-12, monthly.
- **FX_Rates**: 2023-01 → 2024-12.
- ⚠️ The brief asks for a Calendar dimension running **Jan 2023 → Mar 2025** and a **Jan–Mar 2025 forecast**. Those three months are *future* periods with **no actuals** — they exist only for the forecast/what-if page. The dashboard's official cut-off is therefore **"Data as of: December 2024"**.

## 5. Data quality

| Check | Result |
|---|---|
| Null values (any sheet) | **0** |
| Duplicate `Transaction_ID` | **0** |
| `Volume <= 0` | 0 |
| `Revenue <= 0` | 0 |
| Negative `Gross_Margin` / `Margin_Pct` | **0** (no loss-making lines) |
| `Gross_Margin` vs `Revenue − COGS` | Identical (max diff 5.7e-14) — internally consistent |
| `Revenue` vs `Volume × Unit_Price` | Max diff €0.68 — explained by `Unit_Price` being rounded to 2 dp; Revenue is the authoritative figure |
| Product `Status` | All 20 **Active** |
| Customer `Status` | All 36 **Active** |

The dataset is exceptionally clean: no missing values, no duplicates, no referential-integrity breaks, no negative margins.

## 6. Currency — is conversion needed?

**No.** `Revenue`, `COGS`, `Gross_Margin`, `Unit_Price` and `Unit_Cost` are **already expressed in EUR** for all three countries:

- The README never mentions a transaction currency other than EUR.
- There is **no currency column** in `Transactions`.
- Transaction `Unit_Price` values line up with the EUR `List_Price` in `Products` for every country, including the UK (e.g. BEV-001 list price €3.20; UK unit prices cluster around €3.0–3.3). If UK figures were in GBP they would be ~14% lower than the EUR list price, which they are not.

`FX_Rates` (EUR/GBP, EUR/USD) is provided as **reference / a modelling distractor**. The app loads it and exposes it for transparency, but applies **no FX conversion** because the fact table is already in EUR. This is documented in code.

## 7. Headline numbers (sanity baseline)

| Metric | Value |
|---|---|
| Total Revenue (2 yrs) | €4,604,418 |
| Total Budget Revenue | €4,830,965 |
| Total Budget Variance | **−€226,547 (−4.7%, unfavourable)** |
| Revenue 2023 | €2,241,376 |
| Revenue 2024 | €2,363,042 |
| **YoY growth 2024 vs 2023** | **+5.4%** |
| Blended Gross Margin % | ~38.7% (very even across countries: FR 38.7%, DE 38.8%, UK 38.7%) |

## 8. Anomalies & analyst notes

1. **Actuals consistently under budget (−4.7%).** Every country's revenue lands below plan — budgets were set optimistically. This is the central story of the Budget Variance page, not a data error.
2. **11 of 20 products sit *marginally* below their category target margin** (e.g. Beverages 41.8% vs 42% target). The gaps are small (tenths of a point) and reflect realised vs list-price erosion rather than structurally unprofitable products — worth flagging but not alarming. The app surfaces the full list with the size of each gap.
3. **Target margins are category-level** (Beverages 42%, Fresh Produce 30%, Dry Goods 48%, Frozen Food 35%) and identical for every SKU in a category.
4. **Budget has no Segment dimension.** Variance analysis is therefore only valid at the Country × Category × Month grain; segment slicers apply to actuals only.
5. **Forecast periods (Jan–Mar 2025) carry no actuals** and must be modelled.
6. `Unit_Price` is rounded; always derive average price as `Revenue / Volume` rather than averaging `Unit_Price`.
