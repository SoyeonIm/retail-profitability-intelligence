
"""Shared visual design system for MarginIQ dashboards."""

import plotly.graph_objects as go


# ---------------------------------------------------------
# 1. FINANCIAL ANALYTICS COLOUR PALETTE
# ---------------------------------------------------------

COLORS = {
    "background": "#F8FAFC",
    "surface": "#FFFFFF",
    "surface_alt": "#F1F5F9",
    "border": "#E2E8F0",
    "text": "#17233B",
    "muted": "#64748B",
    "blue": "#2563EB",
    "cyan": "#0891B2",
    "green": "#059669",
    "red": "#DC2626",
    "amber": "#D97706",
    "purple": "#7C3AED",
}


REGION_COLORS = {
    "Auckland": "#2563EB",
    "Bay of Plenty": "#0891B2",
    "Canterbury": "#059669",
    "Otago": "#7C3AED",
    "Waikato": "#D97706",
    "Wellington": "#E11D48",
}


# ---------------------------------------------------------
# 2. SHARED PLOTLY CHART THEME
# ---------------------------------------------------------

def apply_chart_theme(
    fig: go.Figure,
    title: str | None = None,
) -> go.Figure:
    """Apply a consistent light financial analytics theme."""

    fig.update_layout(
        title=title,
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(
            family="Arial, sans-serif",
            color=COLORS["text"],
            size=12,
        ),
        title_font=dict(
            size=16,
            color=COLORS["text"],
        ),
        margin=dict(
            l=30,
            r=30,
            t=55,
            b=35,
        ),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor=COLORS["surface"],
            font_color=COLORS["text"],
            bordercolor=COLORS["border"],
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=COLORS["border"],
        tickfont_color=COLORS["muted"],
    )

    fig.update_yaxes(
        gridcolor=COLORS["border"],
        zeroline=False,
        tickfont_color=COLORS["muted"],
    )

    return fig


# ---------------------------------------------------------
# 3. STREAMLIT DASHBOARD STYLES
# ---------------------------------------------------------

def dashboard_css() -> str:
    """Return the shared light Streamlit dashboard stylesheet."""

    return f"""
    <style>

        .stApp {{
            background-color: {COLORS["background"]};
            color: {COLORS["text"]};
        }}

        [data-testid="stSidebar"] {{
            background-color: {COLORS["surface"]};
            border-right: 1px solid {COLORS["border"]};
        }}

        [data-testid="stMetric"] {{
            background: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 10px;
            padding: 18px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        }}

        [data-testid="stMetricLabel"] {{
            color: {COLORS["muted"]};
        }}

        h1, h2, h3 {{
            color: {COLORS["text"]};
            letter-spacing: -0.025em;
        }}

        h1 {{
            font-weight: 750;
        }}

        div[data-testid="stHorizontalBlock"] {{
            gap: 14px;
        }}

        .block-container {{
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }}

    </style>
    """
