"""Load generated CSVs into DuckDB and run first KPI query."""
from pathlib import Path
import duckdb
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data' / 'retail.duckdb'

def main():
    con = duckdb.connect(str(DB))
    stores = str(ROOT / 'data' / 'raw' / 'stores.csv')
    perf = str(ROOT / 'data' / 'raw' / 'store_month_financials.csv')
    con.execute('CREATE OR REPLACE TABLE dim_store AS SELECT * FROM read_csv_auto(?)', [stores])
    con.execute('CREATE OR REPLACE TABLE fact_store_month AS SELECT * FROM read_csv_auto(?)', [perf])
    sql = (ROOT / 'sql' / '01_first_kpis.sql').read_text()
    print(con.execute(sql).df().to_string(index=False))
    con.close()
    print(f'Created {DB}')

if __name__ == '__main__':
    main()
