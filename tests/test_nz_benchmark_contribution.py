
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
TOL = 0.00000051


@pytest.fixture(scope="module")
def data():
    def sql(filename):
        return (
            ROOT / "sql" / filename
        ).read_text(encoding="utf-8").strip().rstrip(";")

    con = duckdb.connect()

    try:
        con.execute(
            "CREATE TEMP VIEW category_mart AS "
            + sql("04_category_profitability.sql")
        )
        con.execute(
            "CREATE TEMP VIEW store_performance AS "
            + sql("06_store_performance.sql")
        )

        actual = con.execute(
            sql("13_nz_benchmark_contribution.sql")
        ).df()

        stores = con.execute("""
            SELECT
                region,
                month,
                store_id,
                net_sales_cents,
                gross_profit_cents
            FROM store_performance
            WHERE net_sales_cents > 0
        """).df()

    finally:
        con.close()

    return actual, stores


def calculate_expected(stores):
    expected = stores.copy()

    regional = expected.groupby(
        ["region", "month"]
    ).agg(
        region_sales=("net_sales_cents", "sum"),
        region_gp=("gross_profit_cents", "sum"),
    ).reset_index()

    national = expected.groupby("month").agg(
        nz_sales=("net_sales_cents", "sum"),
        nz_gp=("gross_profit_cents", "sum"),
    ).reset_index()

    expected = expected.merge(
        regional,
        on=["region", "month"],
        validate="many_to_one",
    ).merge(
        national,
        on="month",
        validate="many_to_one",
    )

    sales = expected["net_sales_cents"]
    gp = expected["gross_profit_cents"]

    expected["store_margin"] = 100 * gp / sales
    expected["region_margin"] = (
        100 * expected["region_gp"] / expected["region_sales"]
    )
    expected["nz_margin"] = (
        100 * expected["nz_gp"] / expected["nz_sales"]
    )

    expected["store_gap"] = (
        expected["store_margin"] - expected["nz_margin"]
    )
    expected["region_gap"] = (
        expected["region_margin"] - expected["nz_margin"]
    )
    expected["sales_share"] = (
        100 * sales / expected["region_sales"]
    )
    expected["contribution"] = (
        sales / expected["region_sales"]
        * expected["store_gap"]
    )
    expected["shortfall_cents"] = (
        sales * expected["nz_gp"] / expected["nz_sales"] - gp
    )

    return expected


@pytest.fixture(scope="module")
def comparison(data):
    actual, stores = data
    expected = calculate_expected(stores)

    check = actual.merge(
        expected,
        on=["region", "month", "store_id"],
        how="outer",
        validate="one_to_one",
        indicator=True,
        suffixes=("_actual", "_expected"),
    )

    assert (check["_merge"] == "both").all()
    return check


def assert_close(actual, expected):
    assert np.allclose(
        actual, expected, atol=TOL, rtol=0
    )


def test_grain(data):
    actual, stores = data

    assert len(actual) == 1260
    assert actual["store_id"].nunique() == 60
    assert actual["region"].nunique() == 6
    assert actual["month"].nunique() == 21
    assert not actual.duplicated(
        ["store_id", "month"]
    ).any()
    assert len(stores) == len(actual)


def test_source_financials(comparison):
    for column in ["net_sales_cents", "gross_profit_cents"]:
        assert (
            comparison[f"{column}_actual"]
            == comparison[f"{column}_expected"]
        ).all()


def test_regional_and_national_totals(comparison):
    mappings = {
        "region_sales_cents": "region_sales",
        "region_gp_cents": "region_gp",
        "nz_sales_cents": "nz_sales",
        "nz_gp_cents": "nz_gp",
    }

    for actual_col, expected_col in mappings.items():
        assert (
            comparison[actual_col]
            == comparison[expected_col]
        ).all()


def test_margins(comparison):
    mappings = {
        "store_gp_margin_pct": "store_margin",
        "region_gp_margin_pct": "region_margin",
        "nz_gp_margin_pct": "nz_margin",
    }

    for actual_col, expected_col in mappings.items():
        assert_close(
            comparison[actual_col],
            comparison[expected_col],
        )


def test_benchmark_gaps(comparison):
    assert_close(
        comparison["store_vs_nz_gap_pp"],
        comparison["store_gap"],
    )

    assert_close(
        comparison["region_vs_nz_gap_pp"],
        comparison["region_gap"],
    )


def test_sales_share_and_contribution(comparison):
    assert_close(
        comparison["region_sales_share_pct"],
        comparison["sales_share"],
    )

    assert_close(
        comparison["contribution_to_region_gap_pp"],
        comparison["contribution"],
    )


def test_shortfall_amounts(comparison):
    assert_close(
        comparison["gp_shortfall_vs_nz_cents"],
        comparison["shortfall_cents"],
    )

    expected_nzd = np.round(
        comparison["shortfall_cents"] / 100.0, 2
    )

    assert np.allclose(
        comparison["gp_shortfall_vs_nz_nzd"],
        expected_nzd,
        atol=0.00000001,
        rtol=0,
    )


def test_contribution_reconciliation(comparison):
    grouped = comparison.groupby(
        ["region", "month"]
    ).agg(
        contribution_sum=("contribution", "sum"),
        region_gap=("region_gap", "first"),
    )

    assert np.allclose(
        grouped["contribution_sum"],
        grouped["region_gap"],
        atol=1e-10,
        rtol=0,
    )


def test_shortfall_reconciliation(comparison):
    grouped = comparison.groupby(
        ["region", "month"]
    ).agg(
        shortfall_sum=("shortfall_cents", "sum"),
        region_sales=("region_sales", "first"),
        region_gp=("region_gp", "first"),
        nz_sales=("nz_sales", "first"),
        nz_gp=("nz_gp", "first"),
    )

    expected_shortfall = (
        grouped["region_sales"]
        * grouped["nz_gp"]
        / grouped["nz_sales"]
        - grouped["region_gp"]
    )

    assert np.allclose(
        grouped["shortfall_sum"],
        expected_shortfall,
        atol=1e-8,
        rtol=0,
    )


def test_negative_contribution_ranking(comparison):
    expected = comparison.sort_values(
        ["region", "month", "contribution", "store_id"],
        ascending=[True, True, True, True],
    ).copy()

    expected["expected_rank"] = (
        expected.groupby(["region", "month"]).cumcount() + 1
    )

    assert (
        expected["negative_contribution_rank"]
        == expected["expected_rank"]
    ).all()


def test_no_missing_values(data):
    actual, _ = data

    assert not actual.isna().any().any()
    assert (actual["net_sales_cents"] > 0).all()
    assert (actual["region_sales_cents"] > 0).all()
    assert (actual["nz_sales_cents"] > 0).all()
