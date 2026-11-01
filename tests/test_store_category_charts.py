
import pandas as pd
import pytest

from src.reporting_data import load_category_reporting_data
from src.dashboard_metrics import calculate_store_category_metrics
from src.dashboard_charts import (
    store_category_mix_chart,
    store_category_margin_chart,
)


@pytest.fixture
def category_metrics():
    category = load_category_reporting_data()

    selected = category.loc[
        (category["store_id"] == "S044")
        & (
            pd.to_datetime(category["month"])
            == pd.Timestamp("2026-09-01")
        )
    ].copy()

    return calculate_store_category_metrics(selected)


def test_category_charts_have_expected_series(category_metrics):
    mix_fig = store_category_mix_chart(category_metrics)
    margin_fig = store_category_margin_chart(category_metrics)

    assert len(mix_fig.data) == 2
    assert len(margin_fig.data) == 1
    assert len(mix_fig.data[0].x) == 6
    assert len(margin_fig.data[0].x) == 6


def test_category_mix_reconciles_to_100_percent(category_metrics):
    assert category_metrics["sales_mix_pct"].sum() == pytest.approx(100)
    assert category_metrics["gp_contribution_pct"].sum() == pytest.approx(100)


def test_category_chart_matches_source_data(category_metrics):
    mix_fig = store_category_mix_chart(category_metrics)
    margin_fig = store_category_margin_chart(category_metrics)

    assert list(mix_fig.data[0].y) == pytest.approx(
        category_metrics["sales_mix_pct"].tolist()
    )
    assert list(mix_fig.data[1].y) == pytest.approx(
        category_metrics["gp_contribution_pct"].tolist()
    )
    assert list(margin_fig.data[0].y) == pytest.approx(
        category_metrics["gp_margin_pct"].tolist()
    )


def test_category_charts_reject_empty_data(category_metrics):
    empty = category_metrics.iloc[0:0]

    with pytest.raises(ValueError, match="empty"):
        store_category_mix_chart(empty)

    with pytest.raises(ValueError, match="empty"):
        store_category_margin_chart(empty)


def test_category_charts_reject_duplicate_categories(category_metrics):
    duplicated = pd.concat(
        [category_metrics, category_metrics.iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="Duplicate"):
        store_category_mix_chart(duplicated)

    with pytest.raises(ValueError, match="Duplicate"):
        store_category_margin_chart(duplicated)


def test_category_charts_reject_missing_columns(category_metrics):
    with pytest.raises(ValueError, match="Missing required columns"):
        store_category_mix_chart(
            category_metrics.drop(columns=["sales_mix_pct"])
        )

    with pytest.raises(ValueError, match="Missing required columns"):
        store_category_margin_chart(
            category_metrics.drop(columns=["gp_margin_pct"])
        )
