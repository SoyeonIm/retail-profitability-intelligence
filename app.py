
"""MarginIQ — Commercial Performance Analytics dashboard."""

import pandas as pd
import streamlit as st

from src.reporting_data import (
    load_reporting_data,
    load_category_reporting_data,
)
from src.dashboard_metrics import (
    calculate_monthly_kpis,
    calculate_store_category_metrics,
    prepare_store_margin_heatmap,
    calculate_heatmap_performance_snapshot
)
from src.dashboard_theme import dashboard_css
from src.dashboard_charts import (
    regional_benchmark_chart,
    monthly_financial_chart,
    monthly_growth_chart,
    monthly_margin_chart,
    store_performance_scatter_chart,
    investigation_priority_chart,
    store_margin_trend_chart,
    store_category_mix_chart,
    store_category_margin_chart,
    store_margin_heatmap_chart
)


# ---------------------------------------------------------
# 1. PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="MarginIQ | Commercial Performance Analytics",
    page_icon="📊",
    layout="wide",
)

st.markdown(dashboard_css(), unsafe_allow_html=True)


# ---------------------------------------------------------
# 2. LOAD VALIDATED REPORTING DATA
# ---------------------------------------------------------

@st.cache_data(show_spinner="Loading validated reporting data...")
def get_data():
    return load_reporting_data()


data = get_data()

store = data["store"]
region = data["region"]

monthly = calculate_monthly_kpis(store)


# ---------------------------------------------------------
# 3. DASHBOARD HEADER
# ---------------------------------------------------------

st.title("MarginIQ")

st.subheader("Commercial Performance Analytics")

st.caption(
    "Synthetic New Zealand retail data | "
    "Validated DuckDB reporting layer"
)


# ---------------------------------------------------------
# 4. SIDEBAR FILTERS
# ---------------------------------------------------------

st.sidebar.header("Filters")

months = sorted(
    pd.to_datetime(store["month"]).dt.date.unique()
)

selected_month = st.sidebar.selectbox(
    "Reporting Month",
    options=months,
    index=len(months) - 1,
    format_func=lambda value: value.strftime("%B %Y"),
)


# Filter both datasets to the selected month.

store_month = store[
    pd.to_datetime(store["month"]).dt.date == selected_month
].copy()

region_month = region[
    pd.to_datetime(region["month"]).dt.date == selected_month
].copy()


# ---------------------------------------------------------
# 5. MONTHLY KPI CALCULATIONS
# ---------------------------------------------------------

selected_kpi = monthly[
    pd.to_datetime(monthly["month"]).dt.date == selected_month
].iloc[0]

total_sales_nzd = selected_kpi["net_sales_nzd"]
total_gp_nzd = selected_kpi["gross_profit_nzd"]
gp_margin_pct = selected_kpi["gp_margin_pct"]
store_count = int(selected_kpi["store_count"])

sales_mom_pct = selected_kpi["sales_mom_pct"]
gp_mom_pct = selected_kpi["gp_mom_pct"]
margin_mom_pp = selected_kpi["margin_mom_pp"]
stores_mom_change = selected_kpi["stores_mom_change"]


def format_delta(value, unit):
    """Format monthly changes without inventing comparisons."""
    if pd.isna(value):
        return None

    return f"{value:+.2f}{unit}"


def format_nzd_compact(value):
    """Display NZD amounts in thousands without changing source data."""
    return f"NZ${value / 1000:,.1f}K"


# ---------------------------------------------------------
# 6. EXECUTIVE OVERVIEW
# ---------------------------------------------------------

st.subheader("Executive Overview")

col1, col2, col3, col4 = st.columns(4)


# KPI 1: Net Sales

col1.metric(
    label="Net Sales",
    value=format_nzd_compact(total_sales_nzd),
    delta=format_delta(sales_mom_pct, "% MoM"),
    help=f"Exact Net Sales: NZ${total_sales_nzd:,.2f}",
)


# KPI 2: Gross Profit

col2.metric(
    label="Gross Profit",
    value=format_nzd_compact(total_gp_nzd),
    delta=format_delta(gp_mom_pct, "% MoM"),
    help=f"Exact Gross Profit: NZ${total_gp_nzd:,.2f}",
)


# KPI 3: Gross Profit Margin

col3.metric(
    label="GP Margin",
    value=f"{gp_margin_pct:.2f}%",
    delta=format_delta(margin_mom_pp, " pp MoM"),
)


# KPI 4: Active Stores

col4.metric(
    label="Active Stores",
    value=f"{store_count}",
    delta=(
        None
        if pd.isna(stores_mom_change)
        else f"{int(stores_mom_change):+d} MoM"
    ),
)



# ---------------------------------------------------------
# 7. MONTHLY PROFITABILITY TRENDS
# ---------------------------------------------------------

st.subheader("Monthly Profitability Trends")

# Include historical months only up to the selected month.
trend_data = monthly[
    pd.to_datetime(monthly["month"]).dt.date <= selected_month
].copy()

# Main financial performance chart
financial_fig = monthly_financial_chart(trend_data)

st.plotly_chart(
    financial_fig,
    width="stretch",
    config={"displayModeBar": False},
)

# Two analytical charts displayed side by side.
growth_col, margin_col = st.columns(2)

with growth_col:
    growth_fig = monthly_growth_chart(trend_data)
    st.plotly_chart(
        growth_fig,
        width="stretch",
        config={"displayModeBar": False},
    )

with margin_col:
    margin_fig = monthly_margin_chart(trend_data)
    st.plotly_chart(
        margin_fig,
        width="stretch",
        config={"displayModeBar": False},
    )

st.caption(
    "Monthly GP Margin = Total Gross Profit / Total Net Sales. "
    "MoM growth is calculated against the preceding month. "
    "GP Margin is sales-weighted, not an average of store margins."
)



# ---------------------------------------------------------
# 8. REGIONAL PROFITABILITY TABLE
# ---------------------------------------------------------

st.divider()

st.subheader("Regional Profitability")

regional_display = region_month[
    [
        "region",
        "store_count",
        "net_sales_cents",
        "gross_profit_cents",
        "regional_gp_margin_pct",
        "margin_variance_pp",
    ]
].copy()


# Convert integer cents to NZD for display only.

regional_display["Net Sales (NZD)"] = (
    regional_display["net_sales_cents"] / 100
)

regional_display["Gross Profit (NZD)"] = (
    regional_display["gross_profit_cents"] / 100
)


regional_display = regional_display.rename(
    columns={
        "region": "Region",
        "store_count": "Stores",
        "regional_gp_margin_pct": "GP Margin (%)",
        "margin_variance_pp": "vs NZ Benchmark (pp)",
    }
)


regional_display = regional_display[
    [
        "Region",
        "Stores",
        "Net Sales (NZD)",
        "Gross Profit (NZD)",
        "GP Margin (%)",
        "vs NZ Benchmark (pp)",
    ]
].sort_values(
    "Net Sales (NZD)",
    ascending=False,
)


st.dataframe(
    regional_display,
    hide_index=True,
    width="stretch",
)


# ---------------------------------------------------------
# 9. REGIONAL BENCHMARK ANALYSIS
# ---------------------------------------------------------

st.subheader("Regional Benchmark Analysis")

regional_fig = regional_benchmark_chart(
    region_month
)

st.plotly_chart(
    regional_fig,
    width="stretch",
    config={"displayModeBar": False},
)

st.caption(
    "Variance is measured in percentage points against "
    "the sales-weighted New Zealand GP margin benchmark. "
    "Positive values indicate above-benchmark performance."
)


# ---------------------------------------------------------
# 10. METHODOLOGY
# ---------------------------------------------------------

st.caption(
    "GP Margin = Gross Profit / Net Sales. "
    "All financial values are derived from validated SQL models."
)


# ---------------------------------------------------------
# 11. STORE PERFORMANCE ANALYSIS
# ---------------------------------------------------------

st.divider()
st.subheader("Store Performance Analysis")

st.caption(
    "Explore store-level profitability against the "
    "sales-weighted NZ benchmark."
)

available_regions = sorted(store_month["region"].unique())

selected_regions = st.multiselect(
    "Filter by Region",
    options=available_regions,
    default=available_regions,
)

filtered_stores = store_month[
    store_month["region"].isin(selected_regions)
].copy()

if filtered_stores.empty:
    st.info("Select at least one region to display stores.")
else:
    scatter_fig = store_performance_scatter_chart(
        filtered_stores
    )

    st.plotly_chart(
        scatter_fig,
        width="stretch",
        config={"displayModeBar": False},
    )

    st.caption(
        "Each point represents one store in the selected month. "
        "The horizontal line shows the national sales-weighted "
        "GP margin benchmark. Below-benchmark performance "
        "indicates a potential investigation opportunity, "
        "not a confirmed operational issue."
    )

# ---------------------------------------------------------
# 12. INVESTIGATION PRIORITIES
# ---------------------------------------------------------

st.divider()
st.subheader("Investigation Priorities")

st.caption(
    "Identify stores with the largest hypothetical GP gap "
    "relative to the national sales-weighted benchmark."
)

# Use the full national store population for the selected month.
# The national investigation rank must not be recalculated
# after filtering by region.

priority_data = store_month.copy()

high_priority_count = int(
    (priority_data["investigation_priority"] == "High").sum()
)

below_benchmark_count = int(
    (priority_data["store_vs_nz_gap_pp"] < 0).sum()
)

positive_gp_gap_nzd = float(
    priority_data["gp_shortfall_vs_nz_nzd"]
    .clip(lower=0)
    .sum()
)

priority_col1, priority_col2, priority_col3 = st.columns(3)

priority_col1.metric(
    "High Priority Stores",
    f"{high_priority_count}",
)

priority_col2.metric(
    "Potential GP Gap",
    f"NZ${positive_gp_gap_nzd:,.2f}",
    help=(
        "Sum of positive hypothetical GP shortfalls "
        "against the national benchmark. "
        "This is not an actual financial loss."
    ),
)

priority_col3.metric(
    "Below NZ Benchmark",
    f"{below_benchmark_count}",
)

# Show the ten largest positive hypothetical GP gaps.
if (priority_data["gp_shortfall_vs_nz_nzd"] > 0).any():
    priority_fig = investigation_priority_chart(priority_data)

    st.plotly_chart(
        priority_fig,
        width="stretch",
        config={"displayModeBar": False},
    )
else:
    st.info(
        "No stores have a positive hypothetical GP gap "
        "for the selected reporting month."
    )

st.caption(
    "The national investigation rank is based on hypothetical "
    "GP shortfall, while High / Medium / Monitor is a separate "
    "rule-based classification using persistence and regional "
    "performance signals. Potential GP gaps are benchmark "
    "scenarios, not confirmed losses or recoverable savings."
)


# ---------------------------------------------------------
# 13. STORE INVESTIGATION DETAIL
# ---------------------------------------------------------

st.divider()
st.subheader("Store Investigation Detail")

st.caption(
    "Examine individual store performance against "
    "national and regional profitability benchmarks."
)

# Store selection is independent of the scatter plot's
# regional filter.
store_options = sorted(store_month["store_id"].unique())

selected_store_id = st.selectbox(
    "Select Store",
    options=store_options,
    index=store_options.index("S044")
    if "S044" in store_options
    else 0,
    key="investigation_store",
)

selected_store_data = store_month.loc[
    store_month["store_id"] == selected_store_id
]

if len(selected_store_data) != 1:
    st.error(
        "Expected exactly one reporting row "
        "for the selected store and month."
    )
    st.stop()

selected_store = selected_store_data.iloc[0]

store_sales_nzd = selected_store["net_sales_cents"] / 100
store_gp_nzd = selected_store["gross_profit_cents"] / 100

store_margin_pct = float(selected_store["gp_margin_pct"])
store_nz_gap_pp = float(selected_store["store_vs_nz_gap_pp"])
store_region_gap_pp = float(
    selected_store["store_vs_region_gap_pp"]
)

st.caption(
    f"Region: {selected_store['region']} | "
    f"Reporting Month: {selected_month:%B %Y}"
)

detail_col1, detail_col2, detail_col3, detail_col4 = (
    st.columns(4)
)

detail_col1.metric(
    "Net Sales",
    f"NZ${store_sales_nzd:,.2f}",
)

detail_col2.metric(
    "Gross Profit",
    f"NZ${store_gp_nzd:,.2f}",
)

detail_col3.metric(
    "GP Margin",
    f"{store_margin_pct:.2f}%",
)

detail_col4.metric(
    "vs NZ Benchmark",
    f"{store_nz_gap_pp:+.2f} pp",
)

st.caption(
    f"Regional benchmark variance: "
    f"{store_region_gap_pp:+.2f} percentage points. "
    "Benchmark differences are diagnostic signals, "
    "not confirmed causes of underperformance."
)


# ---------------------------------------------------------
# 14. STORE MONTHLY PROFITABILITY TREND
# ---------------------------------------------------------

st.markdown("#### Monthly Profitability Trend")

# Use the complete store history, but exclude months
# after the selected reporting month.
store_history = store.loc[
    (store["store_id"] == selected_store_id)
    & (
        pd.to_datetime(store["month"]).dt.date
        <= selected_month
    )
].copy()

if store_history.empty:
    st.warning(
        "No historical reporting data is available "
        "for the selected store."
    )
else:
    trend_fig = store_margin_trend_chart(store_history)

    st.plotly_chart(
        trend_fig,
        width="stretch",
        config={"displayModeBar": False},
    )

    st.caption(
        "Monthly store GP margin compared with the "
        "sales-weighted regional and NZ benchmarks. "
        "Historical trends end at the selected reporting month."
    )


# ---------------------------------------------------------
# 15. STORE CATEGORY PROFITABILITY
# ---------------------------------------------------------

st.markdown("#### Category Profitability")

@st.cache_data(show_spinner="Loading category profitability...")
def get_category_data():
    return load_category_reporting_data()


category_data = get_category_data()

category_month = category_data.loc[
    (category_data["store_id"] == selected_store_id)
    & (
        pd.to_datetime(category_data["month"]).dt.date
        == selected_month
    )
].copy()

if category_month.empty:
    st.warning(
        "No category profitability data is available "
        "for the selected store and reporting month."
    )
else:
    category_metrics = calculate_store_category_metrics(
        category_month
    )

    # Reconcile category totals to the selected store.
    if (
        category_metrics["net_sales_cents"].sum()
        != selected_store["net_sales_cents"]
        or category_metrics["gross_profit_cents"].sum()
        != selected_store["gross_profit_cents"]
    ):
        st.error(
            "Category totals do not reconcile to store reporting."
        )
        st.stop()

    category_col1, category_col2 = st.columns(2)

    with category_col1:
        st.plotly_chart(
            store_category_mix_chart(category_metrics),
            width="stretch",
            config={"displayModeBar": False},
        )

    with category_col2:
        st.plotly_chart(
            store_category_margin_chart(category_metrics),
            width="stretch",
            config={"displayModeBar": False},
        )

    st.caption(
        "Sales Mix is each category's share of store net sales. "
        "GP Contribution is each category's share of store gross "
        "profit. Category margins are calculated from validated "
        "net sales and gross profit in integer NZD cents."
    )


# ---------------------------------------------------------
# 16. STORE PROFITABILITY HEATMAP
# ---------------------------------------------------------

st.divider()
st.subheader("Store Profitability Heatmap")

st.caption(
    "Explore monthly store GP margin differences against "
    "the NZ sales-weighted benchmark."
)

heatmap_regions = sorted(store["region"].unique())

selected_heatmap_regions = st.multiselect(
    "Filter Heatmap by Region",
    options=heatmap_regions,
    default=heatmap_regions,
    key="heatmap_region_filter",
)


heatmap_col1, heatmap_col2 = st.columns(2)

with heatmap_col1:
    heatmap_period = st.selectbox(
        "Analysis Period",
        options=[6, 12, 21],
        index=0,
        format_func=lambda value: (
            f"Last {value} Months"
            if value < 21
            else "All Available Months"
        ),
        key="heatmap_period",
    )

with heatmap_col2:
    heatmap_store_count = st.selectbox(
        "Number of Stores",
        options=[10, 20, 30, 60],
        index=1,
      format_func=lambda value: (
    f"{value} Lowest-Ranked Stores"
    if value < 60
    else "All Stores"
),
        key="heatmap_store_count",
    )

heatmap_data = prepare_store_margin_heatmap(
    store,
    end_month=selected_month,
)

heatmap_data = heatmap_data.loc[
    heatmap_data["region"].isin(selected_heatmap_regions)
].copy()

if not heatmap_data.empty:
    available_months = sorted(
        heatmap_data["month"].unique()
    )

    recent_months = available_months[-heatmap_period:]

    heatmap_data = heatmap_data.loc[
        heatmap_data["month"].isin(recent_months)
    ].copy()

    # Rank stores by sales-weighted GP margin gap
    # across the selected analysis period.
    store_rank = (
        heatmap_data.groupby("store_id")
        .agg(
            total_sales=("net_sales_cents", "sum"),
            total_gp=("gross_profit_cents", "sum"),
            benchmark_gp=(
                "nz_gp_margin_pct",
                lambda values: 0.0,
            ),
        )
    )

    # Calculate each store's period-weighted benchmark
    # using its own monthly sales as weights.
    weighted_benchmark = (
        heatmap_data.assign(
            weighted_benchmark_gp=(
                heatmap_data["net_sales_cents"]
                * heatmap_data["nz_gp_margin_pct"]
            )
        )
        .groupby("store_id")[
            "weighted_benchmark_gp"
        ]
        .sum()
    )

    store_rank["benchmark_gp"] = weighted_benchmark

    store_rank["period_gap_pp"] = (
        100
        * store_rank["total_gp"]
        / store_rank["total_sales"]
        - store_rank["benchmark_gp"]
        / store_rank["total_sales"]
    )

    store_rank = store_rank.sort_values(
        ["period_gap_pp", "total_sales"],
        ascending=[True, False],
    )

    selected_stores = store_rank.head(
        heatmap_store_count
    ).index

    heatmap_data = heatmap_data.loc[
        heatmap_data["store_id"].isin(selected_stores)
    ].copy()


# ---------------------------------------------------------
# HEATMAP PERFORMANCE SUMMARY
# ---------------------------------------------------------


if not heatmap_data.empty:
    snapshot = calculate_heatmap_performance_snapshot(
        heatmap_data
    )

    stores_below_benchmark = snapshot[
        "stores_below_benchmark"
    ]

    persistent_underperformers = snapshot[
        "persistent_underperformers"
    ]

    potential_gp_shortfall_nzd = snapshot[
        "potential_gp_shortfall_nzd"
    ]

    st.markdown("#### Performance Snapshot")

    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

    with kpi_col1:
        st.metric(
            "Stores Below NZ Benchmark",
            f"{stores_below_benchmark:,}",
            help="Number of displayed stores below the NZ benchmark in the latest month.",
        )

    with kpi_col2:
        st.metric(
            "Persistent Underperformers",
            f"{persistent_underperformers:,}",
            help="Displayed stores below the NZ benchmark in every month of the selected period.",
        )

    with kpi_col3:
        st.metric(
            "Potential GP Shortfall",
            f"NZ${potential_gp_shortfall_nzd:,.0f}",
            help=(
                "Hypothetical GP shortfall against the monthly "
                "NZ sales-weighted benchmark, aggregated across "
                "displayed stores and the selected period. "
                "Not an actual loss or guaranteed opportunity."
            ),
        )

    st.caption(
        "Snapshot covers the displayed stores and selected analysis period. "
        "Potential GP shortfall is a hypothetical benchmark comparison, "
        "not a realised financial loss."
    )

if heatmap_data.empty:
    st.info("Select at least one region to display the heatmap.")
else:
    heatmap_fig = store_margin_heatmap_chart(heatmap_data)

    st.plotly_chart(
        heatmap_fig,
        width="stretch",
        config={"displayModeBar": False},
    )


    st.caption(
        "Each cell shows the store's GP margin gap against "
        "the NZ sales-weighted benchmark, in percentage points. "
        "Coral indicates below benchmark, while slate blue "
        "indicates above benchmark. Period Gap is calculated "
        "using sales-weighted margins across the selected months."
    )