
from pathlib import Path

import duckdb
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def marts():
    def read_sql(filename):
        return (
            ROOT / "sql" / filename
        ).read_text(encoding="utf-8").strip().rstrip(";")

    con = duckdb.connect()

    try:
        con.execute(
            "CREATE TEMP VIEW category_mart AS "
            + read_sql("04_category_profitability.sql")
        )

        con.execute(
            "CREATE TEMP VIEW store_performance AS "
            + read_sql("06_store_performance.sql")
        )

        regional = con.execute(
            read_sql("07_regional_profitability.sql")
        ).df()

        decomposition = con.execute(
            read_sql("08_regional_margin_decomposition.sql")
        ).df()

        stores = con.execute(
            "SELECT * FROM read_csv_auto('data/raw/stores.csv')"
        ).df()

    finally:
        con.close()

    return regional, decomposition, stores


def test_store_dimension_has_unique_keys(marts):
    _, _, stores = marts

    assert not stores["store_id"].isna().any()
    assert not stores["store_id"].duplicated().any()


def test_decomposition_grain(marts):
    _, result, _ = marts

    assert len(result) == 126
    assert result["region"].nunique() == 6
    assert result["month"].nunique() == 21

    assert not result.duplicated(
        ["region", "month"]
    ).any()


def test_financial_totals_match_regional_mart(marts):
    regional, decomposition, _ = marts

    expected = regional[
        [
            "region",
            "month",
            "net_sales_cents",
            "gross_profit_cents",
        ]
    ]

    comparison = decomposition.merge(
        expected,
        on=["region", "month"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    assert (comparison["_merge"] == "both").all()

    assert (
        comparison["region_sales_cents"]
        == comparison["net_sales_cents"]
    ).all()

    assert (
        comparison["region_gp_cents"]
        == comparison["gross_profit_cents"]
    ).all()


def test_margins_match_regional_mart(marts):
    regional, decomposition, _ = marts

    comparison = decomposition.merge(
        regional[
            [
                "region",
                "month",
                "regional_gp_margin_pct",
                "nz_gp_margin_pct",
            ]
        ],
        on=["region", "month"],
        how="outer",
        validate="one_to_one",
        suffixes=("", "_regional"),
        indicator=True,
    )

    assert (comparison["_merge"] == "both").all()

    assert np.allclose(
        comparison["regional_gp_margin_pct"],
        comparison["regional_gp_margin_pct_regional"],
        atol=0.0000001,
        rtol=0,
    )

    assert np.allclose(
        comparison["benchmark_gp_margin_pct"],
        comparison["nz_gp_margin_pct"],
        atol=0.0000001,
        rtol=0,
    )


def test_effects_explain_actual_gap(marts):
    _, result, _ = marts

    assert np.allclose(
        result["explained_gap_pp"],
        result["actual_gap_pp"],
        atol=0.000001,
        rtol=0,
    )

    assert np.allclose(
        result["mix_effect_pp"]
        + result["margin_effect_pp"],
        result["explained_gap_pp"],
        atol=0.000002,
        rtol=0,
    )


def test_gap_matches_unrounded_financials(marts):
    _, result, _ = marts

    expected = 100.0 * (
        result["region_gp_cents"]
        / result["region_sales_cents"]
        -
        result["benchmark_total_gp_cents"]
        / result["benchmark_total_sales_cents"]
    )

    assert np.allclose(
        result["actual_gap_pp"],
        expected,
        atol=0.00000051,
        rtol=0,
    )


def test_reconciliation_residual(marts):
    _, result, _ = marts

    assert np.isfinite(
        result["reconciliation_residual_pp"]
    ).all()

    assert (
        result["reconciliation_residual_pp"]
        .abs()
        .max()
        <= 0.00000001
    )


def test_no_missing_decomposition_values(marts):
    _, result, _ = marts

    columns = [
        "region_sales_cents",
        "region_gp_cents",
        "benchmark_total_sales_cents",
        "benchmark_total_gp_cents",
        "mix_effect_pp",
        "margin_effect_pp",
        "explained_gap_pp",
        "actual_gap_pp",
        "reconciliation_residual_pp",
    ]

    assert result[columns].notna().all().all()
    assert (result["region_sales_cents"] > 0).all()
    assert (result["benchmark_total_sales_cents"] > 0).all()
