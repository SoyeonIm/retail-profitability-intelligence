
"""MarginIQ — Commercial Performance Analytics dashboard."""

import pandas as pd
import streamlit as st

from src.reporting_data import load_reporting_data
from src.dashboard_metrics import calculate_monthly_kpis
from src.dashboard_theme import dashboard_css
from src.dashboard_charts import (
    regional_benchmark_chart,
    monthly_financial_chart,
    monthly_growth_chart,
    monthly_margin_chart,
    store_performance_scatter_chart,
    investigation_priority_chart,
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