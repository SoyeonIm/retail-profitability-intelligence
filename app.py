
"""Retail Profitability Intelligence — Streamlit dashboard."""

import pandas as pd
import streamlit as st

from src.reporting_data import load_reporting_data


st.set_page_config(
    page_title="Retail Profitability Intelligence",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(show_spinner="Loading validated reporting data...")
def get_data():
    return load_reporting_data()


data = get_data()
store = data["store"]
region = data["region"]

st.title("Retail Profitability Intelligence")
st.caption(
    "Synthetic New Zealand retail data | "
    "Validated DuckDB reporting layer"
)

# Sidebar filters
st.sidebar.header("Filters")

months = sorted(pd.to_datetime(store["month"]).dt.date.unique())
selected_month = st.sidebar.selectbox(
    "Reporting Month",
    options=months,
    index=len(months) - 1,
    format_func=lambda value: value.strftime("%B %Y"),
)

# Filter both datasets to the same month.
store_month = store[
    pd.to_datetime(store["month"]).dt.date == selected_month
].copy()

region_month = region[
    pd.to_datetime(region["month"]).dt.date == selected_month
].copy()

# Financial metrics: amounts are stored as integer NZD cents.
total_sales_cents = int(store_month["net_sales_cents"].sum())
total_gp_cents = int(store_month["gross_profit_cents"].sum())

total_sales_nzd = total_sales_cents / 100
total_gp_nzd = total_gp_cents / 100

gp_margin_pct = (
    total_gp_cents / total_sales_cents * 100
    if total_sales_cents != 0
    else 0
)

store_count = store_month["store_id"].nunique()

st.subheader("Executive Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Net Sales", f"NZ${total_sales_nzd:,.2f}")
col2.metric("Gross Profit", f"NZ${total_gp_nzd:,.2f}")
col3.metric("GP Margin", f"{gp_margin_pct:.2f}%")
col4.metric("Active Stores", f"{store_count}")

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
].sort_values("Net Sales (NZD)", ascending=False)

st.dataframe(
    regional_display,
    hide_index=True,
    width="stretch",
)

st.subheader("Regional GP Margin Comparison")

chart_data = regional_display.set_index("Region")[
    "GP Margin (%)"
]

st.bar_chart(chart_data)

st.caption(
    "GP Margin = Gross Profit / Net Sales. "
    "All financial values are derived from validated SQL models."
)
