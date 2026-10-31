from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_marts():
    """Build the category mart and run the margin decomposition SQL."""

    category_sql = (
        ROOT / "sql/04_category_profitability.sql"
    ).read_text(encoding="utf-8").strip().rstrip(";")

    decomposition_sql = (
        ROOT / "sql/05_margin_decomposition.sql"
    ).read_text(encoding="utf-8")

    con = duckdb.connect()

    try:
        con.execute(
            f"CREATE TEMP VIEW category_mart AS {category_sql}"
        )

        category_mart = con.execute(
            "SELECT * FROM category_mart"
        ).df()

        decomposition = con.execute(
            decomposition_sql
        ).df()

    finally:
        con.close()

    category_mart["month"] = pd.to_datetime(
        category_mart["month"]
    )

    decomposition["month"] = pd.to_datetime(
        decomposition["month"]
    )

    return category_mart, decomposition


def test_decomposition_has_unique_store_month_grain():
    _, result = load_marts()

    assert len(result) == 1260

    assert not result.duplicated(
        ["store_id", "month"]
    ).any()

    assert result["store_id"].nunique() == 60

    assert result["month"].nunique() == 21


def test_store_financial_totals_match_category_mart():
    category_mart, result = load_marts()

    expected = (
        category_mart.groupby(
            ["store_id", "month"],
            as_index=False,
        )
        .agg(
            expected_sales_cents=(
                "net_sales_cents", "sum"
            ),
            expected_gp_cents=(
                "gross_profit_cents", "sum"
            ),
        )
    )

    actual = result.merge(
        expected,
        on=["store_id", "month"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    assert (actual["_merge"] == "both").all()

    assert (
        actual["store_sales_cents"]
        == actual["expected_sales_cents"]
    ).all()

    assert (
        actual["store_gp_cents"]
        == actual["expected_gp_cents"]
    ).all()


def test_benchmark_margin_matches_all_store_weighted_margin():
    category_mart, result = load_marts()

    expected = (
        category_mart.groupby("month", as_index=False)
        .agg(
            total_sales_cents=("net_sales_cents", "sum"),
            total_gp_cents=("gross_profit_cents", "sum"),
        )
    )

    expected["expected_benchmark_margin_pct"] = (
        100.0
        * expected["total_gp_cents"]
        / expected["total_sales_cents"]
    )

    actual = result[
        ["month", "benchmark_gp_margin_pct"]
    ].drop_duplicates()

    comparison = actual.merge(
        expected[
            ["month", "expected_benchmark_margin_pct"]
        ],
        on="month",
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    assert (comparison["_merge"] == "both").all()

    assert np.allclose(
        comparison["benchmark_gp_margin_pct"],
        comparison["expected_benchmark_margin_pct"],
        atol=0.000051,
        rtol=0,
    )


def test_mix_and_margin_effects_reconcile_to_actual_gap():
    _, result = load_marts()

    # The unrounded decomposition must match the actual margin gap.
    assert np.allclose(
        result["explained_gap_pp"],
        result["actual_gap_pp"],
        atol=0.000001,
        rtol=0,
    )

    # The displayed effects are independently rounded to 6 decimals.
    # Allow a small rounding tolerance when adding the displayed values.
    calculated_gap = (
        result["mix_effect_pp"]
        + result["margin_effect_pp"]
    )

    assert np.allclose(
        calculated_gap,
        result["explained_gap_pp"],
        atol=0.000002,
        rtol=0,
    )


def test_reconciliation_residual_is_within_tolerance():
    _, result = load_marts()

    assert np.isfinite(
        result["reconciliation_residual_pp"]
    ).all()

    assert (
        result["reconciliation_residual_pp"]
        .abs()
        .max()
        <= 0.00000001
    )