from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]

def load():
    stores = pd.read_csv(ROOT / 'data' / 'raw' / 'stores.csv')
    facts = pd.read_csv(ROOT / 'data' / 'raw' / 'store_month_financials.csv')
    return stores, facts

def test_expected_shape():
    stores, facts = load()
    assert len(stores) == 60
    assert len(facts) == 60 * 21

def test_unique_keys():
    stores, facts = load()
    assert stores.store_id.is_unique
    assert not facts.duplicated(['store_id', 'month']).any()

def test_referential_integrity():
    stores, facts = load()
    assert set(facts.store_id).issubset(set(stores.store_id))

def test_financial_constraints():
    _, facts = load()
    for c in ['net_sales', 'cogs', 'labour_cost', 'occupancy_cost', 'other_store_cost']:
        assert facts[c].notna().all()
        assert (facts[c] >= 0).all()
    assert (facts.cogs <= facts.net_sales).all()
