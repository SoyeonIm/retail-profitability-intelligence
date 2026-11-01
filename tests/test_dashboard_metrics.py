
"""Tests for monthly dashboard financial metrics."""

import pandas as pd
import pytest

from src.dashboard_metrics import calculate_monthly_kpis
from src.reporting_data import load_reporting_data


@pytest.fixture(scope="module")
def monthly():
    store = load_reporting_data()["store"]
    return calculate_monthly_kpis(store)


def test_monthly_row_count(monthly):
    assert len(monthly) == 21


def test_monthly_unique_keys(monthly):
    assert not monthly["month"].duplicated().any()


def test_monthly_chronological_order(monthly):
    assert monthly["month"].is_monotonic_increasing


def test_september_financial_totals(monthly):
    latest = monthly.iloc[-1]

    assert latest["net_sales_cents"] == 25955980
    assert latest["gross_profit_cents"] == 8363255
    assert latest["store_count"] == 60


def test_september_weighted_margin(monthly):
    latest = monthly.iloc[-1]

    expected = (
        latest["gross_profit_cents"]
        / latest["net_sales_cents"]
        * 100
    )

    assert latest["gp_margin_pct"] == pytest.approx(expected)


def test_september_mom_changes(monthly):
    august = monthly.iloc[-2]
    september = monthly.iloc[-1]

    expected_sales_mom = (
        september["net_sales_cents"]
        / august["net_sales_cents"]
        - 1
    ) * 100

    expected_gp_mom = (
        september["gross_profit_cents"]
        / august["gross_profit_cents"]
        - 1
    ) * 100

    expected_margin_change = (
        september["gp_margin_pct"]
        - august["gp_margin_pct"]
    )

    assert september["sales_mom_pct"] == pytest.approx(
        expected_sales_mom
    )

    assert september["gp_mom_pct"] == pytest.approx(
        expected_gp_mom
    )

    assert september["margin_mom_pp"] == pytest.approx(
        expected_margin_change
    )


def test_first_month_has_no_mom_comparison(monthly):
    first = monthly.iloc[0]

    assert pd.isna(first["sales_mom_pct"])
    assert pd.isna(first["gp_mom_pct"])
    assert pd.isna(first["margin_mom_pp"])


def test_missing_required_column():
    incomplete = pd.DataFrame({
        "month": ["2026-09-01"],
        "store_id": ["S001"],
    })

    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_monthly_kpis(incomplete)


def test_empty_dataset():
    empty = pd.DataFrame(
        columns=[
            "month",
            "store_id",
            "net_sales_cents",
            "gross_profit_cents",
        ]
    )

    with pytest.raises(ValueError, match="empty"):
        calculate_monthly_kpis(empty)


def test_duplicate_store_month_rejected():
    duplicate = pd.DataFrame({
        "month": ["2026-09-01", "2026-09-01"],
        "store_id": ["S001", "S001"],
        "net_sales_cents": [10000, 10000],
        "gross_profit_cents": [3000, 3000],
    })

    with pytest.raises(ValueError, match="Duplicate"):
        calculate_monthly_kpis(duplicate)


def test_non_positive_sales_rejected():
    invalid = pd.DataFrame({
        "month": ["2026-09-01"],
        "store_id": ["S001"],
        "net_sales_cents": [0],
        "gross_profit_cents": [0],
    })

    with pytest.raises(ValueError, match="positive"):
        calculate_monthly_kpis(invalid)
