"""Audit the existing store-month dataset before redesigning its grain."""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data' / 'retail.duckdb'

QUERIES = {
    'Duplicate store-month keys': '''SELECT COUNT(*) FROM (SELECT store_id, month FROM fact_store_month GROUP BY 1,2 HAVING COUNT(*)>1)''',
    'Missing store references': '''SELECT COUNT(*) FROM fact_store_month f LEFT JOIN dim_store s ON f.store_id=s.store_id WHERE s.store_id IS NULL''',
    'Pre-opening financial rows': '''SELECT COUNT(*) FROM fact_store_month f JOIN dim_store s ON f.store_id=s.store_id WHERE CAST(f.month AS DATE) < CAST(s.open_date AS DATE)''',
    'Missing financial amounts': '''SELECT COUNT(*) FROM fact_store_month WHERE net_sales IS NULL OR cogs IS NULL OR labour_cost IS NULL OR occupancy_cost IS NULL OR other_store_cost IS NULL''',
    'Negative or invalid sales/COGS': '''SELECT COUNT(*) FROM fact_store_month WHERE net_sales <= 0 OR cogs < 0 OR cogs > net_sales''',
}

def audit(con):
    return {label: con.execute(sql).fetchone()[0] for label, sql in QUERIES.items()}

def main():
    if not DB.exists():
        raise SystemExit('Database missing. Run: python src/build_database.py')
    with duckdb.connect(str(DB), read_only=True) as con:
        results = audit(con)
        stores, months, rows = con.execute('''SELECT COUNT(DISTINCT store_id), COUNT(DISTINCT month), COUNT(*) FROM fact_store_month''').fetchone()
        print(f'Baseline: {stores} stores | {months} months | {rows} store-month records')
        for label, count in results.items():
            print(f'{label}: {count}')
        if results['Pre-opening financial rows']:
            print('ACTION: Exclude or repair pre-opening rows before publishing profitability comparisons.')
        print('Audit complete; no data were modified.')

if __name__ == '__main__':
    main()
