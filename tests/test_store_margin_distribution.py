
from pathlib import Path

import duckdb
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]


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

        distribution = con.execute(
            sql("10_store_margin_distribution.sql")
        ).df()

        stores = con.execute("""
            SELECT
                region,
                month,
                store_id,
                net_sales_cents,
                gross_profit_cents,
                100.0 * gross_profit_cents::DOUBLE
                    / net_sales_cents AS margin_pct
            FROM store_performance
            WHERE net_sales_cents > 0
        """).df()

        regional = con.execute(
            sql("07_regional_profitability.sql")
        ).df()

    finally:
        con.close()

    return distribution, stores, regional


def test_distribution_grain(data):
    distribution, _, _ = data

    assert len(distribution) == 126
    assert distribution["region"].nunique() == 6
    assert distribution["month"].nunique() == 21
    assert not distribution.duplicated(
        ["region", "month"]
    ).any()


def test_store_counts(data):
    distribution, stores, _ = data

    expected = stores.groupby(
        ["region", "month"]
    )["store_id"].nunique().reset_index(name="expected_count")

    check = distribution.merge(
        expected,
        on=["region", "month"],
        validate="one_to_one",
    )

    assert len(check) == len(distribution)
    assert (check["store_count"] == check["expected_count"]).all()
    assert (check["store_count"] == 10).all()


def test_financial_totals(data):
    distribution, _, regional = data

    check = distribution.merge(
        regional[
            [
                "region",
                "month",
                "net_sales_cents",
                "gross_profit_cents",
            ]
        ],
        on=["region", "month"],
        validate="one_to_one",
    )

    assert len(check) == len(distribution)
    assert (
        check["region_sales_cents"]
        == check["net_sales_cents"]
    ).all()
    assert (
        check["region_gp_cents"]
        == check["gross_profit_cents"]
    ).all()


def test_weighted_margin(data):
    distribution, _, _ = data

    expected = (
        100.0
        * distribution["region_gp_cents"]
        / distribution["region_sales_cents"]
    )

    assert np.allclose(
        distribution["weighted_gp_margin_pct"],
        expected,
        atol=0.00000051,
        rtol=0,
    )


def test_distribution_statistics(data):
    distribution, stores, _ = data

    expected = stores.groupby(
        ["region", "month"]
    )["margin_pct"].agg(
        mean="mean",
        median="median",
        minimum="min",
        maximum="max",
        stddev="std",
    ).reset_index()

    check = distribution.merge(
        expected,
        on=["region", "month"],
        validate="one_to_one",
    )

    assert len(check) == len(distribution)

    mappings = {
        "mean_store_gp_margin_pct": "mean",
        "median_store_gp_margin_pct": "median",
        "min_gp_margin_pct": "minimum",
        "max_gp_margin_pct": "maximum",
        "stddev_gp_margin_pp": "stddev",
    }

    for actual, expected_col in mappings.items():
        assert np.allclose(
            check[actual],
            check[expected_col],
            atol=0.00000051,
            rtol=0,
        )


def test_quartiles_and_iqr(data):
    distribution, stores, _ = data

    expected = stores.groupby(
        ["region", "month"]
    )["margin_pct"].quantile(
        [0.25, 0.75]
    ).unstack().reset_index()

    expected.columns = [
        "region",
        "month",
        "p25_expected",
        "p75_expected",
    ]

    check = distribution.merge(
        expected,
        on=["region", "month"],
        validate="one_to_one",
    )

    assert len(check) == len(distribution)

    assert np.allclose(
        check["p25_gp_margin_pct"],
        check["p25_expected"],
        atol=0.00000051,
        rtol=0,
    )

    assert np.allclose(
        check["p75_gp_margin_pct"],
        check["p75_expected"],
        atol=0.00000051,
        rtol=0,
    )

    assert np.allclose(
        check["iqr_gp_margin_pp"],
        check["p75_expected"] - check["p25_expected"],
        atol=0.00000051,
        rtol=0,
    )


def test_stores_below_average(data):
    distribution, stores, _ = data

    check = stores.merge(
        distribution[
            ["region", "month", "weighted_gp_margin_pct"]
        ],
        on=["region", "month"],
        validate="many_to_one",
    )

    expected = check.assign(
        below=(
            check["margin_pct"]
            < check["weighted_gp_margin_pct"]
        ).astype(int)
    ).groupby(
        ["region", "month"]
    )["below"].sum().reset_index(name="expected_below")

    actual = distribution.merge(
        expected,
        on=["region", "month"],
        validate="one_to_one",
    )

    assert (
        actual["stores_below_weighted_avg"]
        == actual["expected_below"]
    ).all()


def test_extreme_store_ids(data):
    distribution, stores, _ = data

    ordered = stores.sort_values(
        ["region", "month", "margin_pct", "store_id"],
        ascending=[True, True, False, True],
    )

    highest = ordered.drop_duplicates(
        ["region", "month"]
    )[["region", "month", "store_id"]].rename(
        columns={"store_id": "expected_highest"}
    )

    lowest = stores.sort_values(
        ["region", "month", "margin_pct", "store_id"],
        ascending=[True, True, True, True],
    ).drop_duplicates(
        ["region", "month"]
    )[["region", "month", "store_id"]].rename(
        columns={"store_id": "expected_lowest"}
    )

    check = distribution.merge(
        highest,
        on=["region", "month"],
        validate="one_to_one",
    ).merge(
        lowest,
        on=["region", "month"],
        validate="one_to_one",
    )

    assert (
        check["highest_margin_store_id"]
        == check["expected_highest"]
    ).all()
    assert (
        check["lowest_margin_store_id"]
        == check["expected_lowest"]
    ).all()


def test_no_missing_values(data):
    distribution, _, _ = data

    assert not distribution.isna().any().any()
    assert (distribution["region_sales_cents"] > 0).all()
    assert (distribution["store_count"] > 0).all()
