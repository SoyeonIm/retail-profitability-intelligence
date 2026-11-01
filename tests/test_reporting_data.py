
"""Tests for the Streamlit reporting data access layer."""

import pytest

from src.reporting_data import (
    create_reporting_connection,
    load_reporting_data,
    read_sql,
)


@pytest.fixture(scope="module")
def reporting_data():
    return load_reporting_data()


def test_sql_file_loading():
    sql = read_sql("15_store_reporting.sql")

    assert "SELECT" in sql.upper()
    assert "store_performance" in sql


def test_missing_sql_file():
    with pytest.raises(FileNotFoundError):
        read_sql("nonexistent_reporting_file.sql")


def test_reporting_views_available():
    con = create_reporting_connection()

    try:
        views = {
            row[0]
            for row in con.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                """
            ).fetchall()
        }

        assert "store_reporting" in views
        assert "regional_reporting" in views

    finally:
        con.close()


def test_reporting_row_counts(reporting_data):
    assert len(reporting_data["store"]) == 1260
    assert len(reporting_data["region"]) == 126


def test_reporting_unique_keys(reporting_data):
    store = reporting_data["store"]
    region = reporting_data["region"]

    assert not store.duplicated(
        ["store_id", "month"]
    ).any()

    assert not region.duplicated(
        ["region", "month"]
    ).any()


@pytest.mark.parametrize(
    "column",
    [
        "net_sales_cents",
        "cogs_cents",
        "gross_profit_cents",
        "sale_discount_cents",
    ],
)
def test_reporting_financial_reconciliation(reporting_data, column):
    store = reporting_data["store"]
    region = reporting_data["region"]

    store_totals = (
        store.groupby(["region", "month"])[column]
        .sum()
        .sort_index()
    )

    region_totals = (
        region.set_index(["region", "month"])[column]
        .sort_index()
    )

    assert store_totals.equals(region_totals)


def test_reporting_gp_identity(reporting_data):
    for name in ["store", "region"]:
        data = reporting_data[name]

        assert (
            data["net_sales_cents"]
            - data["cogs_cents"]
            == data["gross_profit_cents"]
        ).all()


def test_reporting_required_fields(reporting_data):
    store = reporting_data["store"]
    region = reporting_data["region"]

    assert store[
        ["store_id", "region", "month", "investigation_priority"]
    ].notna().all().all()

    assert region[
        ["region", "month", "regional_gp_margin_pct"]
    ].notna().all().all()
