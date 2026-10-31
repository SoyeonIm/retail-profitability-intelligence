
from pathlib import Path

import duckdb
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
KEYS = ["region", "month", "category"]


@pytest.fixture(scope="module")
def data():
    def sql(name):
        return (
            ROOT / "sql" / name
        ).read_text(encoding="utf-8").strip().rstrip(";")

    con = duckdb.connect()

    try:
        con.execute(
            "CREATE TEMP VIEW category_mart AS "
            + sql("04_category_profitability.sql")
        )

        drivers = con.execute(
            sql("09_category_margin_drivers.sql")
        ).df()

        decomposition = con.execute(
            sql("08_regional_margin_decomposition.sql")
        ).df()

        source = con.execute("""
            SELECT
                s.region,
                c.month,
                c.category,
                SUM(c.net_sales_cents) AS sales_cents,
                SUM(c.gross_profit_cents) AS gp_cents
            FROM category_mart c
            JOIN read_csv_auto('data/raw/stores.csv') s
              ON c.store_id = s.store_id
            GROUP BY s.region, c.month, c.category
        """).df()

        store_keys = con.execute("""
            SELECT
                COUNT(*) AS rows,
                COUNT(DISTINCT store_id) AS unique_stores
            FROM read_csv_auto('data/raw/stores.csv')
        """).fetchone()

    finally:
        con.close()

    return drivers, decomposition, source, store_keys


def test_store_dimension_unique(data):
    _, _, _, store_keys = data
    assert store_keys[0] == store_keys[1] == 60


def test_driver_grain(data):
    drivers, _, _, _ = data

    assert len(drivers) == 756
    assert drivers["region"].nunique() == 6
    assert drivers["month"].nunique() == 21
    assert drivers["category"].nunique() == 6
    assert not drivers.duplicated(KEYS).any()


def test_category_financials_reconcile(data):
    drivers, _, source, _ = data

    check = drivers.merge(
        source,
        on=KEYS,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    assert (check["_merge"] == "both").all()

    assert (
        check["category_sales_cents"]
        == check["sales_cents"]
    ).all()

    assert (
        check["category_gp_cents"]
        == check["gp_cents"]
    ).all()


def test_region_totals_reconcile(data):
    drivers, decomposition, _, _ = data

    totals = drivers.groupby(
        ["region", "month"],
        as_index=False,
    ).agg(
        sales=("category_sales_cents", "sum"),
        gp=("category_gp_cents", "sum"),
    )

    check = totals.merge(
        decomposition[
            [
                "region",
                "month",
                "region_sales_cents",
                "region_gp_cents",
            ]
        ],
        on=["region", "month"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    assert (check["_merge"] == "both").all()
    assert (check["sales"] == check["region_sales_cents"]).all()
    assert (check["gp"] == check["region_gp_cents"]).all()


def test_category_margins(data):
    drivers, _, _, _ = data

    assert (drivers["category_sales_cents"] > 0).all()
    assert (drivers["benchmark_category_sales_cents"] > 0).all()

    expected_region = (
        100.0
        * drivers["category_gp_cents"]
        / drivers["category_sales_cents"]
    )

    expected_benchmark = (
        100.0
        * drivers["benchmark_category_gp_cents"]
        / drivers["benchmark_category_sales_cents"]
    )

    assert np.allclose(
        drivers["region_category_margin_pct"],
        expected_region,
        atol=0.00000051,
        rtol=0,
    )

    assert np.allclose(
        drivers["benchmark_category_margin_pct"],
        expected_benchmark,
        atol=0.00000051,
        rtol=0,
    )


def test_category_mix_sums_to_100(data):
    drivers, _, _, _ = data

    region_mix = drivers.groupby(
        ["region", "month"]
    )["region_sales_mix_pct"].sum()

    benchmark_mix = drivers.groupby(
        ["region", "month"]
    )["benchmark_sales_mix_pct"].sum()

    assert np.allclose(region_mix, 100.0, atol=0.00001, rtol=0)
    assert np.allclose(benchmark_mix, 100.0, atol=0.00001, rtol=0)


def test_effects_match_independent_formula(data):
    drivers, _, _, _ = data

    region_mix = (
        drivers["category_sales_cents"]
        / drivers["region_sales_cents"]
    )

    benchmark_mix = (
        drivers["benchmark_category_sales_cents"]
        / drivers["benchmark_sales_cents"]
    )

    benchmark_margin = (
        drivers["benchmark_category_gp_cents"]
        / drivers["benchmark_category_sales_cents"]
    )

    region_margin = (
        drivers["category_gp_cents"]
        / drivers["category_sales_cents"]
    )

    expected_mix = (
        100.0
        * (region_mix - benchmark_mix)
        * benchmark_margin
    )

    expected_margin = (
        100.0
        * region_mix
        * (region_margin - benchmark_margin)
    )

    assert np.allclose(
        drivers["mix_effect_pp"],
        expected_mix,
        atol=0.00000051,
        rtol=0,
    )

    assert np.allclose(
        drivers["margin_effect_pp"],
        expected_margin,
        atol=0.00000051,
        rtol=0,
    )

    assert np.allclose(
        drivers["total_effect_pp"],
        expected_mix + expected_margin,
        atol=0.00000051,
        rtol=0,
    )


def test_effects_reconcile_to_step_8(data):
    drivers, decomposition, _, _ = data

    summary = drivers.groupby(
        ["region", "month"],
        as_index=False,
    )[
        ["mix_effect_pp", "margin_effect_pp", "total_effect_pp"]
    ].sum()

    check = summary.merge(
        decomposition[
            [
                "region",
                "month",
                "mix_effect_pp",
                "margin_effect_pp",
                "actual_gap_pp",
            ]
        ],
        on=["region", "month"],
        how="outer",
        validate="one_to_one",
        suffixes=("_drivers", "_step8"),
        indicator=True,
    )

    assert (check["_merge"] == "both").all()

    for effect in ["mix_effect_pp", "margin_effect_pp"]:
        assert np.allclose(
            check[f"{effect}_drivers"],
            check[f"{effect}_step8"],
            atol=0.000004,
            rtol=0,
        )

    assert np.allclose(
        check["total_effect_pp"],
        check["actual_gap_pp"],
        atol=0.000004,
        rtol=0,
    )


def test_no_missing_effects(data):
    drivers, _, _, _ = data

    columns = [
        "region_sales_mix_pct",
        "benchmark_sales_mix_pct",
        "region_category_margin_pct",
        "benchmark_category_margin_pct",
        "mix_effect_pp",
        "margin_effect_pp",
        "total_effect_pp",
    ]

    assert drivers[columns].notna().all().all()
    assert np.isfinite(drivers[columns].to_numpy()).all()
