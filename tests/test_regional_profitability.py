
from pathlib import Path

import duckdb
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def marts():
    category_sql = (
        ROOT / "sql/04_category_profitability.sql"
    ).read_text(encoding="utf-8").strip().rstrip(";")

    store_sql = (
        ROOT / "sql/06_store_performance.sql"
    ).read_text(encoding="utf-8").strip().rstrip(";")

    region_sql = (
        ROOT / "sql/07_regional_profitability.sql"
    ).read_text(encoding="utf-8").strip().rstrip(";")

    con = duckdb.connect()
    try:
        con.execute(
            f"CREATE TEMP VIEW category_mart AS {category_sql}"
        )
        con.execute(
            f"CREATE TEMP VIEW store_performance AS {store_sql}"
        )

        store = con.execute(
            "SELECT * FROM store_performance"
        ).df()

        region = con.execute(region_sql).df()
    finally:
        con.close()

    return store, region


def test_region_month_grain(marts):
    _, region = marts

    assert len(region) == 126
    assert region["region"].nunique() == 6
    assert region["month"].nunique() == 21
    assert not region.duplicated(["region", "month"]).any()


def test_region_store_counts(marts):
    store, region = marts

    expected = (
        store.groupby(["region", "month"])["store_id"]
        .nunique()
        .reset_index(name="expected_store_count")
    )

    comparison = region.merge(
        expected,
        on=["region", "month"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    assert (comparison["_merge"] == "both").all()
    assert (
        comparison["store_count"]
        == comparison["expected_store_count"]
    ).all()


def test_financial_totals_reconcile_to_store_mart(marts):
    store, region = marts

    columns = [
        "net_sales_cents",
        "cogs_cents",
        "gross_profit_cents",
        "sale_lines",
        "return_lines",
        "sale_discount_cents",
    ]

    expected = store.groupby(
        ["region", "month"],
        as_index=False,
    )[columns].sum()

    comparison = region.merge(
        expected,
        on=["region", "month"],
        how="outer",
        validate="one_to_one",
        suffixes=("", "_expected"),
        indicator=True,
    )

    assert (comparison["_merge"] == "both").all()

    for column in columns:
        assert (
            comparison[column]
            == comparison[f"{column}_expected"]
        ).all()

    assert (
        region["gross_profit_cents"]
        == region["net_sales_cents"] - region["cogs_cents"]
    ).all()


def test_regional_margin_uses_weighted_calculation(marts):
    _, region = marts

    expected = (
        100.0
        * region["gross_profit_cents"]
        / region["net_sales_cents"]
    )

    assert np.allclose(
        region["regional_gp_margin_pct"],
        expected,
        atol=0.000051,
        rtol=0,
    )


def test_nz_benchmark_matches_monthly_financials(marts):
    _, region = marts

    monthly = region.groupby(
        "month",
        as_index=False,
    ).agg(
        sales=("net_sales_cents", "sum"),
        gp=("gross_profit_cents", "sum"),
    )

    monthly["expected_margin"] = (
        100.0 * monthly["gp"] / monthly["sales"]
    )

    actual = region[
        ["month", "nz_gp_margin_pct"]
    ].drop_duplicates()

    comparison = actual.merge(
        monthly[["month", "expected_margin"]],
        on="month",
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    assert (comparison["_merge"] == "both").all()

    assert np.allclose(
        comparison["nz_gp_margin_pct"],
        comparison["expected_margin"],
        atol=0.000051,
        rtol=0,
    )


def test_regional_contributions_sum_to_100(marts):
    _, region = marts

    monthly = region.groupby("month").agg(
        sales_share=("sales_contribution_pct", "sum"),
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
    _, region = marts

    expected = (
        100.0
        * region["gross_profit_cents"]
        / region["net_sales_cents"]
        - region["nz_gp_margin_pct"]
    )

    assert np.allclose(
        region["margin_variance_pp"],
        expected,
        atol=0.00011,
        rtol=0,
    )


def test_regional_gp_margin_rank(marts):
    _, region = marts

    expected = region.groupby("month")[
        "regional_gp_margin_pct"
    ].rank(method="min", ascending=False)

    assert (
        region["regional_gp_margin_rank"].to_numpy()
        == expected.to_numpy()
    ).all()
