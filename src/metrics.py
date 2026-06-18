"""Measures & analytics — every metric the brief asks for.

All functions operate on already-filtered DataFrames so the same logic powers
both the global slicers and the page-level breakdowns. Revenue is in EUR.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# Core measures                                                               #
# --------------------------------------------------------------------------- #
def core_kpis(tx: pd.DataFrame) -> dict:
    """Total Revenue, COGS, Gross Margin, Margin %, Volume, Avg Unit Price."""
    rev = float(tx["Revenue"].sum())
    cogs = float(tx["COGS"].sum())
    gm = float(tx["Gross_Margin"].sum())
    vol = float(tx["Volume"].sum())
    return {
        "revenue": rev,
        "cogs": cogs,
        "gross_margin": gm,
        "margin_pct": (gm / rev * 100) if rev else 0.0,
        "volume": vol,
        "avg_unit_price": (rev / vol) if vol else 0.0,   # Revenue/Volume, not mean(Unit_Price)
    }


def yoy_growth(tx: pd.DataFrame, base: int = 2023, comp: int = 2024) -> dict:
    """Year-over-year revenue growth comp vs base (default 2024 vs 2023)."""
    by_year = tx.groupby("Year")["Revenue"].sum()
    rev_base = float(by_year.get(base, 0.0))
    rev_comp = float(by_year.get(comp, 0.0))
    pct = ((rev_comp / rev_base - 1) * 100) if rev_base else np.nan
    return {"base": rev_base, "comp": rev_comp, "delta": rev_comp - rev_base, "pct": pct}


# --------------------------------------------------------------------------- #
# Budget variance                                                             #
# --------------------------------------------------------------------------- #
def variance_summary(var: pd.DataFrame) -> dict:
    """Aggregate actual vs budget over a (filtered) variance frame."""
    actual = float(var["Revenue"].sum())
    budget = float(var["Budget_Revenue"].sum())
    diff = actual - budget
    return {
        "actual": actual,
        "budget": budget,
        "variance": diff,
        "variance_pct": (diff / budget * 100) if budget else np.nan,
        "price_variance": float(var["Price_Variance"].sum()),
        "volume_variance": float(var["Volume_Variance"].sum()),
    }


# --------------------------------------------------------------------------- #
# Product margin gap vs category target                                       #
# --------------------------------------------------------------------------- #
def product_margins(tx: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Per-SKU realised margin vs category target, with the gap and a flag."""
    g = (tx.groupby("SKU", as_index=False)
         .agg(Revenue=("Revenue", "sum"), Gross_Margin=("Gross_Margin", "sum"),
              Volume=("Volume", "sum")))
    g["Margin_Pct"] = g["Gross_Margin"] / g["Revenue"] * 100
    g = g.merge(products[["SKU", "Product_Name", "Category", "Target_Margin_Pct"]], on="SKU")
    g["Gap_pp"] = g["Margin_Pct"] - g["Target_Margin_Pct"]
    g["Below_Target"] = g["Gap_pp"] < -0.05   # tolerance for rounding noise
    return g.sort_values("Gap_pp")


# --------------------------------------------------------------------------- #
# Forecast & what-if                                                          #
# --------------------------------------------------------------------------- #
FORECAST_MONTHS = [(2025, 1), (2025, 2), (2025, 3)]


def forecast_q1_2025(tx: pd.DataFrame, growth_pct: float) -> pd.DataFrame:
    """Project Jan–Mar 2025 revenue by applying a growth rate to the same
    months of 2024 (seasonal-naive forecast).

    Returns one row per forecast month with central / optimistic / pessimistic
    figures. Optimistic and pessimistic use the slider bounds (+20% / −10%).
    """
    base = (tx[tx["Year"] == 2024]
            .groupby("Month")["Revenue"].sum())
    rows = []
    for (yr, mth) in FORECAST_MONTHS:
        b = float(base.get(mth, 0.0))
        rows.append({
            "Year": yr, "Month": mth,
            "Label": pd.Timestamp(yr, mth, 1).strftime("%b %Y"),
            "Baseline_2024": b,
            "Central": b * (1 + growth_pct / 100),
            "Optimistic": b * (1 + 20 / 100),
            "Pessimistic": b * (1 - 10 / 100),
        })
    return pd.DataFrame(rows)


def scenario_impact(tx: pd.DataFrame, online_growth: float = 20.0,
                    convenience_decline: float = 10.0, year: int = 2024) -> dict:
    """Net revenue impact of: Online +online_growth%, Convenience −convenience_decline%.

    Computed on the chosen base year (default 2024, the latest full year).
    """
    base = tx[tx["Year"] == year].groupby("Segment")["Revenue"].sum()
    online = float(base.get("Online", 0.0))
    conv = float(base.get("Convenience", 0.0))
    online_delta = online * online_growth / 100
    conv_delta = -conv * convenience_decline / 100
    return {
        "online_base": online, "convenience_base": conv,
        "online_delta": online_delta, "convenience_delta": conv_delta,
        "net_delta": online_delta + conv_delta,
        "total_base": float(base.sum()),
    }


def segment_scenario_table(tx: pd.DataFrame, adjustments: dict[str, float],
                           year: int = 2024) -> pd.DataFrame:
    """Generic segment simulator: apply a % adjustment per segment to the base year."""
    base = (tx[tx["Year"] == year].groupby("Segment", as_index=False)["Revenue"].sum()
            .rename(columns={"Revenue": "Base"}))
    base["Adj_Pct"] = base["Segment"].map(adjustments).fillna(0.0)
    base["Scenario"] = base["Base"] * (1 + base["Adj_Pct"] / 100)
    base["Delta"] = base["Scenario"] - base["Base"]
    return base


def required_growth_for_target(tx: pd.DataFrame, target: float = 2_500_000.0,
                               base_year: int = 2024) -> dict:
    """Annual revenue growth rate required to reach `target` in the next year."""
    base = float(tx[tx["Year"] == base_year]["Revenue"].sum())
    rate = (target / base - 1) * 100 if base else np.nan
    return {"base": base, "target": target, "required_growth_pct": rate}
