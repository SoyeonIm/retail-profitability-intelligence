
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


def store_margin_trend_chart(
    store_history: pd.DataFrame,
) -> go.Figure:
    """Compare store margin with NZ and regional benchmarks."""

    required_columns = {
        "store_id",
        "month",
        "gp_margin_pct",
        "nz_gp_margin_pct",
        "region_gp_margin_pct",
    }

    missing = required_columns - set(store_history.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if store_history.empty:
        raise ValueError("Store history is empty.")

    if store_history["store_id"].nunique() != 1:
        raise ValueError("Expected exactly one store.")

    if store_history[list(required_columns)].isna().any().any():
        raise ValueError("Store trend contains missing values.")

    chart_data = store_history.copy()
    chart_data["month"] = pd.to_datetime(chart_data["month"])

    if chart_data["month"].duplicated().any():
        raise ValueError("Duplicate reporting months.")

    chart_data = chart_data.sort_values("month")

    fig = go.Figure()

    series = [
        ("gp_margin_pct", "Selected Store", "#2563EB"),
        ("region_gp_margin_pct", "Regional Benchmark", "#F59E0B"),
        ("nz_gp_margin_pct", "NZ Benchmark", "#64748B"),
    ]

    for column, label, color in series:
        fig.add_trace(
            go.Scatter(
                x=chart_data["month"],
                y=chart_data[column],
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=2.5),
                marker=dict(size=5),
                hovertemplate=(
                    "%{x|%b %Y}"
                    "<br>%{y:.2f}%"
                    "<extra>" + label + "</extra>"
                ),
            )
        )

    fig.update_layout(
        title="Monthly GP Margin vs Benchmarks",
        xaxis_title=None,
        yaxis_title="GP Margin (%)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        height=430,
        margin=dict(l=20, r=20, t=85, b=30),
    )

    fig.update_yaxes(ticksuffix="%")

    return apply_chart_theme(fig)


def store_category_mix_chart(
    category_data: pd.DataFrame,
) -> go.Figure:
    """Compare sales mix and GP contribution by category."""

    required = {
        "category",
        "sales_mix_pct",
        "gp_contribution_pct",
    }

    missing = required - set(category_data.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if category_data.empty:
        raise ValueError("Category data is empty.")

    if category_data["category"].duplicated().any():
        raise ValueError("Duplicate categories.")

    if category_data[
        ["sales_mix_pct", "gp_contribution_pct"]
    ].isna().any().any():
        raise ValueError("Missing category mix values.")

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=category_data["category"],
            y=category_data["sales_mix_pct"],
            name="Sales Mix",
            marker_color="#2563EB",
            hovertemplate="%{x}<br>%{y:.2f}%<extra>Sales Mix</extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            x=category_data["category"],
            y=category_data["gp_contribution_pct"],
            name="GP Contribution",
            marker_color="#F59E0B",
            hovertemplate=(
                "%{x}<br>%{y:.2f}%"
                "<extra>GP Contribution</extra>"
            ),
        )
    )

    fig.update_layout(
        title="Sales Mix vs GP Contribution",
        barmode="group",
        height=430,
        margin=dict(l=20, r=20, t=65, b=45),
        yaxis_title="Share (%)",
    )

    fig.update_yaxes(ticksuffix="%")

    return apply_chart_theme(fig)


def store_category_margin_chart(
    category_data: pd.DataFrame,
) -> go.Figure:
    """Show category GP margins for the selected store-month."""

    required = {"category", "gp_margin_pct"}

    missing = required - set(category_data.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if category_data.empty:
        raise ValueError("Category data is empty.")

    if category_data["category"].duplicated().any():
        raise ValueError("Duplicate categories.")

    if category_data["gp_margin_pct"].isna().any():
        raise ValueError("Missing category GP margin.")

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=category_data["category"],
            y=category_data["gp_margin_pct"],
            marker_color="#2563EB",
            hovertemplate=(
                "%{x}<br>GP Margin: %{y:.2f}%"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title="Category GP Margin",
        height=430,
        margin=dict(l=20, r=20, t=65, b=45),
        yaxis_title="GP Margin (%)",
        showlegend=False,
    )

    fig.update_yaxes(ticksuffix="%")

    return apply_chart_theme(fig)


def store_margin_heatmap_chart(
    heatmap_data: pd.DataFrame,
) -> go.Figure:
    """Show monthly store margin gaps with aligned summary columns."""

    from plotly.subplots import make_subplots

    required = {
        "store_id",
        "region",
        "month",
        "net_sales_cents",
        "gross_profit_cents",
        "gp_margin_pct",
        "nz_gp_margin_pct",
        "store_vs_nz_gap_pp",
    }

    missing = required - set(heatmap_data.columns)
    if missing:
        raise ValueError(f"Missing heatmap columns: {sorted(missing)}")

    if heatmap_data.empty:
        raise ValueError("Heatmap data is empty.")

    if heatmap_data[list(required)].isna().any().any():
        raise ValueError("Heatmap contains missing values.")

    data = heatmap_data.copy()
    data["month"] = pd.to_datetime(data["month"])

    if data.duplicated(["store_id", "month"]).any():
        raise ValueError("Duplicate store-month records.")

    if (data["net_sales_cents"] <= 0).any():
        raise ValueError("Store net sales must be positive.")

    if (
        data.groupby("store_id")["region"].nunique() != 1
    ).any():
        raise ValueError("Each store must belong to one region.")

    data["benchmark_gp_cents"] = (
        data["net_sales_cents"]
        * data["nz_gp_margin_pct"] / 100
    )

    ranking = data.groupby("store_id").agg(
        region=("region", "first"),
        total_sales=("net_sales_cents", "sum"),
        total_gp=("gross_profit_cents", "sum"),
        benchmark_gp=("benchmark_gp_cents", "sum"),
        months_below=(
            "store_vs_nz_gap_pp",
            lambda values: int((values < 0).sum()),
        ),
    )

    ranking["period_gap_pp"] = (
        100
        * (ranking["total_gp"] - ranking["benchmark_gp"])
        / ranking["total_sales"]
    )

    ranking = ranking.sort_values(
        ["period_gap_pp", "total_sales"],
        ascending=[True, False],
    )

    stores = ranking.index.tolist()
    months = sorted(data["month"].unique())

    month_labels = [
        pd.Timestamp(month).strftime("%b %Y")
        for month in months
    ]

    store_labels = [
        f"{store_id}  ·  {ranking.loc[store_id, 'region']}"
        for store_id in stores
    ]

    gap_matrix = data.pivot(
        index="store_id",
        columns="month",
        values="store_vs_nz_gap_pp",
    ).reindex(index=stores, columns=months)

    margin_matrix = data.pivot(
        index="store_id",
        columns="month",
        values="gp_margin_pct",
    ).reindex(index=stores, columns=months)

    benchmark_matrix = data.pivot(
        index="store_id",
        columns="month",
        values="nz_gp_margin_pct",
    ).reindex(index=stores, columns=months)

    customdata = [
        [
            [
                float(margin_matrix.iloc[i, j]),
                float(benchmark_matrix.iloc[i, j]),
            ]
            for j in range(len(months))
        ]
        for i in range(len(stores))
    ]

    show_values = len(months) <= 6

    fig = make_subplots(
        rows=1,
        cols=3,
        shared_yaxes=True,
        horizontal_spacing=0.045,
        column_widths=[0.72, 0.16, 0.12],
        subplot_titles=[
            "MONTHLY GP MARGIN GAP",
            "PERIOD GAP",
            "BELOW NZ",
        ],
    )

    fig.add_trace(
        go.Heatmap(
            x=month_labels,
            y=store_labels,
            z=gap_matrix.to_numpy(),
            customdata=customdata,
            text=(
                [
                    [f"{value:+.1f}" for value in row]
                    for row in gap_matrix.to_numpy()
                ]
                if show_values
                else None
            ),
            texttemplate="%{text}" if show_values else None,
            textfont=dict(size=11),
            colorscale=[
                [0.00, "#B65C65"],
                [0.25, "#E6B3B0"],
                [0.50, "#F7F5F2"],
                [0.75, "#B9CCD9"],
                [1.00, "#527C9B"],
            ],
            zmin=-4,
            zmax=4,
            zmid=0,
            xgap=3,
            ygap=3,
            colorbar=dict(
                title="Gap (pp)",
                thickness=12,
                len=0.7,
                x=1.02,
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Month: %{x}<br>"
                "GP Margin: %{customdata[0]:.2f}%<br>"
                "NZ Benchmark: %{customdata[1]:.2f}%<br>"
                "Gap: %{z:+.2f} pp"
                "<extra></extra>"
            ),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Heatmap(
            x=["Period Gap"],
            y=store_labels,
            z=[
                [float(ranking.loc[s, "period_gap_pp"])]
                for s in stores
            ],
            text=[
                [f"{ranking.loc[s, 'period_gap_pp']:+.2f}"]
                for s in stores
            ],
            texttemplate="%{text}",
            textfont=dict(size=11, color="#334155"),
            colorscale=[
                [0.0, "#F4E5E5"],
                [0.5, "#FFFFFF"],
                [1.0, "#E3ECF3"],
            ],
            zmin=-4,
            zmax=4,
            showscale=False,
            hovertemplate=(
                "%{y}<br>Weighted Period Gap: %{z:+.2f} pp"
                "<extra></extra>"
            ),
        ),
        row=1,
        col=2,
    )

    fig.add_trace(
        go.Heatmap(
            x=["Months Below"],
            y=store_labels,
            z=[
                [int(ranking.loc[s, "months_below"])]
                for s in stores
            ],
            text=[
                [f"{int(ranking.loc[s, 'months_below'])}/{len(months)}"]
                for s in stores
            ],
            texttemplate="%{text}",
            textfont=dict(size=11, color="#334155"),
            colorscale=[
                [0.0, "#FFFFFF"],
                [1.0, "#EDF1F5"],
            ],
            zmin=0,
            zmax=len(months),
            showscale=False,
            hovertemplate=(
                "%{y}<br>Months Below NZ: %{text}"
                "<extra></extra>"
            ),
        ),
        row=1,
        col=3,
    )

    fig.update_layout(
        title=dict(
            text="Store Margin Performance | NZ Benchmark",
            x=0,
            xanchor="left",
        ),
        height=max(560, len(stores) * 31 + 180),
        margin=dict(l=165, r=65, t=115, b=65),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        showlegend=False,
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(
        autorange="reversed",
        showgrid=False,
        tickfont=dict(size=11),
    )

    return apply_chart_theme(fig)
