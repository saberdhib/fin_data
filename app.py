"""EuroFoods S.A. — FP&A Performance Dashboard (Streamlit).

Run with:  streamlit run app.py

A 4-page, agency-grade replica (and extension) of the Power BI dashboard from
the Session 5 case-study brief:

    1. Executive Summary
    2. Category Deep-Dive
    3. Budget Variance
    4. Forecast & What-If

Architecture
------------
* ``src/data.py``    – loads the workbook, builds the star schema + monthly/variance tables
* ``src/metrics.py`` – every measure (KPIs, YoY, variance bridge, forecast, scenarios)
* ``src/theme.py``   – palette, Plotly template, number formatting, KPI-card CSS
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import metrics as M
from src import theme as T

DATA_PATH = os.path.join(os.path.dirname(__file__), "case_study_eurofoods.xlsx")

st.set_page_config(page_title="EuroFoods — FP&A Dashboard",
                   page_icon="🥨", layout="wide", initial_sidebar_state="expanded")


# --------------------------------------------------------------------------- #
# Cached data                                                                 #
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Building data model…")
def load_model() -> D.Model:
    return D.build_model(DATA_PATH)


# --------------------------------------------------------------------------- #
# Filtering helpers                                                           #
# --------------------------------------------------------------------------- #
def filter_tx(tx: pd.DataFrame, f: dict) -> pd.DataFrame:
    """Apply all five global slicers to the (weekly) fact table."""
    m = pd.Series(True, index=tx.index)
    if f["countries"]:
        m &= tx["Country"].isin(f["countries"])
    if f["years"]:
        m &= tx["Year"].isin(f["years"])
    if f["quarters"]:
        m &= tx["Quarter"].isin(f["quarters"])
    if f["categories"]:
        m &= tx["Category"].isin(f["categories"])
    if f["segments"]:
        m &= tx["Segment"].isin(f["segments"])
    return tx[m]


def filter_monthly(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    """Filter pre-aggregated monthly/variance frames.

    These tables have no Segment dimension (Budget is set at Country × Category
    × Month), so the Segment slicer does not apply here — by design.
    """
    m = pd.Series(True, index=df.index)
    if f["countries"]:
        m &= df["Country"].isin(f["countries"])
    if f["years"]:
        m &= df["Year"].isin(f["years"])
    if f["quarters"]:
        m &= df["Quarter"].isin(f["quarters"])
    if f["categories"]:
        m &= df["Category"].isin(f["categories"])
    return df[m]


# --------------------------------------------------------------------------- #
# Shared UI bits                                                              #
# --------------------------------------------------------------------------- #
def page_header(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="page-title">{title}</div>'
                f'<div class="page-sub">{subtitle}</div>', unsafe_allow_html=True)


def asof_badge() -> None:
    st.markdown(
        f'<span class="asof-badge"><span class="dot"></span>Data as of: {T.DATA_AS_OF}</span>',
        unsafe_allow_html=True,
    )


def maybe_text(fig: go.Figure, n_points: int, texttemplate: str, **kw) -> None:
    """Show data labels only when there are <= 10 points (per the visual standard)."""
    if n_points <= 10:
        fig.update_traces(texttemplate=texttemplate, textposition=kw.get("pos", "outside"),
                          cliponaxis=False)


# =========================================================================== #
# PAGE 1 — EXECUTIVE SUMMARY                                                   #
# =========================================================================== #
def page_executive(model: D.Model, f: dict) -> None:
    tx = filter_tx(model.transactions, f)
    var = filter_monthly(model.variance, f)
    page_header("Executive Summary",
                "Group-level performance across France, Germany & the UK — actuals vs plan.")
    asof_badge()
    st.write("")

    k = M.core_kpis(tx)
    yoy = M.yoy_growth(tx)
    vs = M.variance_summary(var)

    cards = [
        T.kpi_card("Total Revenue", T.fmt_eur_compact(k["revenue"]),
                   f"{T.fmt_signed_eur(vs['variance'])} vs budget",
                   T.variance_color(vs["variance"]), T.TEAL),
        T.kpi_card("Gross Margin", T.fmt_eur_compact(k["gross_margin"]),
                   f"COGS {T.fmt_eur_compact(k['cogs'])}", T.MUTED, T.TEAL),
        T.kpi_card("Margin %", T.fmt_pct(k["margin_pct"]),
                   f"Avg price {T.fmt_eur(k['avg_unit_price'], 2)}", T.MUTED, T.GREEN),
        T.kpi_card("YoY Growth", T.fmt_signed_pct(yoy["pct"]),
                   f"2024 vs 2023 · {T.fmt_signed_eur(yoy['delta'])}",
                   T.variance_color(yoy["pct"]), T.AMBER),
    ]
    st.markdown(T.kpi_row(cards), unsafe_allow_html=True)
    st.write("")

    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.markdown('<div class="section-title">Revenue by country — Actual vs Budget</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(_chart_rev_vs_budget(var), use_container_width=True)
    with c2:
        st.markdown('<div class="section-title">Revenue by segment</div>', unsafe_allow_html=True)
        st.plotly_chart(_chart_segment_donut(tx), use_container_width=True)

    st.markdown('<div class="section-title">Monthly revenue — 2023 vs 2024</div>',
                unsafe_allow_html=True)
    st.plotly_chart(_chart_monthly_overlay(tx), use_container_width=True)


def _chart_rev_vs_budget(var: pd.DataFrame) -> go.Figure:
    g = var.groupby("Country", as_index=False).agg(Actual=("Revenue", "sum"),
                                                    Budget=("Budget_Revenue", "sum"))
    g = g.sort_values("Actual", ascending=False)
    fig = go.Figure()
    fig.add_bar(x=g["Country"], y=g["Actual"], name="Actual", marker_color=T.TEAL,
                text=[T.fmt_eur_compact(v) for v in g["Actual"]], textposition="outside")
    fig.add_bar(x=g["Country"], y=g["Budget"], name="Budget", marker_color=T.AMBER,
                text=[T.fmt_eur_compact(v) for v in g["Budget"]], textposition="outside")
    fig.update_layout(barmode="group", yaxis_title="Revenue (€)", xaxis_title=None)
    return T.style_fig(fig, 360)


def _chart_segment_donut(tx: pd.DataFrame) -> go.Figure:
    g = tx.groupby("Segment", as_index=False)["Revenue"].sum()
    order = [s for s in D.SEGMENTS if s in set(g["Segment"])]
    g = g.set_index("Segment").reindex(order).reset_index()
    fig = go.Figure(go.Pie(labels=g["Segment"], values=g["Revenue"], hole=0.62,
                           marker=dict(colors=T.CATEGORICAL[:len(g)]),
                           textinfo="percent", sort=False))
    fig.update_layout(annotations=[dict(text="Segment<br>mix", x=0.5, y=0.5,
                                        font_size=14, showarrow=False, font_color=T.MUTED)])
    return T.style_fig(fig, 360)


def _chart_monthly_overlay(tx: pd.DataFrame) -> go.Figure:
    g = tx.groupby(["Year", "Month"], as_index=False)["Revenue"].sum()
    fig = go.Figure()
    palette = {2023: T.AMBER, 2024: T.TEAL}
    for yr in sorted(g["Year"].unique()):
        sub = g[g["Year"] == yr].sort_values("Month")
        fig.add_scatter(x=[D.MONTH_NAMES[m - 1] for m in sub["Month"]], y=sub["Revenue"],
                        mode="lines+markers", name=str(yr),
                        line=dict(color=palette.get(yr, T.MUTED), width=3),
                        marker=dict(size=6))
    fig.update_layout(yaxis_title="Revenue (€)", xaxis_title=None)
    return T.style_fig(fig, 360)


# =========================================================================== #
# PAGE 2 — CATEGORY DEEP-DIVE                                                  #
# =========================================================================== #
def page_category(model: D.Model, f: dict) -> None:
    tx = filter_tx(model.transactions, f)
    page_header("Category Deep-Dive",
                "Revenue, margin and product economics across the four categories.")
    asof_badge()
    st.write("")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-title">Revenue by category × country</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(_chart_cat_country_stacked(tx), use_container_width=True)
    with c2:
        st.markdown('<div class="section-title">Margin % by category — 24 months</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(_chart_margin_lines(tx), use_container_width=True)

    st.markdown('<div class="section-title">Margin % matrix — category × country</div>',
                unsafe_allow_html=True)
    st.caption("Conditional formatting: green = stronger margin, red = weaker.")
    st.dataframe(_matrix_margin(tx), use_container_width=True)

    c3, c4 = st.columns([1.2, 1])
    with c3:
        st.markdown('<div class="section-title">Top 10 products by revenue</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(_chart_top_products(tx, model.products), use_container_width=True)
    with c4:
        st.markdown('<div class="section-title">Products below target margin</div>',
                    unsafe_allow_html=True)
        st.dataframe(_table_below_target(tx, model.products), use_container_width=True,
                     height=360)


def _chart_cat_country_stacked(tx: pd.DataFrame) -> go.Figure:
    g = tx.groupby(["Category", "Country"], as_index=False)["Revenue"].sum()
    fig = go.Figure()
    for i, country in enumerate(D.COUNTRIES):
        sub = g[g["Country"] == country]
        fig.add_bar(x=sub["Category"], y=sub["Revenue"], name=country,
                    marker_color=T.CATEGORICAL[i])
    fig.update_layout(barmode="stack", yaxis_title="Revenue (€)", xaxis_title=None)
    return T.style_fig(fig, 380)


def _chart_margin_lines(tx: pd.DataFrame) -> go.Figure:
    g = (tx.groupby(["YearMonth", "Category"], as_index=False)
         .agg(GM=("Gross_Margin", "sum"), Rev=("Revenue", "sum")))
    g["Margin_Pct"] = g["GM"] / g["Rev"] * 100
    fig = go.Figure()
    cats = [c for c in D.CATEGORIES if c in set(g["Category"])]
    for i, cat in enumerate(cats):
        sub = g[g["Category"] == cat].sort_values("YearMonth")
        fig.add_scatter(x=sub["YearMonth"], y=sub["Margin_Pct"], mode="lines",
                        name=cat, line=dict(width=2.5, color=T.CATEGORICAL[i]))
        # target line per category
        tgt = D.TARGET_MARGINS[cat]
        fig.add_hline(y=tgt, line=dict(color=T.CATEGORICAL[i], width=1, dash="dot"),
                      opacity=0.35)
    fig.update_layout(yaxis_title="Margin %", xaxis_title=None,
                      yaxis_ticksuffix="%")
    fig.update_xaxes(tickangle=-45, nticks=12)
    return T.style_fig(fig, 380)


def _matrix_margin(tx: pd.DataFrame):
    g = (tx.groupby(["Category", "Country"], as_index=False)
         .agg(GM=("Gross_Margin", "sum"), Rev=("Revenue", "sum")))
    g["Margin_Pct"] = g["GM"] / g["Rev"] * 100
    pivot = g.pivot(index="Category", columns="Country", values="Margin_Pct")
    pivot = pivot.reindex([c for c in D.CATEGORIES if c in pivot.index])
    styled = (pivot.style
              .background_gradient(cmap="RdYlGn", axis=None)
              .format("{:.1f}%"))
    return styled


def _chart_top_products(tx: pd.DataFrame, products: pd.DataFrame) -> go.Figure:
    g = (tx.groupby("Product", as_index=False)["Revenue"].sum()
         .sort_values("Revenue", ascending=True).tail(10))
    fig = go.Figure(go.Bar(y=g["Product"], x=g["Revenue"], orientation="h",
                           marker_color=T.TEAL))
    fig.update_layout(xaxis_title="Revenue (€)", yaxis_title=None)
    return T.style_fig(fig, 380)


def _table_below_target(tx: pd.DataFrame, products: pd.DataFrame):
    pm = M.product_margins(tx, products)
    below = pm[pm["Below_Target"]].copy()
    if below.empty:
        return pd.DataFrame({"Result": ["All products meet their category target ✓"]})
    out = below[["Product_Name", "Category", "Margin_Pct", "Target_Margin_Pct", "Gap_pp"]].copy()
    out.columns = ["Product", "Category", "Margin %", "Target %", "Gap (pp)"]
    return (out.style
            .format({"Margin %": "{:.1f}%", "Target %": "{:.0f}%", "Gap (pp)": "{:+.1f}"})
            .background_gradient(cmap="Reds_r", subset=["Gap (pp)"]))


# =========================================================================== #
# PAGE 3 — BUDGET VARIANCE                                                     #
# =========================================================================== #
def page_variance(model: D.Model, f: dict) -> None:
    var = filter_monthly(model.variance, f)
    page_header("Budget Variance",
                "Actual vs plan by country, category and month — with a price/volume bridge.")
    asof_badge()
    if f["segments"]:
        st.caption("ℹ️ Budget is set at Country × Category × Month (no segment), "
                   "so the Segment slicer does not apply on this page.")
    st.write("")

    vs = M.variance_summary(var)
    cards = [
        T.kpi_card("Actual Revenue", T.fmt_eur_compact(vs["actual"]), accent=T.TEAL),
        T.kpi_card("Budget Revenue", T.fmt_eur_compact(vs["budget"]), accent=T.AMBER),
        T.kpi_card("Total Variance", T.fmt_signed_eur(vs["variance"]),
                   T.fmt_signed_pct(vs["variance_pct"]), T.variance_color(vs["variance"]),
                   T.variance_color(vs["variance"])),
        T.kpi_card("Price / Volume", "Bridge",
                   f"Price {T.fmt_signed_eur(vs['price_variance'])} · "
                   f"Vol {T.fmt_signed_eur(vs['volume_variance'])}", T.MUTED, T.MUTED),
    ]
    st.markdown(T.kpi_row(cards), unsafe_allow_html=True)
    st.write("")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-title">Budget → Actual waterfall (by category)</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(_chart_waterfall(var), use_container_width=True)
    with c2:
        st.markdown('<div class="section-title">Quarterly variance by country</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(_chart_quarterly_variance(var), use_container_width=True)

    st.markdown('<div class="section-title">Variance matrix — Country × Category</div>',
                unsafe_allow_html=True)
    st.caption("Actual / Budget / Variance € / Variance %. Green favourable, red unfavourable.")
    st.dataframe(_matrix_variance(var), use_container_width=True)


def _chart_waterfall(var: pd.DataFrame) -> go.Figure:
    budget_total = float(var["Budget_Revenue"].sum())
    g = (var.groupby("Category", as_index=False)["Rev_Variance"].sum())
    g = g.reindex([i for c in D.CATEGORIES for i in g.index[g["Category"] == c]])
    measures = ["absolute"] + ["relative"] * len(g) + ["total"]
    x = ["Budget"] + list(g["Category"]) + ["Actual"]
    y = [budget_total] + list(g["Rev_Variance"]) + [budget_total + g["Rev_Variance"].sum()]
    fig = go.Figure(go.Waterfall(
        x=x, y=y, measure=measures,
        increasing=dict(marker_color=T.GREEN), decreasing=dict(marker_color=T.RED),
        totals=dict(marker_color=T.TEAL), connector=dict(line=dict(color=T.GRID)),
    ))
    fig.update_layout(yaxis_title="Revenue (€)", showlegend=False)
    return T.style_fig(fig, 380)


def _chart_quarterly_variance(var: pd.DataFrame) -> go.Figure:
    var = var.copy()
    var["YQ"] = var["Year"].astype(str) + " " + var["Quarter"]
    g = var.groupby(["YQ", "Country"], as_index=False)["Rev_Variance"].sum()
    fig = go.Figure()
    for i, country in enumerate(D.COUNTRIES):
        sub = g[g["Country"] == country].sort_values("YQ")
        if sub.empty:
            continue
        fig.add_bar(x=sub["YQ"], y=sub["Rev_Variance"], name=country,
                    marker_color=T.CATEGORICAL[i])
    fig.add_hline(y=0, line=dict(color=T.MUTED, width=1))
    fig.update_layout(barmode="group", yaxis_title="Variance (€)", xaxis_title=None)
    fig.update_xaxes(tickangle=-45)
    return T.style_fig(fig, 380)


def _matrix_variance(var: pd.DataFrame):
    g = (var.groupby(["Country", "Category"], as_index=False)
         .agg(Actual=("Revenue", "sum"), Budget=("Budget_Revenue", "sum")))
    g["Variance €"] = g["Actual"] - g["Budget"]
    g["Variance %"] = g["Variance €"] / g["Budget"] * 100
    g = g.sort_values(["Country", "Category"])
    return (g.style
            .format({"Actual": "€{:,.0f}", "Budget": "€{:,.0f}",
                     "Variance €": "{:+,.0f}", "Variance %": "{:+.1f}%"})
            .background_gradient(cmap="RdYlGn", subset=["Variance €", "Variance %"]))


# =========================================================================== #
# PAGE 4 — FORECAST & WHAT-IF                                                  #
# =========================================================================== #
def page_forecast(model: D.Model, f: dict) -> None:
    tx = filter_tx(model.transactions, f)
    page_header("Forecast & What-If",
                "Project Q1 2025, simulate channel scenarios and back-solve the 2025 target.")
    asof_badge()
    st.write("")

    growth = st.slider("Annual revenue growth assumption", min_value=-10.0, max_value=20.0,
                       value=round(M.yoy_growth(tx)["pct"], 1), step=0.5, format="%.1f%%",
                       help="Applied to the matching 2024 month (seasonal-naive forecast).")

    fc = M.forecast_q1_2025(tx, growth)
    central = float(fc["Central"].sum())
    optimistic = float(fc["Optimistic"].sum())
    pessimistic = float(fc["Pessimistic"].sum())

    cards = [
        T.kpi_card("Q1 2025 — Central", T.fmt_eur_compact(central),
                   f"at {T.fmt_signed_pct(growth)} growth", T.MUTED, T.TEAL),
        T.kpi_card("Q1 2025 — Optimistic", T.fmt_eur_compact(optimistic),
                   "at +20.0%", T.GREEN, T.GREEN),
        T.kpi_card("Q1 2025 — Pessimistic", T.fmt_eur_compact(pessimistic),
                   "at −10.0%", T.RED, T.RED),
    ]
    st.markdown(T.kpi_row(cards), unsafe_allow_html=True)
    st.write("")

    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown('<div class="section-title">Jan–Mar 2025 revenue projection</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(_chart_forecast(tx, fc), use_container_width=True)
    with c2:
        st.markdown('<div class="section-title">Path to €2.5M in 2025</div>',
                    unsafe_allow_html=True)
        req = M.required_growth_for_target(tx, 2_500_000.0)
        st.markdown(T.kpi_row([
            T.kpi_card("Required growth", T.fmt_signed_pct(req["required_growth_pct"]),
                       f"2024 base {T.fmt_eur_compact(req['base'])}",
                       T.variance_color(req["required_growth_pct"]
                                        - growth), T.AMBER),
        ]), unsafe_allow_html=True)
        gap = req["required_growth_pct"] - growth
        verdict = ("on track ✓" if gap <= 0 else f"{gap:.1f} pp short of plan")
        st.markdown(
            f"To hit **€2.5M** in 2025 from a 2024 base of "
            f"**{T.fmt_eur(req['base'])}**, EuroFoods needs annual revenue growth of "
            f"**{T.fmt_signed_pct(req['required_growth_pct'])}**. "
            f"At the current slider assumption of {T.fmt_signed_pct(growth)}, the group is "
            f"**{verdict}**."
        )

    st.markdown('<div class="section-title">Channel scenario simulator</div>',
                unsafe_allow_html=True)
    st.caption("Adjust each segment's growth; the net revenue impact is computed on the 2024 base. "
               "Defaults reproduce the brief's *Online +20% / Convenience −10%* scenario.")

    defaults = {"Hypermarket": 0.0, "Supermarket": 0.0, "Convenience": -10.0, "Online": 20.0}
    sc1, sc2, sc3, sc4 = st.columns(4)
    adj = {}
    for col, seg in zip((sc1, sc2, sc3, sc4), D.SEGMENTS):
        with col:
            adj[seg] = st.slider(seg, -30.0, 30.0, defaults[seg], 1.0, format="%.0f%%",
                                 key=f"adj_{seg}")

    table = M.segment_scenario_table(tx, adj)
    base_total = float(table["Base"].sum())
    scen_total = float(table["Scenario"].sum())
    net = scen_total - base_total

    c3, c4 = st.columns([1, 1.2])
    with c3:
        st.markdown(T.kpi_row([
            T.kpi_card("Net revenue impact", T.fmt_signed_eur(net),
                       T.fmt_signed_pct(net / base_total * 100 if base_total else 0),
                       T.variance_color(net), T.variance_color(net)),
        ]), unsafe_allow_html=True)
        st.markdown("")
        # brief headline scenario
        sc = M.scenario_impact(tx)
        st.info(
            f"**Brief scenario** (Online +20%, Convenience −10%): "
            f"Online {T.fmt_signed_eur(sc['online_delta'])}, "
            f"Convenience {T.fmt_signed_eur(sc['convenience_delta'])} → "
            f"net **{T.fmt_signed_eur(sc['net_delta'])}** "
            f"({T.fmt_signed_pct(sc['net_delta']/sc['total_base']*100)} of segment revenue)."
        )
    with c4:
        st.plotly_chart(_chart_scenario(table), use_container_width=True)


def _chart_forecast(tx: pd.DataFrame, fc: pd.DataFrame) -> go.Figure:
    hist = (tx[tx["Year"] == 2024].groupby("Month", as_index=False)["Revenue"].sum())
    fig = go.Figure()
    fig.add_scatter(x=[D.MONTH_NAMES[m - 1] + " '24" for m in hist["Month"]],
                    y=hist["Revenue"], mode="lines", name="2024 actual",
                    line=dict(color=T.MUTED, width=2))
    fig.add_scatter(x=fc["Label"], y=fc["Central"], mode="lines+markers", name="Central",
                    line=dict(color=T.TEAL, width=3),
                    text=[T.fmt_eur_compact(v) for v in fc["Central"]], textposition="top center")
    fig.add_scatter(x=fc["Label"], y=fc["Optimistic"], mode="lines", name="Optimistic",
                    line=dict(color=T.GREEN, width=1.5, dash="dot"))
    fig.add_scatter(x=fc["Label"], y=fc["Pessimistic"], mode="lines", name="Pessimistic",
                    line=dict(color=T.RED, width=1.5, dash="dot"))
    fig.update_layout(yaxis_title="Revenue (€)", xaxis_title=None)
    fig.update_xaxes(tickangle=-45)
    return T.style_fig(fig, 380)


def _chart_scenario(table: pd.DataFrame) -> go.Figure:
    t = table.set_index("Segment").reindex(D.SEGMENTS).reset_index()
    fig = go.Figure()
    fig.add_bar(x=t["Segment"], y=t["Base"], name="Base (2024)", marker_color=T.AMBER)
    fig.add_bar(x=t["Segment"], y=t["Scenario"], name="Scenario", marker_color=T.TEAL)
    fig.update_layout(barmode="group", yaxis_title="Revenue (€)", xaxis_title=None)
    return T.style_fig(fig, 360)


# =========================================================================== #
# SIDEBAR & ROUTER                                                            #
# =========================================================================== #
def sidebar_filters(model: D.Model) -> tuple[str, dict]:
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">🥨 EuroFoods S.A.</div>'
                    '<div class="sidebar-tag">FP&A Performance Dashboard</div>',
                    unsafe_allow_html=True)
        page = st.radio("Page", ["Executive Summary", "Category Deep-Dive",
                                 "Budget Variance", "Forecast & What-If"], label_visibility="collapsed")
        st.markdown("---")
        st.markdown("**Global filters**")
        tx = model.transactions
        f = {
            "countries": st.multiselect("Country", D.COUNTRIES),
            "years": st.multiselect("Year", sorted(tx["Year"].unique())),
            "quarters": st.multiselect("Quarter", ["Q1", "Q2", "Q3", "Q4"]),
            "categories": st.multiselect("Category", D.CATEGORIES),
            "segments": st.multiselect("Segment", D.SEGMENTS),
        }
        st.markdown("---")
        st.caption("Revenue is reported in **EUR**. FX rates are reference only — "
                   "the fact table is already in EUR (see `data_profile.md`).")
    return page, f


def main() -> None:
    T.register_template()
    T.inject_css(st)
    model = load_model()
    page, f = sidebar_filters(model)

    if page == "Executive Summary":
        page_executive(model, f)
    elif page == "Category Deep-Dive":
        page_category(model, f)
    elif page == "Budget Variance":
        page_variance(model, f)
    else:
        page_forecast(model, f)


if __name__ == "__main__":
    main()
