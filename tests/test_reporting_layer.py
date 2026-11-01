
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]


def read_sql(filename):
    return (
        ROOT / "sql" / filename
    ).read_text(encoding="utf-8").strip().rstrip(";")


@pytest.fixture(scope="module")
def reporting_data():
    con = duckdb.connect()

    views = [
        ("category_mart", "04_category_profitability.sql"),
        ("store_performance", "06_store_performance.sql"),
        ("regional_profitability", "07_regional_profitability.sql"),
        ("category_margin_drivers", "09_category_margin_drivers.sql"),
        ("profitability_trends", "11_profitability_trends.sql"),
        ("store_profitability_diagnostics", "12_store_profitability_diagnostics.sql"),
        ("nz_benchmark_contribution", "13_nz_benchmark_contribution.sql"),
        ("investigation_priorities", "14_investigation_priorities.sql"),
        ("store_reporting", "15_store_reporting.sql"),
        ("regional_reporting", "16_regional_reporting.sql"),
    ]

    try:
        for name, filename in views:
            con.execute(
                f"CREATE TEMP VIEW {name} AS "
                + read_sql(filename)
            )

        data = {
            name: con.execute(
                f"SELECT * FROM {name}"
            ).df()
            for name, _ in views
        }

    finally:
        con.close()

    return data


def test_reporting_grains(reporting_data):
    store = reporting_data["store_reporting"]
    region = reporting_data["regional_reporting"]

    assert len(store) == 1260
    assert len(region) == 126

    assert not store.duplicated(
        ["store_id", "month"]
    ).any()

    assert not region.duplicated(
        ["region", "month"]
    ).any()


def test_store_source_keys_preserved(reporting_data):
    store = reporting_data["store_reporting"]
    source = reporting_data["store_performance"]

    keys = ["store_id", "region", "month"]

    merged = store[keys].merge(
        source[keys],
        on=keys,
        how="outer",
        indicator=True,
        validate="one_to_one",
    )

    assert (merged["_merge"] == "both").all()


def test_regional_source_keys_preserved(reporting_data):
    region = reporting_data["regional_reporting"]
    source = reporting_data["regional_profitability"]

    keys = ["region", "month"]

    merged = region[keys].merge(
        source[keys],
        on=keys,
        how="outer",
        indicator=True,
        validate="one_to_one",
    )

    assert (merged["_merge"] == "both").all()


@pytest.mark.parametrize(
    "metric",
    [
        "net_sales_cents",
        "cogs_cents",
        "gross_profit_cents",
        "sale_discount_cents",
        "sale_lines",
        "return_lines",
    ],
)
def test_store_region_financial_reconciliation(
    reporting_data, metric
):
    store = reporting_data["store_reporting"]
    region = reporting_data["regional_reporting"]

    store_totals = (
        store.groupby(["region", "month"])[metric]
        .sum()
        .reset_index(name="store_total")
    )

    merged = store_totals.merge(
        region[["region", "month", metric]],
        on=["region", "month"],
        validate="one_to_one",
    )

    assert len(merged) == len(region)

    assert (
        merged["store_total"]
        == merged[metric]
    ).all()


@pytest.mark.parametrize(
    "metric",
    [
        "net_sales_cents",
        "cogs_cents",
        "gross_profit_cents",
        "sale_discount_cents",
    ],
)
def test_store_financials_match_source(
    reporting_data, metric
):
    store = reporting_data["store_reporting"]
    source = reporting_data["store_performance"]

    merged = store.merge(
        source[
            ["store_id", "month", metric]
        ],
        on=["store_id", "month"],
        suffixes=("_report", "_source"),
        validate="one_to_one",
    )

    assert (
        merged[f"{metric}_report"]
        == merged[f"{metric}_source"]
    ).all()


def test_store_gp_margin_recalculation(reporting_data):
    store = reporting_data["store_reporting"]

    expected = (
        100.0
        * store["gross_profit_cents"]
        / store["net_sales_cents"]
    )

    assert np.allclose(
        store["gp_margin_pct"],
        expected,
        atol=0.0001,
        rtol=0,
    )


def test_regional_gp_margin_recalculation(reporting_data):
    region = reporting_data["regional_reporting"]

    expected = (
        100.0
        * region["gross_profit_cents"]
        / region["net_sales_cents"]
    )

    assert np.allclose(
        region["regional_gp_margin_pct"],
        expected,
        atol=0.0001,
        rtol=0,
    )


def test_investigation_fields_preserved(reporting_data):
    store = reporting_data["store_reporting"]
    priorities = reporting_data["investigation_priorities"]

    merged = store.merge(
        priorities[
            [
                "store_id",
                "month",
                "investigation_priority",
                "national_investigation_rank",
                "store_below_benchmark_streak",
            ]
        ],
        on=["store_id", "month"],
        suffixes=("_report", "_source"),
        validate="one_to_one",
    )

    for metric in [
        "investigation_priority",
        "national_investigation_rank",
        "store_below_benchmark_streak",
    ]:
        assert (
            merged[f"{metric}_report"]
            == merged[f"{metric}_source"]
        ).all()


def test_regional_trends_preserved(reporting_data):
    region = reporting_data["regional_reporting"]
    trends = reporting_data["profitability_trends"]

    merged = region.merge(
        trends[
            [
                "region",
                "month",
                "below_benchmark_streak",
                "rolling_3m_gp_margin_pct",
            ]
        ],
        on=["region", "month"],
        suffixes=("_report", "_source"),
        validate="one_to_one",
    )

    assert (
        merged["below_benchmark_streak_report"]
        == merged["below_benchmark_streak_source"]
    ).all()

    assert np.allclose(
        merged["rolling_3m_gp_margin_pct_report"],
        merged["rolling_3m_gp_margin_pct_source"],
        equal_nan=True,
    )


def test_reporting_required_fields(reporting_data):
    store = reporting_data["store_reporting"]
    region = reporting_data["regional_reporting"]

    store_required = [
        "store_id",
        "region",
        "month",
        "net_sales_cents",
        "gross_profit_cents",
        "investigation_priority",
    ]

    region_required = [
        "region",
        "month",
        "net_sales_cents",
        "gross_profit_cents",
        "regional_gp_margin_pct",
    ]

    assert not store[store_required].isna().any().any()
    assert not region[region_required].isna().any().any()


def test_store_counts_match_region(reporting_data):
    store = reporting_data["store_reporting"]
    region = reporting_data["regional_reporting"]

    counts = (
        store.groupby(["region", "month"])["store_id"]
        .nunique()
        .reset_index(name="actual_store_count")
    )

    merged = counts.merge(
        region[["region", "month", "store_count"]],
        on=["region", "month"],
        validate="one_to_one",
    )

    assert (
        merged["actual_store_count"]
        == merged["store_count"]
    ).all()
