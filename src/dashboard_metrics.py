
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


def calculate_store_category_metrics(
    category_data: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate category mix and GP contribution for one store-month."""

    required = {
        "store_id",
        "month",
        "category",
        "net_sales_cents",
        "cogs_cents",
        "gross_profit_cents",
    }

    missing = required - set(category_data.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if category_data.empty:
        raise ValueError("Category data is empty.")

    if category_data["store_id"].nunique() != 1:
        raise ValueError("Expected one store.")

    if pd.to_datetime(category_data["month"]).nunique() != 1:
        raise ValueError("Expected one reporting month.")

    if category_data["category"].isna().any():
        raise ValueError("Missing category values.")

    if category_data["category"].duplicated().any():
        raise ValueError("Duplicate categories.")

    result = category_data.copy()

    monetary_columns = [
        "net_sales_cents",
        "cogs_cents",
        "gross_profit_cents",
    ]

    if result[monetary_columns].isna().any().any():
        raise ValueError("Missing financial values.")

    if not (
        result["net_sales_cents"] - result["cogs_cents"]
        == result["gross_profit_cents"]
    ).all():
        raise ValueError("Category GP reconciliation failed.")

    total_sales = result["net_sales_cents"].sum()
    total_gp = result["gross_profit_cents"].sum()

    if total_sales <= 0:
        raise ValueError("Store net sales must be positive.")

    result["net_sales_nzd"] = (
        result["net_sales_cents"] / 100
    )

    result["gross_profit_nzd"] = (
        result["gross_profit_cents"] / 100
    )

    result["sales_mix_pct"] = (
        100 * result["net_sales_cents"] / total_sales
    )

    result["gp_margin_pct"] = (
        100
        * result["gross_profit_cents"]
        / result["net_sales_cents"].replace(0, float("nan"))
    )

    result["gp_contribution_pct"] = (
        100 * result["gross_profit_cents"] / total_gp
        if total_gp != 0
        else float("nan")
    )

    return result.sort_values(
        "net_sales_cents",
        ascending=False,
    ).reset_index(drop=True)


def prepare_store_margin_heatmap(
    store_data: pd.DataFrame,
    end_month,
) -> pd.DataFrame:
    """Prepare validated store-month NZ benchmark variances."""

    required = {
        "store_id",
        "month",
        "gp_margin_pct",
        "nz_gp_margin_pct",
        "store_vs_nz_gap_pp",
    }

    missing = required - set(store_data.columns)

    if missing:
        raise ValueError(
            f"Missing heatmap columns: {sorted(missing)}"
        )

    if store_data.empty:
        raise ValueError("Store reporting data is empty.")

    result = store_data.copy()
    result["month"] = pd.to_datetime(result["month"])
    cutoff = pd.Timestamp(end_month)

    if result[list(required)].isna().any().any():
        raise ValueError("Heatmap contains missing values.")

    if result.duplicated(["store_id", "month"]).any():
        raise ValueError("Duplicate store-month records.")

    result = result.loc[
        result["month"] <= cutoff
    ].copy()

    if result.empty:
        raise ValueError(
            "No reporting data available before selected month."
        )

    expected_gap = (
        result["gp_margin_pct"]
        - result["nz_gp_margin_pct"]
    )

    if not (
        (expected_gap - result["store_vs_nz_gap_pp"])
        .abs()
        .le(0.0001)
    ).all():
        raise ValueError(
            "Store margin variance does not reconcile."
        )

    return result.sort_values(
        ["store_id", "month"]
    ).reset_index(drop=True)


def calculate_heatmap_performance_snapshot(
    heatmap_data: pd.DataFrame,
) -> dict:
    """Calculate KPIs for the selected store-month heatmap data."""

    required = {
        "store_id",
        "month",
        "net_sales_cents",
        "gross_profit_cents",
        "nz_gp_margin_pct",
        "store_vs_nz_gap_pp",
    }

    missing = required - set(heatmap_data.columns)
    if missing:
        raise ValueError(
            f"Missing snapshot columns: {sorted(missing)}"
        )

    if heatmap_data.empty:
        raise ValueError("Heatmap snapshot data is empty.")

    data = heatmap_data.copy()
    data["month"] = pd.to_datetime(data["month"])

    if data[list(required)].isna().any().any():
        raise ValueError("Snapshot contains missing values.")

    if data.duplicated(["store_id", "month"]).any():
        raise ValueError("Duplicate store-month records.")

    if (data["net_sales_cents"] <= 0).any():
        raise ValueError("Store net sales must be positive.")

    latest_month = data["month"].max()

    latest_data = data.loc[
        data["month"] == latest_month
    ]

    stores_below_benchmark = int(
        (latest_data["store_vs_nz_gap_pp"] < 0).sum()
    )

    months_in_period = data["month"].nunique()

    persistent_underperformers = int(
        data.groupby("store_id")["store_vs_nz_gap_pp"]
        .apply(
            lambda gaps: (
                len(gaps) == months_in_period
                and (gaps < 0).all()
            )
        )
        .sum()
    )

    data["benchmark_gp_cents"] = (
        data["net_sales_cents"]
        * data["nz_gp_margin_pct"]
        / 100
    )

    store_gp_gaps = data.groupby("store_id").agg(
        actual_gp=("gross_profit_cents", "sum"),
        benchmark_gp=("benchmark_gp_cents", "sum"),
    )

    potential_gp_shortfall_nzd = float(
        (
            store_gp_gaps["benchmark_gp"]
            - store_gp_gaps["actual_gp"]
        )
        .clip(lower=0)
        .sum()
        / 100
    )

    return {
        "stores_below_benchmark": stores_below_benchmark,
        "persistent_underperformers": persistent_underperformers,
        "potential_gp_shortfall_nzd": potential_gp_shortfall_nzd,
        "store_count": int(data["store_id"].nunique()),
        "month_count": int(months_in_period),
    }