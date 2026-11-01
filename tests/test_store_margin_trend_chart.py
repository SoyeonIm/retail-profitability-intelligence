
import pandas as pd
import pytest

from src.reporting_data import load_reporting_data
from src.dashboard_charts import store_margin_trend_chart


@pytest.fixture
def store_history():
    store = load_reporting_data()["store"].copy()
    store["month"] = pd.to_datetime(store["month"])

    selected = store.loc[
        store["store_id"] == "S044"
    ].sort_values("month").copy()

    assert len(selected) == 21
    return selected


def test_chart_contains_three_series(store_history):
    fig = store_margin_trend_chart(store_history)

    assert len(fig.data) == 3
    assert len(fig.data[0].x) == 21


def test_chart_matches_validated_september_margin(store_history):
    fig = store_margin_trend_chart(store_history)

    september = store_history.iloc[-1]

    assert fig.data[0].y[-1] == pytest.approx(
        september["gp_margin_pct"]
    )

    assert fig.data[1].y[-1] == pytest.approx(
        september["region_gp_margin_pct"]
    )

    assert fig.data[2].y[-1] == pytest.approx(
        september["nz_gp_margin_pct"]
    )


def test_chart_rejects_duplicate_months(store_history):
    duplicated = pd.concat(
        [store_history, store_history.iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="Duplicate"):
        store_margin_trend_chart(duplicated)


def test_chart_rejects_multiple_stores(store_history):
    invalid = store_history.copy()
    invalid.loc[invalid.index[0], "store_id"] = "S999"

    with pytest.raises(ValueError, match="one store"):
        store_margin_trend_chart(invalid)


def test_chart_rejects_missing_columns(store_history):
    invalid = store_history.drop(
        columns=["nz_gp_margin_pct"]
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        store_margin_trend_chart(invalid)


def test_chart_rejects_empty_data(store_history):
    empty = store_history.iloc[0:0]

    with pytest.raises(ValueError, match="empty"):
        store_margin_trend_chart(empty)
