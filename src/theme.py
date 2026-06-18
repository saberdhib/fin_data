"""Visual standards for the EuroFoods dashboard.

Central place for the colour palette, number formatting and the custom CSS that
gives the app its agency-grade look. Keeping it here means every page renders
charts and KPI cards consistently.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# --------------------------------------------------------------------------- #
# Palette (mandated by the brief)                                             #
# --------------------------------------------------------------------------- #
TEAL = "#0891B2"      # Actual
AMBER = "#F59E0B"     # Budget
RED = "#EF4444"       # Unfavourable
GREEN = "#10B981"     # Favourable

# Supporting palette for categorical breakdowns (segments, categories, …)
CATEGORICAL = ["#0891B2", "#F59E0B", "#6366F1", "#EC4899", "#10B981", "#64748B"]

INK = "#0F172A"        # primary text
MUTED = "#64748B"      # secondary text
GRID = "#E2E8F0"       # gridlines
SURFACE = "#FFFFFF"
CANVAS = "#F8FAFC"

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"

DATA_AS_OF = "December 2024"


# --------------------------------------------------------------------------- #
# Plotly template                                                             #
# --------------------------------------------------------------------------- #
def register_template() -> None:
    """Register and activate the EuroFoods Plotly template."""
    tmpl = go.layout.Template()
    tmpl.layout = go.Layout(
        font=dict(family=FONT, size=13, color=INK),
        title=dict(font=dict(family=FONT, size=17, color=INK), x=0.01, xanchor="left"),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        colorway=CATEGORICAL,
        margin=dict(l=60, r=30, t=60, b=50),
        xaxis=dict(showgrid=False, linecolor=GRID, zeroline=False, color=MUTED),
        yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False, color=MUTED),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=12, color=MUTED)),
        hoverlabel=dict(font=dict(family=FONT, size=12)),
    )
    pio.templates["eurofoods"] = tmpl
    pio.templates.default = "plotly_white+eurofoods"


def style_fig(fig: go.Figure, height: int = 380) -> go.Figure:
    """Apply common layout polish to a figure."""
    fig.update_layout(template="plotly_white+eurofoods", height=height,
                      title_x=0.0, margin=dict(l=60, r=30, t=60, b=50))
    return fig


# --------------------------------------------------------------------------- #
# Number formatting                                                           #
# --------------------------------------------------------------------------- #
def fmt_eur(value: float, decimals: int = 0) -> str:
    """€#,##0 with thin-space thousands grouping (e.g. €1,234,567)."""
    if value is None:
        return "—"
    return f"€{value:,.{decimals}f}"


def fmt_eur_compact(value: float) -> str:
    """Compact EUR for cards: €1.23M / €456K."""
    if value is None:
        return "—"
    a = abs(value)
    if a >= 1_000_000:
        return f"€{value/1_000_000:,.2f}M"
    if a >= 1_000:
        return f"€{value/1_000:,.0f}K"
    return f"€{value:,.0f}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    """0.0% format (value already in percent units, e.g. 38.7 -> '38.7%')."""
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}%"


def fmt_signed_eur(value: float) -> str:
    """Signed EUR variance, e.g. +€12,345 / −€9,876 (true minus glyph)."""
    if value is None:
        return "—"
    sign = "+" if value >= 0 else "−"
    return f"{sign}€{abs(value):,.0f}"


def fmt_signed_pct(value: float, decimals: int = 1) -> str:
    """Signed percentage variance, e.g. +5.4% / −4.7%."""
    if value is None:
        return "—"
    sign = "+" if value >= 0 else "−"
    return f"{sign}{abs(value):,.{decimals}f}%"


def variance_color(value: float) -> str:
    """Green when favourable (>=0), red when unfavourable."""
    return GREEN if value >= 0 else RED


# --------------------------------------------------------------------------- #
# Custom CSS                                                                  #
# --------------------------------------------------------------------------- #
def inject_css(st) -> None:
    """Inject the global stylesheet (KPI cards, typography, spacing)."""
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }
            .main .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1320px; }
            #MainMenu, footer { visibility: hidden; }

            /* ---- Page header ---- */
            .page-title { font-size: 1.9rem; font-weight: 800; color: #0F172A; margin: 0 0 .15rem 0; letter-spacing: -.02em; }
            .page-sub   { font-size: .95rem; color: #64748B; margin: 0 0 1.4rem 0; }
            .section-title { font-size: 1.1rem; font-weight: 700; color: #0F172A; margin: 1.6rem 0 .4rem 0; }

            /* ---- KPI cards ---- */
            .kpi-row { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: .5rem; }
            .kpi-card {
                flex: 1; min-width: 180px; background: #FFFFFF; border: 1px solid #E2E8F0;
                border-radius: 16px; padding: 1.15rem 1.3rem;
                box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 8px 24px -16px rgba(15,23,42,.18);
            }
            .kpi-label { font-size: .72rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #64748B; margin-bottom: .35rem; }
            .kpi-value { font-size: 1.85rem; font-weight: 800; color: #0F172A; line-height: 1.1; letter-spacing: -.02em; }
            .kpi-delta { font-size: .85rem; font-weight: 600; margin-top: .35rem; }
            .kpi-accent { height: 4px; border-radius: 4px; margin-top: .9rem; }

            /* ---- "Data as of" badge ---- */
            .asof-badge {
                display: inline-flex; align-items: center; gap: .45rem;
                background: #ECFEFF; color: #0E7490; border: 1px solid #A5F3FC;
                border-radius: 999px; padding: .3rem .85rem; font-size: .78rem; font-weight: 600;
            }
            .asof-badge .dot { width: 8px; height: 8px; border-radius: 50%; background: #0891B2; }

            /* ---- Tabs ---- */
            .stTabs [data-baseweb="tab-list"] { gap: .25rem; }
            .stTabs [data-baseweb="tab"] { font-weight: 600; font-size: .92rem; padding: .55rem 1rem; }

            /* ---- DataFrames ---- */
            [data-testid="stDataFrame"] { border-radius: 12px; border: 1px solid #E2E8F0; }

            /* ---- Sidebar ---- */
            section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E2E8F0; }
            .sidebar-brand { font-size: 1.2rem; font-weight: 800; color: #0891B2; letter-spacing: -.02em; }
            .sidebar-tag { font-size: .75rem; color: #64748B; margin-bottom: 1rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, delta: str | None = None,
             delta_color: str | None = None, accent: str = TEAL) -> str:
    """Return HTML for a single KPI card."""
    delta_html = ""
    if delta is not None:
        color = delta_color or MUTED
        delta_html = f'<div class="kpi-delta" style="color:{color};">{delta}</div>'
    return (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{delta_html}'
        f'<div class="kpi-accent" style="background:{accent};"></div>'
        f'</div>'
    )


def kpi_row(cards: list[str]) -> str:
    """Wrap a list of kpi_card() HTML strings in a flex row."""
    return f'<div class="kpi-row">{"".join(cards)}</div>'
