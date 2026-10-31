
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
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

        diagnostics = con.execute(
            sql("12_store_profitability_diagnostics.sql")
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

    return diagnostics, stores


def expected_calculations(stores):
    expected = stores.copy()

    totals = expected.groupby(
        ["region", "month"]
    ).agg(
        expected_region_sales=("net_sales_cents", "sum"),
        expected_region_gp=("gross_profit_cents", "sum"),
    ).reset_index()

    expected = expected.merge(
        totals,
        on=["region", "month"],
        validate="many_to_one",
    )

    sales = expected["net_sales_cents"]
    gp = expected["gross_profit_cents"]
    region_sales = expected["expected_region_sales"]
    region_gp = expected["expected_region_gp"]

    expected["expected_store_margin"] = 100 * gp / sales
    expected["expected_region_margin"] = (
        100 * region_gp / region_sales
    )
    expected["expected_sales_pct"] = (
        100 * sales / region_sales
    )
    expected["expected_gap"] = (
        expected["expected_store_margin"]
        - expected["expected_region_margin"]
    )
    expected["expected_impact"] = (
        sales / region_sales * expected["expected_gap"]
    )
    expected["expected_shortfall_cents"] = (
        sales * region_gp / region_sales - gp
    )

    return expected


def test_grain(data):
    diagnostics, stores = data

    assert len(diagnostics) == 1260
    assert diagnostics["store_id"].nunique() == 60
    assert diagnostics["region"].nunique() == 6
    assert diagnostics["month"].nunique() == 21
    assert not diagnostics.duplicated(
        ["store_id", "month"]
    ).any()
    assert len(stores) == len(diagnostics)


def test_source_financials(data):
    diagnostics, stores = data

    check = diagnostics.merge(
        stores,
        on=["region", "month", "store_id"],
        how="outer",
        validate="one_to_one",
        indicator=True,
        suffixes=("_actual", "_source"),
    )

    assert (check["_merge"] == "both").all()

    for col in ["net_sales_cents", "gross_profit_cents"]:
        assert (
            check[f"{col}_actual"]
            == check[f"{col}_source"]
        ).all()


def test_region_totals(data):
    diagnostics, stores = data

    expected = expected_calculations(stores)

    check = diagnostics.merge(
        expected,
        on=["region", "month", "store_id"],
        validate="one_to_one",
    )

    assert (
        check["region_sales_cents"]
        == check["expected_region_sales"]
    ).all()

    assert (
        check["region_gp_cents"]
        == check["expected_region_gp"]
    ).all()


def test_margin_and_contribution(data):
    diagnostics, stores = data
    expected = expected_calculations(stores)

    check = diagnostics.merge(
        expected,
        on=["region", "month", "store_id"],
        validate="one_to_one",
    )

    mappings = {
        "store_gp_margin_pct": "expected_store_margin",
        "region_gp_margin_pct": "expected_region_margin",
        "margin_gap_pp": "expected_gap",
        "sales_contribution_pct": "expected_sales_pct",
        "gp_gap_impact_pp": "expected_impact",
    }

    for actual_col, expected_col in mappings.items():
        assert np.allclose(
            check[actual_col],
            check[expected_col],
            rtol=0,
            atol=0.00000051,
        )


def test_shortfall_amounts(data):
    diagnostics, stores = data
    expected = expected_calculations(stores)

    check = diagnostics.merge(
        expected,
        on=["region", "month", "store_id"],
        validate="one_to_one",
    )

    assert np.allclose(
        check["gp_shortfall_cents"],
        check["expected_shortfall_cents"],
        rtol=0,
        atol=0.00000051,
    )

    assert np.allclose(
        check["gp_shortfall_nzd"],
        np.round(check["expected_shortfall_cents"] / 100, 2),
        rtol=0,
        atol=0.00000001,
    )


def test_region_reconciliation(data):
    diagnostics, _ = data

    totals = diagnostics.groupby(
        ["region", "month"]
    ).agg(
        sales_pct=("sales_contribution_pct", "sum"),
        impact=("gp_gap_impact_pp", "sum"),
        shortfall=("gp_shortfall_cents", "sum"),
    )

    assert np.allclose(
        totals["sales_pct"], 100, atol=0.00001, rtol=0
    )
    assert np.allclose(
        totals["impact"], 0, atol=0.00001, rtol=0
    )
    assert np.allclose(
        totals["shortfall"], 0, atol=0.00001, rtol=0
    )


def test_shortfall_rank(data):
    diagnostics, stores = data
    expected = expected_calculations(stores)

    expected = expected.sort_values(
        [
            "region",
            "month",
            "expected_shortfall_cents",
            "store_id",
        ],
        ascending=[True, True, False, True],
    )

    expected["expected_rank"] = (
        expected.groupby(["region", "month"]).cumcount() + 1
    )

    check = diagnostics.merge(
        expected[
            ["region", "month", "store_id", "expected_rank"]
        ],
        on=["region", "month", "store_id"],
        validate="one_to_one",
    )

    assert (
        check["shortfall_rank"] == check["expected_rank"]
    ).all()


def test_negative_impact_rank(data):
    diagnostics, stores = data
    expected = expected_calculations(stores)

    expected = expected.sort_values(
        [
            "region",
            "month",
            "expected_impact",
            "store_id",
        ],
        ascending=[True, True, True, True],
    )

    expected["expected_rank"] = (
        expected.groupby(["region", "month"]).cumcount() + 1
    )

    check = diagnostics.merge(
        expected[
            ["region", "month", "store_id", "expected_rank"]
        ],
        on=["region", "month", "store_id"],
        validate="one_to_one",
    )

    assert (
        check["negative_impact_rank"]
        == check["expected_rank"]
    ).all()


def test_no_missing_values(data):
    diagnostics, _ = data

    assert not diagnostics.isna().any().any()
    assert (diagnostics["net_sales_cents"] > 0).all()
    assert (diagnostics["region_sales_cents"] > 0).all()


def test_rank_coverage(data):
    diagnostics, _ = data

    for _, group in diagnostics.groupby(["region", "month"]):
        expected = list(range(1, len(group) + 1))

        assert sorted(group["shortfall_rank"]) == expected
        assert sorted(group["negative_impact_rank"]) == expected
