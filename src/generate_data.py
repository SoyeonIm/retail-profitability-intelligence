"""Generate reproducible fictional NZ retail store-month data."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'raw'
SEED = 20261030

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    regions = ['Auckland', 'Waikato', 'Wellington', 'Canterbury', 'Bay of Plenty', 'Otago']
    stores = []
    for i in range(1, 61):
        region = regions[(i - 1) % len(regions)]
        sqm = int(rng.integers(300, 1301))
        open_year = int(rng.integers(2014, 2026))
        stores.append({'store_id': f'S{i:03d}', 'region': region,
                       'floor_area_sqm': sqm, 'open_date': f'{open_year}-01-01'})
    store_df = pd.DataFrame(stores)
    store_df.to_csv(OUT / 'stores.csv', index=False)

    months = pd.date_range('2025-01-01', '2026-09-01', freq='MS')
    rows = []
    for s in stores:
        base = s['floor_area_sqm'] * rng.uniform(220, 370)
        region_factor = {'Auckland': 1.11, 'Waikato': .97, 'Wellington': 1.05,
                         'Canterbury': 1.01, 'Bay of Plenty': .96, 'Otago': .94}[s['region']]
        gp_base = rng.uniform(.255, .345)
        for dt in months:
            season = 1.18 if dt.month == 12 else (1.07 if dt.month in [6, 7] else 1.0)
            revenue = max(10000, base * region_factor * season * rng.normal(1, .075))
            gp_rate = np.clip(gp_base + rng.normal(0, .012), .15, .48)
            cogs = revenue * (1 - gp_rate)
            labour = revenue * rng.uniform(.095, .16)
            occupancy = s['floor_area_sqm'] * rng.uniform(17, 28)
            other = revenue * rng.uniform(.025, .055)
            rows.append({'store_id': s['store_id'], 'month': dt.strftime('%Y-%m-%d'),
                         'net_sales': round(revenue, 2), 'cogs': round(cogs, 2),
                         'labour_cost': round(labour, 2), 'occupancy_cost': round(occupancy, 2),
                         'other_store_cost': round(other, 2)})
    perf = pd.DataFrame(rows)
    perf.to_csv(OUT / 'store_month_financials.csv', index=False)
    print(f'Generated {len(store_df)} fictional stores and {len(perf)} store-month rows.')
    print('Synthetic data only: no real company financials or causal claims.')

if __name__ == '__main__':
    main()
