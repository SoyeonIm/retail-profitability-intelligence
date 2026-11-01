
"""Financial validation tests for the MarginIQ store heatmap."""

import pandas as pd
import pytest

from src.dashboard_metrics import prepare_store_margin_heatmap


def sample_store_data():
    """Small synthetic dataset with independently checkable values."""
    rows = [
        # S001: below benchmark in both months.
        ("S001", "Auckland", "2026-08-01", 10000, 3000, 30.0, 32.0),
        ("S001", "Auckland", "2026-09-01", 20000, 6000, 30.0, 34.0),

        # S002: above benchmark in August, below in September.
        ("S002", "Waikato", "2026-08-01", 10000, 3500, 35.0, 32.0),
        ("S002", "Waikato", "2026-09-01", 10000, 3100, 31.0, 34.0),
    ]

    data = pd.DataFrame(
        rows,
        columns=[
            "store_id",
            "region",
            "month",
            "net_sales_cents",
            "gross_profit_cents",
            "gp_margin_pct",
            "nz_gp_margin_pct",
        ],
    )

    data["store_vs_nz_gap_pp"] = (
        data["gp_margin_pct"] - data["nz_gp_margin_pct"]
    )

    return data


def test_heatmap_has_unique_store_month_keys():
    data = prepare_store_margin_heatmap(
        sample_store_data(),
        end_month="2026-09-01",
    )

    assert len(data) == 4
    assert not data.duplicated(["store_id", "month"]).any()


def test_heatmap_excludes_future_months():
    data = prepare_store_margin_heatmap(
        sample_store_data(),
        end_month="2026-08-01",
    )

    assert len(data) == 2
    assert data["month"].max() == pd.Timestamp("2026-08-01")


def test_heatmap_rejects_incorrect_margin_gap():
    data = sample_store_data()
    data.loc[0, "store_vs_nz_gap_pp"] = -99.0

    with pytest.raises(ValueError, match="does not reconcile"):
        prepare_store_margin_heatmap(
            data,
            end_month="2026-09-01",
        )


def test_weighted_period_gap_calculation():
    data = sample_store_data()
    data["benchmark_gp_cents"] = (
        data["net_sales_cents"]
        * data["nz_gp_margin_pct"] / 100
    )

    summary = data.groupby("store_id").agg(
        total_sales=("net_sales_cents", "sum"),
        total_gp=("gross_profit_cents", "sum"),
        benchmark_gp=("benchmark_gp_cents", "sum"),
    )

    summary["period_gap_pp"] = (
        100
        * (summary["total_gp"] - summary["benchmark_gp"])
        / summary["total_sales"]
    )

    # S001:
    # Actual GP = 9000 cents
    # Benchmark GP = 3200 + 6800 = 10000 cents
    # Period gap = (9000 - 10000) / 30000 * 100
    assert summary.loc["S001", "period_gap_pp"] == pytest.approx(
        -3.3333333333
    )

    # S002:
    # Actual GP = 6600 cents
    # Benchmark GP = 3200 + 3400 = 6600 cents
    assert summary.loc["S002", "period_gap_pp"] == pytest.approx(0.0)


def test_persistent_underperformer_count():
    data = sample_store_data()

    months_in_period = data["month"].nunique()

    persistent = data.groupby("store_id")["store_vs_nz_gap_pp"].apply(
        lambda gaps: (
            len(gaps) == months_in_period
            and (gaps < 0).all()
        )
    )

    assert int(persistent.sum()) == 1
    assert persistent.loc["S001"]
    assert not persistent.loc["S002"]


def test_potential_gp_shortfall():
    data = sample_store_data()

    data["benchmark_gp_cents"] = (
        data["net_sales_cents"]
        * data["nz_gp_margin_pct"] / 100
    )

    summary = data.groupby("store_id").agg(
        actual_gp=("gross_profit_cents", "sum"),
        benchmark_gp=("benchmark_gp_cents", "sum"),
    )

    shortfall_nzd = (
        (summary["benchmark_gp"] - summary["actual_gp"])
        .clip(lower=0)
        .sum()
        / 100
    )

    # S001: NZ$10 shortfall; S002: NZ$0.
    assert shortfall_nzd == pytest.approx(10.0)


def test_region_filter_excludes_other_regions():
    data = sample_store_data()

    filtered = data.loc[
        data["region"].isin(["Auckland"])
    ]

    assert set(filtered["store_id"]) == {"S001"}
    assert set(filtered["region"]) == {"Auckland"}


def test_actual_snapshot_function():
    """Verify the production KPI function against known sample results."""
    from src.dashboard_metrics import (
        calculate_heatmap_performance_snapshot,
    )

    data = sample_store_data()

    snapshot = calculate_heatmap_performance_snapshot(data)

    assert snapshot["store_count"] == 2
    assert snapshot["month_count"] == 2

    # September: both stores are below the NZ benchmark.
    assert snapshot["stores_below_benchmark"] == 2

    # Only S001 is below benchmark in both months.
    assert snapshot["persistent_underperformers"] == 1

    # S001 has NZ$10 shortfall; S002 has no period shortfall.
    assert snapshot["potential_gp_shortfall_nzd"] == pytest.approx(
        10.0
    )