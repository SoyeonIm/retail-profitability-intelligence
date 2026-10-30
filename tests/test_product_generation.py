"""Product master invariants and reproducibility checks."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from generate_products import generate_products

CONFIG = json.loads((ROOT / 'config' / 'generation.json').read_text(encoding='utf-8'))


def test_product_count_and_keys():
    df = generate_products(CONFIG)
    assert len(df) == CONFIG['product_count']
    assert df.product_id.is_unique
    assert df.product_id.notna().all()
    assert set(df.category) == set(CONFIG['product_categories'])


def test_prices_costs_and_margin_identity():
    df = generate_products(CONFIG)
    assert (df.base_price_nzd > 0).all()
    assert (df.unit_cost_nzd >= 0).all()
    assert (df.unit_cost_nzd <= df.base_price_nzd).all()
    calculated = (df.base_price_nzd - df.unit_cost_nzd) / df.base_price_nzd * 100
    assert ((calculated - df.base_margin_pct).abs() < 0.0001).all()


def test_deterministic_generation():
    pd.testing.assert_frame_equal(generate_products(CONFIG), generate_products(CONFIG))


def test_invalid_config_rejected():
    import pytest
    with pytest.raises(ValueError):
        generate_products({**CONFIG, 'product_count': 0})
