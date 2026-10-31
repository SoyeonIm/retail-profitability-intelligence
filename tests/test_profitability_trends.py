
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]


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
        con.execute(
            "CREATE TEMP VIEW store_performance AS "
            + sql("06_store_performance.sql")
        )
        con.execute(
            "CREATE TEMP VIEW regional_profitability AS "
            + sql("07_regional_profitability.sql")
        )

        trends = con.execute(
            sql("11_profitability_trends.sql")
        ).df()

        regional = con.execute(
            "SELECT * FROM regional_profitability"
        ).df()

    finally:
        con.close()

    trends["month"] = pd.to_datetime(trends["month"])
    regional["month"] = pd.to_datetime(regional["month"])

    return trends, regional


def test_trend_grain(data):
    trends, _ = data

    assert len(trends) == 126
    assert trends["region"].nunique() == 6
    assert trends["month"].nunique() == 21
    assert not trends.duplicated(
        ["region", "month"]
    ).any()


def test_months_are_contiguous(data):
    trends, _ = data

    for _, group in trends.groupby("region"):
        months = sorted(group["month"])
        expected = pd.date_range(
            start=months[0],
            periods=len(months),
            freq="MS",
        )
        assert list(months) == list(expected)


def test_financial_totals(data):
    trends, regional = data

    check = trends.merge(
        regional[
            [
                "region",
                "month",
                "net_sales_cents",
                "gross_profit_cents",
            ]
        ],
        on=["region", "month"],
        how="outer",
        validate="one_to_one",
        indicator=True,
        suffixes=("_trend", "_regional"),
    )

    assert (check["_merge"] == "both").all()
    assert (
        check["net_sales_cents_trend"]
        == check["net_sales_cents_regional"]
    ).all()
    assert (
        check["gross_profit_cents_trend"]
        == check["gross_profit_cents_regional"]
    ).all()


def test_monthly_margin(data):
    trends, _ = data

    expected = (
        100.0
        * trends["gross_profit_cents"]
        / trends["net_sales_cents"]
    )

    assert np.allclose(
        trends["gp_margin_pct"],
        expected,
        atol=0.00000051,
        rtol=0,
    )


def test_nz_benchmark(data):
    trends, _ = data

    benchmark = trends.groupby("month").agg(
        sales=("net_sales_cents", "sum"),
        gp=("gross_profit_cents", "sum"),
    )

    benchmark["expected"] = (
        100.0 * benchmark["gp"] / benchmark["sales"]
    )

    check = trends.merge(
        benchmark[["expected"]],
        left_on="month",
        right_index=True,
        validate="many_to_one",
    )

    assert np.allclose(
        check["nz_gp_margin_pct"],
        check["expected"],
        atol=0.00000051,
        rtol=0,
    )


def test_mom_and_yoy(data):
    trends, _ = data

    ordered = trends.sort_values(
        ["region", "month"]
    ).copy()

    raw_margin = (
        100.0
        * ordered["gross_profit_cents"]
        / ordered["net_sales_cents"]
    )

    expected_mom = raw_margin - raw_margin.groupby(
        ordered["region"]
    ).shift(1)

    expected_yoy = raw_margin - raw_margin.groupby(
        ordered["region"]
    ).shift(12)

    assert np.allclose(
        ordered["mom_margin_change_pp"],
        expected_mom,
        atol=0.00000051,
        rtol=0,
        equal_nan=True,
    )

    assert np.allclose(
        ordered["yoy_margin_change_pp"],
        expected_yoy,
        atol=0.00000051,
        rtol=0,
        equal_nan=True,
    )


def test_rolling_three_months(data):
    trends, _ = data

    ordered = trends.sort_values(
        ["region", "month"]
    ).copy()

    rolling_sales = ordered.groupby(
        "region"
    )["net_sales_cents"].transform(
        lambda x: x.rolling(3, min_periods=3).sum()
    )

    rolling_gp = ordered.groupby(
        "region"
    )["gross_profit_cents"].transform(
        lambda x: x.rolling(3, min_periods=3).sum()
    )

    expected_margin = (
        100.0 * rolling_gp / rolling_sales
    )

    assert np.allclose(
        ordered["rolling_3m_gp_margin_pct"],
        expected_margin,
        atol=0.00000051,
        rtol=0,
        equal_nan=True,
    )

    assert np.allclose(
        ordered.loc[
            expected_margin.notna(),
            "rolling_3m_sales_cents",
        ],
        rolling_sales.dropna(),
        rtol=0,
        atol=0,
    )

    assert np.allclose(
        ordered.loc[
            expected_margin.notna(),
            "rolling_3m_gp_cents",
        ],
        rolling_gp.dropna(),
        rtol=0,
        atol=0,
    )


def test_benchmark_gap(data):
    trends, _ = data

    raw_nz = trends.groupby("month").agg(
        sales=("net_sales_cents", "sum"),
        gp=("gross_profit_cents", "sum"),
    )
    raw_nz["margin"] = (
        100.0 * raw_nz["gp"] / raw_nz["sales"]
    )

    check = trends.merge(
        raw_nz[["margin"]],
        left_on="month",
        right_index=True,
        validate="many_to_one",
    )

    expected_gap = (
        100.0
        * check["gross_profit_cents"]
        / check["net_sales_cents"]
        - check["margin"]
    )

    assert np.allclose(
        check["benchmark_gap_pp"],
        expected_gap,
        atol=0.00000051,
        rtol=0,
    )


def test_below_benchmark_streak(data):
    trends, _ = data

    for _, group in trends.groupby("region"):
        group = group.sort_values("month")
        streak = 0

        for _, row in group.iterrows():
            if row["below_nz_benchmark"] == 1:
                streak += 1
            else:
                streak = 0

            assert row["below_benchmark_streak"] == streak


def test_expected_nulls(data):
    trends, _ = data

    assert trends["mom_margin_change_pp"].isna().sum() == 6
    assert trends["yoy_margin_change_pp"].isna().sum() == 72
    assert (
        trends["rolling_3m_gp_margin_pct"].isna().sum()
        == 12
    )


def test_no_missing_financials(data):
    trends, _ = data

    columns = [
        "net_sales_cents",
        "gross_profit_cents",
        "gp_margin_pct",
        "nz_gp_margin_pct",
        "benchmark_gap_pp",
        "below_nz_benchmark",
        "below_benchmark_streak",
    ]

    assert trends[columns].notna().all().all()
    assert (trends["net_sales_cents"] > 0).all()
    assert trends["below_nz_benchmark"].isin([0, 1]).all()
