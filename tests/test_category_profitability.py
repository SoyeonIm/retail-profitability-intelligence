
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_data():
    transactions = pd.read_csv(
        ROOT / "data/raw/transactions.csv"
    )
    products = pd.read_csv(
        ROOT / "data/raw/products.csv"
    )

    sql = (
        ROOT / "sql/04_category_profitability.sql"
    ).read_text(encoding="utf-8")

    con = duckdb.connect()
    try:
        mart = con.execute(sql).df()
    finally:
        con.close()

    return transactions, products, mart


def test_product_references_and_unique_grain():
    transactions, products, mart = load_data()

    assert products["product_id"].is_unique

    assert transactions["product_id"].isin(
        products["product_id"]
    ).all()

    assert not mart.duplicated(
        ["store_id", "month", "category"]
    ).any()


def test_category_mart_financial_reconciliation():
    transactions, products, mart = load_data()

    transactions["month"] = (
        pd.to_datetime(transactions["transaction_date"])
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    enriched = transactions.merge(
        products[["product_id", "category"]],
        on="product_id",
        how="left",
        validate="many_to_one",
    )

    expected = (
        enriched.groupby(
            ["store_id", "month", "category"],
            as_index=False,
        )
        .agg(
            net_sales_cents=("net_sales_cents", "sum"),
            cogs_cents=("cogs_cents", "sum"),
        )
    )

    mart["month"] = pd.to_datetime(mart["month"])

    actual = expected.merge(
        mart,
        on=["store_id", "month", "category"],
        how="outer",
        validate="one_to_one",
        indicator=True,
        suffixes=("_expected", "_actual"),
    )

    assert (actual["_merge"] == "both").all()

    for metric in ["net_sales_cents", "cogs_cents"]:
        assert (
            actual[f"{metric}_expected"]
            == actual[f"{metric}_actual"]
        ).all()

    assert (
        actual["gross_profit_cents"]
        == actual["net_sales_cents_actual"]
        - actual["cogs_cents_actual"]
    ).all()
