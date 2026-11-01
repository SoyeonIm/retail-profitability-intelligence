
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
def data():
    con = duckdb.connect()

    views = [
        ("category_mart", "04_category_profitability.sql"),
        ("store_performance", "06_store_performance.sql"),
        ("regional_profitability", "07_regional_profitability.sql"),
        ("category_margin_drivers", "09_category_margin_drivers.sql"),
        ("profitability_trends", "11_profitability_trends.sql"),
        ("nz_benchmark_contribution", "13_nz_benchmark_contribution.sql"),
    ]

    try:
        for name, filename in views:
            con.execute(
                f"CREATE TEMP VIEW {name} AS "
                + read_sql(filename)
            )

        actual = con.execute(
            read_sql("14_investigation_priorities.sql")
        ).df()

        source = con.execute(
            "SELECT * FROM nz_benchmark_contribution"
        ).df()

        trends = con.execute(
            "SELECT * FROM profitability_trends"
        ).df()

        categories = con.execute(
            "SELECT * FROM category_margin_drivers"
        ).df()

    finally:
        con.close()

    return actual, source, trends, categories


def test_store_month_grain(data):
    actual, source, _, _ = data

    assert len(actual) == 1260
    assert len(actual) == len(source)
    assert actual["store_id"].nunique() == 60
    assert actual["region"].nunique() == 6
    assert actual["month"].nunique() == 21
    assert not actual.duplicated(
        ["store_id", "month"]
    ).any()


def test_financial_values_unchanged(data):
    actual, source, _, _ = data

    merged = actual.merge(
        source,
        on=["region", "month", "store_id"],
        suffixes=("_actual", "_source"),
        validate="one_to_one",
    )

    assert len(merged) == len(source)

    columns = [
        "net_sales_cents",
        "gross_profit_cents",
        "store_vs_nz_gap_pp",
        "contribution_to_region_gap_pp",
        "gp_shortfall_vs_nz_nzd",
    ]

    for col in columns:
        assert np.allclose(
            merged[f"{col}_actual"],
            merged[f"{col}_source"],
            atol=1e-8,
            rtol=0,
        )


def test_store_streaks_independently(data):
    actual, source, _, _ = data

    expected = source.sort_values(
        ["store_id", "month"]
    ).copy()

    def calculate_streak(group):
        streak = 0
        values = []

        for gap in group["store_vs_nz_gap_pp"]:
            streak = streak + 1 if gap < 0 else 0
            values.append(streak)

        group = group.copy()
        group["expected_streak"] = values
        return group

    expected = pd.concat(
        [
            calculate_streak(group)
            for _, group in expected.groupby("store_id")
        ],
        ignore_index=True,
    )

    merged = actual.merge(
        expected[[
            "store_id", "month", "expected_streak"
        ]],
        on=["store_id", "month"],
        validate="one_to_one",
    )

    assert (
        merged["store_below_benchmark_streak"]
        == merged["expected_streak"]
    ).all()


def test_regional_trend_mapping(data):
    actual, _, trends, _ = data

    merged = actual.merge(
        trends,
        on=["region", "month"],
        validate="many_to_one",
    )

    assert len(merged) == len(actual)

    mappings = {
        "region_benchmark_gap_pp": "benchmark_gap_pp",
        "region_mom_change_pp": "mom_margin_change_pp",
        "region_rolling_3m_margin_pct":
            "rolling_3m_gp_margin_pct",
        "region_below_benchmark_streak":
            "below_benchmark_streak",
    }

    for actual_col, source_col in mappings.items():
        assert np.allclose(
            merged[actual_col],
            merged[source_col],
            atol=1e-8,
            rtol=0,
            equal_nan=True,
        )


def test_category_context(data):
    actual, _, _, categories = data

    expected = (
        categories.sort_values(
            ["region", "month", "total_effect_pp", "category"]
        )
        .drop_duplicates(["region", "month"])
        [["region", "month", "category", "total_effect_pp"]]
    )

    merged = actual.merge(
        expected,
        on=["region", "month"],
        validate="many_to_one",
    )

    assert len(merged) == len(actual)

    assert (
        merged["top_negative_category"]
        == merged["category"]
    ).all()

    assert np.allclose(
        merged["category_effect_pp"],
        merged["total_effect_pp"],
        atol=1e-8,
        rtol=0,
    )


def test_national_ranking(data):
    actual, _, _, _ = data

    expected = actual.sort_values(
        [
            "month",
            "gp_shortfall_vs_nz_nzd",
            "store_id",
        ],
        ascending=[True, False, True],
    ).copy()

    expected["expected_rank"] = (
        expected.groupby("month").cumcount() + 1
    )

    assert (
        expected["national_investigation_rank"]
        == expected["expected_rank"]
    ).all()

    for _, group in actual.groupby("month"):
        assert sorted(
            group["national_investigation_rank"].tolist()
        ) == list(range(1, len(group) + 1))


def test_priority_rules(data):
    actual, _, _, _ = data

    below = actual["store_vs_nz_gap_pp"] < 0
    negative = actual["contribution_to_region_gap_pp"] < 0

    high = (
        below
        & negative
        & (actual["store_below_benchmark_streak"] >= 3)
        & (actual["region_below_benchmark_streak"] >= 3)
        & (actual["region_mom_change_pp"] < 0)
    )

    medium = below & negative

    expected = np.select(
        [high, medium],
        ["High", "Medium"],
        default="Monitor",
    )

    assert (
        actual["investigation_priority"].to_numpy()
        == expected
    ).all()


def test_priority_counts(data):
    actual, _, _, _ = data

    counts = actual["investigation_priority"].value_counts()

    assert counts.get("High", 0) == 19
    assert counts.get("Medium", 0) == 612
    assert counts.get("Monitor", 0) == 629


def test_no_invalid_streaks(data):
    actual, _, _, _ = data

    assert (
        actual["store_below_benchmark_streak"] >= 0
    ).all()

    above = actual["store_vs_nz_gap_pp"] >= 0

    assert (
        actual.loc[
            above, "store_below_benchmark_streak"
        ] == 0
    ).all()


def test_september_reference_cases(data):
    actual, _, _, _ = data

    september = actual[
        actual["month"].astype(str) == "2026-09-01"
    ].set_index("store_id")

    assert september.loc[
        "S044", "national_investigation_rank"
    ] == 1

    assert september.loc[
        "S037", "store_below_benchmark_streak"
    ] == 2

    assert september.loc[
        "S037", "investigation_priority"
    ] == "Medium"

    assert september.loc[
        "S007", "store_below_benchmark_streak"
    ] == 5

    assert september.loc[
        "S043", "store_below_benchmark_streak"
    ] == 8

    assert september.loc[
        "S007", "investigation_priority"
    ] == "High"

    assert september.loc[
        "S043", "investigation_priority"
    ] == "High"


def test_required_fields(data):
    actual, _, _, _ = data

    required = [
        "region",
        "month",
        "store_id",
        "net_sales_cents",
        "gross_profit_cents",
        "store_vs_nz_gap_pp",
        "gp_shortfall_vs_nz_nzd",
        "store_below_benchmark_streak",
        "national_investigation_rank",
        "investigation_priority",
    ]

    assert not actual[required].isna().any().any()
