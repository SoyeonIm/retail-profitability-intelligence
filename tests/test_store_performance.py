
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def marts():
    category_sql = (
        ROOT / "sql/04_category_profitability.sql"
    ).read_text(encoding="utf-8").strip().rstrip(";")

    performance_sql = (
        ROOT / "sql/06_store_performance.sql"
    ).read_text(encoding="utf-8").strip().rstrip(";")

    con = duckdb.connect()

    try:
        con.execute(
            f"CREATE TEMP VIEW category_mart AS {category_sql}"
        )

        category = con.execute(
            "SELECT * FROM category_mart"
        ).df()

        performance = con.execute(
            performance_sql
        ).df()

        stores = con.execute(
            "SELECT * FROM read_csv_auto('data/raw/stores.csv')"
        ).df()
    finally:
        con.close()

    return category, performance, stores


def test_store_month_grain(marts):
    _, performance, _ = marts

    assert len(performance) == 1260
    assert performance["store_id"].nunique() == 60
    assert performance["month"].nunique() == 21

    assert not performance.duplicated(
        ["store_id", "month"]
    ).any()


def test_store_dimensions_match_source(marts):
    _, performance, stores = marts

    assert not stores["store_id"].duplicated().any()

    expected = stores[
        ["store_id", "region", "floor_area_sqm", "open_date"]
    ]

    actual = performance.merge(
        expected,
        on="store_id",
        how="left",
        validate="many_to_one",
        suffixes=("", "_source"),
        indicator=True,
    )

    assert (actual["_merge"] == "both").all()

    for column in ["region", "floor_area_sqm", "open_date"]:
        pd.testing.assert_series_equal(
            actual[column],
            actual[f"{column}_source"],
            check_names=False,
        )


def test_financial_totals_reconcile_to_category_mart(marts):
    category, performance, _ = marts

    columns = [
        "transaction_lines",
        "sale_lines",
        "return_lines",
        "net_sales_cents",
        "cogs_cents",
        "gross_profit_cents",
        "sale_discount_cents",
    ]

    expected = category.groupby(
        ["store_id", "month"],
        as_index=False,
    )[columns].sum()

    actual = performance.merge(
        expected,
        on=["store_id", "month"],
        how="outer",
        validate="one_to_one",
        suffixes=("", "_expected"),
        indicator=True,
    )

    assert (actual["_merge"] == "both").all()

    for column in columns:
        assert (
            actual[column] == actual[f"{column}_expected"]
        ).all()

    assert (
        performance["gross_profit_cents"]
        == performance["net_sales_cents"]
        - performance["cogs_cents"]
    ).all()


def test_benchmark_is_sales_weighted(marts):
    _, performance, _ = marts

    monthly = performance.groupby(
        "month",
        as_index=False,
    ).agg(
        sales=("net_sales_cents", "sum"),
        gp=("gross_profit_cents", "sum"),
    )

    monthly["expected_margin"] = (
        100.0 * monthly["gp"] / monthly["sales"]
    )

    actual = performance[
        ["month", "benchmark_gp_margin_pct"]
    ].drop_duplicates()

    comparison = actual.merge(
        monthly[["month", "expected_margin"]],
        on="month",
        validate="one_to_one",
    )

    assert len(comparison) == 21

    assert np.allclose(
        comparison["benchmark_gp_margin_pct"],
        comparison["expected_margin"],
        atol=0.000051,
        rtol=0,
    )


def test_contributions_sum_to_100_percent(marts):
    _, performance, _ = marts

    monthly = performance.groupby("month").agg(
        sales_share=("sales_share_pct", "sum"),
        gp_share=("gp_contribution_pct", "sum"),
    )

    assert np.allclose(
        monthly["sales_share"],
        100.0,
        atol=0.0001,
        rtol=0,
    )

    assert np.allclose(
        monthly["gp_share"],
        100.0,
        atol=0.0001,
        rtol=0,
    )


def test_margin_variance_reconciles(marts):
    _, performance, _ = marts

    expected = (
        100.0
        * performance["gross_profit_cents"]
        / performance["net_sales_cents"]
        - performance["benchmark_gp_margin_pct"]
    )

    assert np.allclose(
        performance["margin_variance_pp"],
        expected,
        atol=0.00011,
        rtol=0,
    )


def test_return_line_ratio(marts):
    _, performance, _ = marts

    expected = (
        100.0
        * performance["return_lines"]
        / performance["sale_lines"]
    )

    assert np.allclose(
        performance["return_lines_per_100_sale_lines"],
        expected,
        atol=0.000051,
        rtol=0,
    )


def test_monthly_ranks_match_financial_values(marts):
    _, performance, _ = marts

    rank_cases = [
        ("net_sales_cents", "sales_rank"),
        ("gross_profit_cents", "gp_rank"),
        ("gp_margin_pct", "gp_margin_rank"),
    ]

    for value_column, rank_column in rank_cases:
        expected = performance.groupby("month")[
            value_column
        ].rank(method="min", ascending=False)

        assert (
            performance[rank_column].to_numpy()
            == expected.to_numpy()
        ).all()
