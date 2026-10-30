
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_sql_store_month_reconciliation():
    transactions = pd.read_csv(
        ROOT / "data/raw/transactions.csv",
        dtype={"store_id": "string"},
    )

    transactions["month"] = (
        pd.to_datetime(transactions["transaction_date"])
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    expected = (
        transactions.groupby(["store_id", "month"], as_index=False)
        .agg(
            net_sales_cents=("net_sales_cents", "sum"),
            cogs_cents=("cogs_cents", "sum"),
        )
    )

    sql = (
        ROOT / "sql/03_transaction_reconciliation.sql"
    ).read_text(encoding="utf-8")

    con = duckdb.connect()
    try:
        actual = con.execute(sql).df()
    finally:
        con.close()

    actual["month"] = pd.to_datetime(actual["month"])

    # Check the uniqueness of the store-month grain.
    assert not actual.duplicated(["store_id", "month"]).any()

    # Check the number of store-month groups.
    assert len(actual) == len(expected)

    # Compare every store-month, not just the overall total.
    merged = expected.merge(
        actual,
        on=["store_id", "month"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    assert (merged["_merge"] == "both").all()

    # SQL outputs NZD; compare back in integer cents.
    actual_sales_cents = (
        merged["net_sales_nzd"] * 100
    ).round().astype("int64")

    actual_cogs_cents = (
        merged["cogs_nzd"] * 100
    ).round().astype("int64")

    assert (
        actual_sales_cents == merged["net_sales_cents"]
    ).all()

    assert (
        actual_cogs_cents == merged["cogs_cents"]
    ).all()
