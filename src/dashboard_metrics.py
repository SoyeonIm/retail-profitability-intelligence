
"""Reusable financial metrics for the retail dashboard."""

import pandas as pd


def calculate_monthly_kpis(store: pd.DataFrame) -> pd.DataFrame:
    """Aggregate store reporting data into monthly NZ KPIs."""

    required_columns = {
        "month",
        "store_id",
        "net_sales_cents",
        "gross_profit_cents",
    }

    missing = required_columns - set(store.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if store.empty:
        raise ValueError("Store reporting data is empty.")

    if store.duplicated(["store_id", "month"]).any():
        raise ValueError("Duplicate store-month keys detected.")

    monthly = (
        store.groupby("month", as_index=False)
        .agg(
            net_sales_cents=("net_sales_cents", "sum"),
            gross_profit_cents=("gross_profit_cents", "sum"),
            store_count=("store_id", "nunique"),
        )
        .sort_values("month")
        .reset_index(drop=True)
    )

    if (monthly["net_sales_cents"] <= 0).any():
        raise ValueError(
            "Monthly net sales must be positive to calculate GP margin."
        )

    monthly["net_sales_nzd"] = (
        monthly["net_sales_cents"] / 100
    )

    monthly["gross_profit_nzd"] = (
        monthly["gross_profit_cents"] / 100
    )

    monthly["gp_margin_pct"] = (
        monthly["gross_profit_cents"]
        / monthly["net_sales_cents"]
        * 100
    )

    monthly["sales_mom_pct"] = (
        monthly["net_sales_cents"].pct_change() * 100
    )

    monthly["gp_mom_pct"] = (
        monthly["gross_profit_cents"].pct_change() * 100
    )

    monthly["margin_mom_pp"] = (
        monthly["gp_margin_pct"].diff()
    )

    monthly["stores_mom_change"] = (
        monthly["store_count"].diff()
    )

    return monthly
