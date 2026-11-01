
import pandas as pd
import pytest

from src.reporting_data import load_reporting_data
from src.dashboard_charts import investigation_priority_chart


@pytest.fixture
def september_store_data():
    store = load_reporting_data()["store"].copy()
    store["month"] = pd.to_datetime(store["month"])

    selected = store[
        store["month"] == pd.Timestamp("2026-09-01")
    ].copy()

    assert len(selected) == 60
    return selected


def test_chart_contains_top_10_stores(september_store_data):
    fig = investigation_priority_chart(september_store_data)

    assert len(fig.data) == 1
    assert len(fig.data[0].x) == 10


def test_chart_matches_validated_september_values(
    september_store_data,
):
    fig = investigation_priority_chart(september_store_data)

    chart_values = list(fig.data[0].x)
    chart_stores = list(fig.data[0].y)

    assert max(chart_values) == pytest.approx(136.69)
    assert chart_stores[-1] == "S044"


def test_chart_rejects_duplicate_stores(september_store_data):
    duplicated = pd.concat(
        [
            september_store_data,
            september_store_data.iloc[[0]],
        ],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="Duplicate stores"):
        investigation_priority_chart(duplicated)


def test_chart_rejects_missing_columns(september_store_data):
    invalid = september_store_data.drop(
        columns=["gp_shortfall_vs_nz_nzd"]
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        investigation_priority_chart(invalid)


def test_chart_rejects_empty_data(september_store_data):
    empty = september_store_data.iloc[0:0]

    with pytest.raises(ValueError, match="empty"):
        investigation_priority_chart(empty)


def test_chart_rejects_unknown_priority(september_store_data):
    invalid = september_store_data.copy()
    invalid.loc[
        invalid["store_id"] == "S044",
        "investigation_priority",
    ] = "Unknown"

    with pytest.raises(
        ValueError,
        match="Unknown investigation priority",
    ):
        investigation_priority_chart(invalid)
