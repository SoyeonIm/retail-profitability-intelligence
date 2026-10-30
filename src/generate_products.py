"""Generate a reproducible synthetic product master for retail analysis."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def generate_products(config: dict) -> pd.DataFrame:
    count = int(config['product_count'])
    categories = list(config['product_categories'])
    seed = int(config['random_seed'])
    if count <= 0 or not categories or len(categories) != len(set(categories)):
        raise ValueError('product_count must be positive and categories unique/nonempty')
    rng = np.random.default_rng(seed)
    # Explicit simulation assumptions, not empirically calibrated estimates.
    category_margin = {
        'Health': .32, 'Beauty': .40, 'Skincare': .43,
        'Personal Care': .34, 'Vitamins': .36, 'Household': .24,
    }
    records = []
    for i in range(count):
        category = categories[i % len(categories)]
        # Prices are strictly positive, right-skewed and rounded to NZD cents.
        price = round(float(np.clip(rng.lognormal(np.log(19), .65), 3, 180)), 2)
        target_margin = float(np.clip(rng.normal(category_margin.get(category, .32), .065), .08, .65))
        cost = round(price * (1 - target_margin), 2)
        records.append({
            'product_id': f'P{i+1:05d}',
            'category': category,
            'product_name': f'{category} Item {i+1:05d}',
            'base_price_nzd': price,
            'unit_cost_nzd': cost,
            'base_margin_pct': round((price-cost)/price*100, 4),
        })
    return pd.DataFrame.from_records(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=ROOT / 'config' / 'generation.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'data' / 'raw' / 'products.csv')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    products = generate_products(config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    products.to_csv(args.output, index=False, float_format='%.4f')
    print(f'Generated {len(products)} synthetic products -> {args.output}')
    print(products.groupby('category').agg(products=('product_id','size'), avg_base_margin_pct=('base_margin_pct','mean')).round(2).to_string())


if __name__ == '__main__':
    main()
