"""Data layer — load the workbook and build the star schema.

Star schema
-----------
* Fact:        ``transactions`` (weekly grain, already in EUR)
* Dimensions:  ``products``, ``customers``, ``calendar``
* Budget fact: ``budget`` (monthly grain, Country × Category)

Critical modelling step: the weekly fact table is aggregated to the **monthly**
grain (Year, Month, Country, Category) so it can be joined to the Budget on
``(YearMonth, Country, Category)``. See :func:`build_model`.

Currency: ``Revenue``/``COGS`` are already in EUR (verified in data_profile.md),
so no FX conversion is applied. ``FX_Rates`` is loaded for reference only.
"""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

# Category-level target margins (from README / Products sheet)
TARGET_MARGINS = {
    "Beverages": 42.0,
    "Fresh Produce": 30.0,
    "Dry Goods": 48.0,
    "Frozen Food": 35.0,
}

COUNTRIES = ["France", "Germany", "UK"]
CATEGORIES = ["Beverages", "Fresh Produce", "Dry Goods", "Frozen Food"]
SEGMENTS = ["Hypermarket", "Supermarket", "Convenience", "Online"]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@dataclass
class Model:
    """Container for the full data model."""
    transactions: pd.DataFrame   # weekly fact (enriched)
    budget: pd.DataFrame         # monthly budget fact
    products: pd.DataFrame       # product dimension
    customers: pd.DataFrame      # customer dimension
    calendar: pd.DataFrame       # Jan 2023 -> Mar 2025
    fx_rates: pd.DataFrame       # reference only
    monthly: pd.DataFrame        # actuals aggregated to month x country x category
    variance: pd.DataFrame       # monthly actual vs budget, with variance decomposition


def _year_month(df: pd.DataFrame) -> pd.Series:
    """Build a 'YYYY-MM' period key from Year + Month columns."""
    return df["Year"].astype(int).astype(str) + "-" + df["Month"].astype(int).map("{:02d}".format)


def load_workbook(path: str) -> dict[str, pd.DataFrame]:
    """Read every data sheet from the Excel workbook."""
    xl = pd.ExcelFile(path)
    sheets = {name: pd.read_excel(xl, name)
              for name in ["Transactions", "Budget", "Products", "Customers", "FX_Rates"]}
    return sheets


def build_calendar() -> pd.DataFrame:
    """Calendar dimension spanning Jan 2023 -> Mar 2025 (forecast horizon)."""
    rng = pd.date_range("2023-01-01", "2025-03-31", freq="MS")
    cal = pd.DataFrame({"MonthStart": rng})
    cal["Year"] = cal.MonthStart.dt.year
    cal["Month"] = cal.MonthStart.dt.month
    cal["Quarter"] = "Q" + cal.MonthStart.dt.quarter.astype(str)
    cal["MonthName"] = cal.MonthStart.dt.strftime("%b")
    cal["YearMonth"] = _year_month(cal)
    cal["Label"] = cal.MonthStart.dt.strftime("%b %Y")
    cal["IsForecast"] = cal.MonthStart > pd.Timestamp("2024-12-31")
    return cal


def build_model(path: str) -> Model:
    """Load the workbook and assemble the complete star schema + derived tables."""
    s = load_workbook(path)
    tx, budget = s["Transactions"].copy(), s["Budget"].copy()
    products, customers, fx = s["Products"].copy(), s["Customers"].copy(), s["FX_Rates"].copy()

    # --- enrich the fact table -------------------------------------------- #
    tx["Date"] = pd.to_datetime(tx["Date"])
    tx["YearMonth"] = _year_month(tx)
    tx["Target_Margin_Pct"] = tx["Category"].map(TARGET_MARGINS)
    # Customer_ID for completeness of the customer relationship
    tx = tx.merge(customers[["Customer_Name", "Customer_ID"]],
                  left_on="Customer", right_on="Customer_Name", how="left")
    tx.drop(columns=["Customer_Name"], inplace=True)

    budget["YearMonth"] = _year_month(budget)

    calendar = build_calendar()

    # --- aggregate weekly actuals -> monthly grain ----------------------- #
    monthly = (
        tx.groupby(["Year", "Month", "Quarter", "YearMonth", "Country", "Category"], as_index=False)
        .agg(Revenue=("Revenue", "sum"),
             COGS=("COGS", "sum"),
             Gross_Margin=("Gross_Margin", "sum"),
             Volume=("Volume", "sum"))
    )
    monthly["Margin_Pct"] = monthly["Gross_Margin"] / monthly["Revenue"] * 100

    # --- monthly actual vs budget + price/volume variance decomposition --- #
    variance = monthly.merge(
        budget[["YearMonth", "Country", "Category", "Budget_Revenue",
                "Budget_COGS", "Budget_Volume", "Budget_Gross_Margin"]],
        on=["YearMonth", "Country", "Category"], how="left",
    )
    variance["Rev_Variance"] = variance["Revenue"] - variance["Budget_Revenue"]
    variance["Rev_Variance_Pct"] = variance["Rev_Variance"] / variance["Budget_Revenue"] * 100
    variance["GM_Variance"] = variance["Gross_Margin"] - variance["Budget_Gross_Margin"]

    # Price/volume bridge:
    #   Volume var = (Actual_Vol - Budget_Vol) * Budget_Price
    #   Price  var = (Actual_Price - Budget_Price) * Actual_Vol
    #   Volume var + Price var == Revenue variance  (exact identity)
    b_price = variance["Budget_Revenue"] / variance["Budget_Volume"]
    a_price = variance["Revenue"] / variance["Volume"]
    variance["Budget_Price"] = b_price
    variance["Actual_Price"] = a_price
    variance["Volume_Variance"] = (variance["Volume"] - variance["Budget_Volume"]) * b_price
    variance["Price_Variance"] = (a_price - b_price) * variance["Volume"]

    return Model(
        transactions=tx, budget=budget, products=products, customers=customers,
        calendar=calendar, fx_rates=fx, monthly=monthly, variance=variance,
    )
