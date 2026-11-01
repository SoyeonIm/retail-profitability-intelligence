
"""Interactive Plotly charts for MarginIQ."""

import pandas as pd
import plotly.graph_objects as go

from src.dashboard_theme import COLORS, apply_chart_theme


def regional_benchmark_chart(
    regional_data: pd.DataFrame,
) -> go.Figure:
    """Compare regional GP margins with the NZ benchmark."""

    required_columns = {
        "region",
        "regional_gp_margin_pct",
        "margin_variance_pp",
        "net_sales_cents",
        "gross_profit_cents",
    }

    missing = required_columns - set(regional_data.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if regional_data.empty:
        raise ValueError("Regional reporting data is empty.")

    if regional_data["region"].duplicated().any():
        raise ValueError("Duplicate regions detected.")

    chart_data = regional_data.sort_values(
        "margin_variance_pp",
        ascending=True,
    ).copy()

    chart_data["Net Sales (NZD)"] = (
        chart_data["net_sales_cents"] / 100
    )

    chart_data["Gross Profit (NZD)"] = (
        chart_data["gross_profit_cents"] / 100
    )

    bar_colors = [
        COLORS["green"] if value >= 0 else COLORS["red"]
        for value in chart_data["margin_variance_pp"]
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=chart_data["margin_variance_pp"],
            y=chart_data["region"],
            orientation="h",
            marker_color=bar_colors,
            customdata=chart_data[
                [
                    "regional_gp_margin_pct",
                    "Net Sales (NZD)",
                    "Gross Profit (NZD)",
                ]
            ].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "vs NZ Benchmark: %{x:+.3f} pp<br>"
                "GP Margin: %{customdata[0]:.2f}%<br>"
                "Net Sales: NZ$%{customdata[1]:,.2f}<br>"
                "Gross Profit: NZ$%{customdata[2]:,.2f}"
                "<extra></extra>"
            ),
            text=[
                f"{value:+.3f} pp"
                for value in chart_data["margin_variance_pp"]
            ],
            textposition="outside",
            cliponaxis=False,
        )
    )

    fig.add_vline(
        x=0,
        line_color=COLORS["muted"],
        line_width=1,
    )

    apply_chart_theme(
        fig,
        title="Regional GP Margin vs NZ Benchmark",
    )

    max_abs_variance = max(
        abs(chart_data["margin_variance_pp"]).max(),
        0.1,
    )

    fig.update_layout(
        height=440,
        showlegend=False,
        margin=dict(l=30, r=75, t=65, b=40),
        bargap=0.35,
    )

    fig.update_xaxes(
        title_text="Variance (percentage points)",
        range=[
            -max_abs_variance * 1.35,
            max_abs_variance * 1.35,
        ],
        ticksuffix=" pp",
        zeroline=False,
    )

    fig.update_yaxes(
        title_text=None,
        automargin=True,
    )

    return fig


def monthly_financial_chart(monthly_data: pd.DataFrame) -> go.Figure:
    """Display monthly net sales and gross profit in NZD."""
    required = {"month", "net_sales_nzd", "gross_profit_nzd"}
    missing = required - set(monthly_data.columns)

    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if monthly_data.empty:
        raise ValueError("Monthly reporting data is empty.")

    chart_data = monthly_data.sort_values("month").copy()
    chart_data["month"] = pd.to_datetime(chart_data["month"])

    fig = go.Figure()

    for column, name, color in [
        ("net_sales_nzd", "Net Sales", COLORS["blue"]),
        ("gross_profit_nzd", "Gross Profit", COLORS["green"]),
    ]:
        fig.add_trace(
            go.Scatter(
                x=chart_data["month"],
                y=chart_data[column],
                name=name,
                mode="lines+markers",
                line=dict(color=color, width=3),
                marker=dict(size=6),
                hovertemplate=(
                    "%{x|%B %Y}<br>"
                    + name
                    + ": NZ$%{y:,.2f}<extra></extra>"
                ),
            )
        )

    apply_chart_theme(fig, "Net Sales & Gross Profit")

    fig.update_layout(
        height=360,
        hovermode="x unified",
        yaxis_title="NZD",
    )
    fig.update_yaxes(tickprefix="NZ$")
    return fig


def monthly_growth_chart(monthly_data: pd.DataFrame) -> go.Figure:
    """Compare monthly sales and gross profit growth rates."""
    required = {"month", "sales_mom_pct", "gp_mom_pct"}
    missing = required - set(monthly_data.columns)

    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if monthly_data.empty:
        raise ValueError("Monthly reporting data is empty.")

    chart_data = monthly_data.sort_values("month").copy()
    chart_data["month"] = pd.to_datetime(chart_data["month"])

    fig = go.Figure()

    for column, name, color in [
        ("sales_mom_pct", "Sales Growth", COLORS["blue"]),
        ("gp_mom_pct", "GP Growth", COLORS["purple"]),
    ]:
        fig.add_trace(
            go.Bar(
                x=chart_data["month"],
                y=chart_data[column],
                name=name,
                marker_color=color,
                hovertemplate=(
                    "%{x|%B %Y}<br>"
                    + name
                    + ": %{y:+.2f}%<extra></extra>"
                ),
            )
        )

    fig.add_hline(y=0, line_color=COLORS["muted"], line_width=1)
    apply_chart_theme(fig, "Month-on-Month Growth")

    fig.update_layout(
        height=360,
        barmode="group",
        yaxis_title="MoM Change (%)",
    )
    fig.update_yaxes(ticksuffix="%")
    return fig


def monthly_margin_chart(monthly_data: pd.DataFrame) -> go.Figure:
    """Show sales-weighted monthly GP margin."""
    required = {"month", "gp_margin_pct"}
    missing = required - set(monthly_data.columns)

    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if monthly_data.empty:
        raise ValueError("Monthly reporting data is empty.")

    chart_data = monthly_data.sort_values("month").copy()
    chart_data["month"] = pd.to_datetime(chart_data["month"])

    fig = go.Figure(
        go.Scatter(
            x=chart_data["month"],
            y=chart_data["gp_margin_pct"],
            mode="lines+markers",
            line=dict(color=COLORS["blue"], width=3),
            marker=dict(size=7),
            fill="tozeroy",
            fillcolor="rgba(37,99,235,0.07)",
            hovertemplate=(
                "%{x|%B %Y}<br>"
                "Weighted GP Margin: %{y:.2f}%"
                "<extra></extra>"
            ),
        )
    )

    apply_chart_theme(fig, "Weighted GP Margin Trend")

    minimum = float(chart_data["gp_margin_pct"].min())
    maximum = float(chart_data["gp_margin_pct"].max())
    padding = max((maximum - minimum) * 0.35, 0.25)

    fig.update_layout(height=360, yaxis_title="GP Margin (%)")
    fig.update_yaxes(
        range=[minimum - padding, maximum + padding],
        ticksuffix="%",
    )
    return fig


def store_performance_scatter_chart(
    store_data: pd.DataFrame,
) -> go.Figure:
    """Compare store sales and GP margin against the NZ benchmark."""

    required_columns = {
        "store_id",
        "region",
        "net_sales_cents",
        "gp_margin_pct",
        "nz_gp_margin_pct",
        "store_vs_nz_gap_pp",
        "investigation_priority",
    }

    missing = required_columns - set(store_data.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if store_data.empty:
        raise ValueError("Store reporting data is empty.")

    if store_data["store_id"].duplicated().any():
        raise ValueError("Duplicate stores detected.")

    if (store_data["net_sales_cents"] <= 0).any():
        raise ValueError("Store net sales must be positive.")

    chart_data = store_data.copy()
    chart_data["net_sales_nzd"] = (
        chart_data["net_sales_cents"] / 100
    )

    benchmark_values = chart_data["nz_gp_margin_pct"]

    if benchmark_values.isna().any():
        raise ValueError("NZ benchmark contains missing values.")

    if (
        benchmark_values.max() - benchmark_values.min()
    ) > 0.00001:
        raise ValueError(
            "Expected one NZ benchmark for the selected month."
        )

    benchmark = float(benchmark_values.iloc[0])

    fig = go.Figure()

    groups = [
        ("Below NZ Benchmark", COLORS["red"], True),
        ("At or Above NZ Benchmark", COLORS["blue"], False),
    ]

    for label, color, below in groups:
        subset = chart_data[
            (chart_data["store_vs_nz_gap_pp"] < 0) == below
        ]

        if subset.empty:
            continue

        fig.add_trace(
            go.Scatter(
                x=subset["net_sales_nzd"],
                y=subset["gp_margin_pct"],
                mode="markers",
                name=label,
                marker=dict(
                    color=color,
                    size=11,
                    opacity=0.8,
                    line=dict(
                        color="white",
                        width=1,
                    ),
                ),
                customdata=subset[
                    [
                        "store_id",
                        "region",
                        "store_vs_nz_gap_pp",
                        "investigation_priority",
                    ]
                ].to_numpy(),
                hovertemplate=(
                    "<b>Store %{customdata[0]}</b><br>"
                    "Region: %{customdata[1]}<br>"
                    "Net Sales: NZ$%{x:,.2f}<br>"
                    "GP Margin: %{y:.2f}%<br>"
                    "vs NZ Benchmark: %{customdata[2]:+.3f} pp<br>"
                    "Investigation Priority: %{customdata[3]}"
                    "<extra></extra>"
                ),
            )
        )

    fig.add_hline(
        y=benchmark,
        line_dash="dash",
        line_color=COLORS["muted"],
        annotation_text=f"NZ Benchmark: {benchmark:.2f}%",
        annotation_position="top left",
    )

    apply_chart_theme(
        fig,
        title="Store Sales vs GP Margin",
    )

    fig.update_layout(
        height=470,
        margin=dict(l=45, r=35, t=85, b=55),
        hovermode="closest",
        legend=dict(
            orientation="h",
            x=0,
            y=1.02,
            xanchor="left",
            yanchor="bottom",
        ),
    )

    fig.update_xaxes(
        title_text="Net Sales (NZD)",
        tickprefix="NZ$",
        tickformat="~s",
    )

    fig.update_yaxes(
        title_text="GP Margin (%)",
        ticksuffix="%",
    )

    return fig

def investigation_priority_chart(
    store_data: pd.DataFrame,
) -> go.Figure:
    """Rank stores by positive hypothetical GP shortfall."""

    required_columns = {
        "store_id",
        "region",
        "gp_shortfall_vs_nz_nzd",
        "store_vs_nz_gap_pp",
        "investigation_priority",
        "national_investigation_rank",
    }

    missing = required_columns - set(store_data.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if store_data.empty:
        raise ValueError("Store reporting data is empty.")

    if store_data["store_id"].duplicated().any():
        raise ValueError("Duplicate stores detected.")

    chart_data = (
        store_data[
            store_data["gp_shortfall_vs_nz_nzd"] > 0
        ]
        .sort_values(
            ["national_investigation_rank", "store_id"]
        )
        .head(10)
        .copy()
    )

    if chart_data.empty:
        raise ValueError(
            "No positive hypothetical GP shortfalls found."
        )

    priority_colors = {
        "High": COLORS["red"],
        "Medium": COLORS["amber"],
        "Monitor": COLORS["blue"],
    }

    chart_data["bar_color"] = chart_data[
        "investigation_priority"
    ].map(priority_colors)

    if chart_data["bar_color"].isna().any():
        raise ValueError("Unknown investigation priority.")

    chart_data = chart_data.sort_values(
        "gp_shortfall_vs_nz_nzd",
        ascending=True,
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=chart_data["gp_shortfall_vs_nz_nzd"],
            y=chart_data["store_id"],
            orientation="h",
            marker_color=chart_data["bar_color"],
            customdata=chart_data[
                [
                    "region",
                    "store_vs_nz_gap_pp",
                    "investigation_priority",
                    "national_investigation_rank",
                ]
            ].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Region: %{customdata[0]}<br>"
                "Potential GP Gap: NZ$%{x:,.2f}<br>"
                "Margin vs NZ: %{customdata[1]:+.3f} pp<br>"
                "Priority: %{customdata[2]}<br>"
                "National Rank: %{customdata[3]}"
                "<extra></extra>"
            ),
            text=[
                f"NZ${value:,.2f}"
                for value in chart_data[
                    "gp_shortfall_vs_nz_nzd"
                ]
            ],
            textposition="outside",
            cliponaxis=False,
        )
    )

    apply_chart_theme(
        fig,
        title="Top 10 Stores by Potential GP Gap",
    )

    fig.update_layout(
        height=480,
        showlegend=False,
        margin=dict(l=40, r=110, t=65, b=45),
        bargap=0.3,
    )

    fig.update_xaxes(
        title_text="Hypothetical GP Gap (NZD)",
        tickprefix="NZ$",
        range=[
            0,
            chart_data["gp_shortfall_vs_nz_nzd"].max()
            * 1.35,
        ],
    )

    fig.update_yaxes(
        title_text=None,
        automargin=True,
    )

    return fig