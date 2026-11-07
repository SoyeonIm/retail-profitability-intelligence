
"""Load validated retail reporting views from DuckDB."""

from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"

# Dependency order matters: later views reference earlier views.
REPORTING_VIEWS = [
    ("category_mart", "04_category_profitability.sql"),
    ("margin_decomposition", "05_margin_decomposition.sql"),
    ("store_performance", "06_store_performance.sql"),
    ("regional_profitability", "07_regional_profitability.sql"),
    ("category_margin_drivers", "09_category_margin_drivers.sql"),
    ("profitability_trends", "11_profitability_trends.sql"),
    ("store_profitability_diagnostics", "12_store_profitability_diagnostics.sql"),
    ("nz_benchmark_contribution", "13_nz_benchmark_contribution.sql"),
    ("investigation_priorities", "14_investigation_priorities.sql"),
    ("store_reporting", "15_store_reporting.sql"),
    ("regional_reporting", "16_regional_reporting.sql"),
]


def read_sql(filename: str) -> str:
    """Read an existing SQL model without modifying its logic."""
    path = SQL_DIR / filename

    if not path.is_file():
        raise FileNotFoundError(f"SQL file not found: {path}")

    return path.read_text(encoding="utf-8").strip().rstrip(";")


def create_reporting_connection() -> duckdb.DuckDBPyConnection:
    """Create an in-memory DuckDB connection with reporting views."""
    con = duckdb.connect(database=":memory:")

    try:
        for view_name, filename in REPORTING_VIEWS:
            con.execute(
                f"CREATE TEMP VIEW {view_name} AS {read_sql(filename)}"
            )

        return con

    except Exception:
        con.close()
        raise


def load_reporting_data() -> dict[str, pd.DataFrame]:
    """Return validated store and regional reporting datasets."""
    con = create_reporting_connection()

    try:
        store = con.execute(
            "SELECT * FROM store_reporting ORDER BY month, store_id"
        ).df()

        region = con.execute(
            "SELECT * FROM regional_reporting ORDER BY month, region"
        ).df()

        return {
            "store": store,
            "region": region,
        }

    finally:
        con.close()


def load_category_reporting_data() -> pd.DataFrame:
    """Load store-month-category profitability from validated SQL."""

    con = create_reporting_connection()

    try:
        category = con.execute(
            """
            SELECT
                store_id,
                month,
                category,
                net_sales_cents,
                cogs_cents,
                gross_profit_cents,
                gp_margin_pct
            FROM category_mart
            ORDER BY month, store_id, category
            """
        ).df()

        required_columns = {
            "store_id",
            "month",
            "category",
            "net_sales_cents",
            "cogs_cents",
            "gross_profit_cents",
            "gp_margin_pct",
        }

        missing = required_columns - set(category.columns)

        if missing:
            raise ValueError(
                f"Missing category columns: {sorted(missing)}"
            )

        if category.empty:
            raise ValueError("Category reporting data is empty.")

        if category.duplicated(
            subset=["store_id", "month", "category"]
        ).any():
            raise ValueError(
                "Duplicate store-month-category records."
            )

        return category

    finally:
        con.close()


def load_margin_decomposition_data() -> pd.DataFrame:
    """Load and validate store-month GP margin decomposition."""

    con = create_reporting_connection()

    try:
        data = con.execute(
            """
            SELECT *
            FROM margin_decomposition
            ORDER BY month, store_id
            """
        ).df()

        required_columns = {
            "store_id",
            "month",
            "store_sales_cents",
            "store_gp_cents",
            "benchmark_total_sales_cents",
            "benchmark_total_gp_cents",
            "store_gp_margin_pct",
            "benchmark_gp_margin_pct",
            "mix_effect_pp",
            "margin_effect_pp",
            "explained_gap_pp",
            "actual_gap_pp",
            "reconciliation_residual_pp",
        }

        missing = required_columns - set(data.columns)

        if missing:
            raise ValueError(
                f"Missing decomposition columns: {sorted(missing)}"
            )

        if data.empty:
            raise ValueError(
                "Margin decomposition data is empty."
            )

        if data[list(required_columns)].isna().any().any():
            raise ValueError(
                "Margin decomposition contains missing values."
            )

        if data.duplicated(
            subset=["store_id", "month"]
        ).any():
            raise ValueError(
                "Duplicate store-month decomposition records."
            )

        # The underlying SQL decomposition must reconcile.
        tolerance_pp = 0.0001

        if (
            data["reconciliation_residual_pp"].abs()
            > tolerance_pp
        ).any():
            raise ValueError(
                "Margin decomposition does not reconcile."
            )

        # Validate the bridge independently using reported effects.
        calculated_gap = (
            data["mix_effect_pp"]
            + data["margin_effect_pp"]
        )

        if (
            calculated_gap - data["actual_gap_pp"]
        ).abs().gt(tolerance_pp).any():
            raise ValueError(
                "Mix and margin effects do not match the actual GP gap."
            )

        return data

    finally:
        con.close()