"""Focused transaction integrity and reproducibility tests."""
import json
import sys
from pathlib import Path
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from generate_transactions import generate_transactions,validate_transactions

@pytest.fixture
def sample():
    stores=pd.DataFrame([{'store_id':'S001','open_date':'2025-01-01'}, {'store_id':'S002','open_date':'2025-02-01'}])
    products=pd.DataFrame([{'product_id':'P00001','base_price_nzd':10.00,'unit_cost_nzd':6.00}])
    config={'random_seed':42,'start_date':'2025-01-01','end_date':'2025-02-28','promotions_enabled':True,'returns_enabled':True}
    return stores,products,config

def test_deterministic(sample):
    a,b,c=sample
    pd.testing.assert_frame_equal(generate_transactions(a,b,c,30),generate_transactions(a,b,c,30))

def test_valid_and_no_preopening(sample):
    a,b,c=sample;df=generate_transactions(a,b,c,50)
    validate_transactions(df,a,b)
    assert not ((df.store_id=='S002') & (df.transaction_date<'2025-02-01')).any()

def test_financial_identity(sample):
    a,b,c=sample;df=generate_transactions(a,b,c,50)
    assert (df.net_sales_cents==df.quantity*df.unit_price_cents-df.discount_cents).all()
    monthly=df.assign(month=df.transaction_date.str[:7]).groupby(['store_id','month'])[['net_sales_cents','cogs_cents']].sum()
    assert int(monthly.net_sales_cents.sum())==int(df.net_sales_cents.sum())
    assert int(monthly.cogs_cents.sum())==int(df.cogs_cents.sum())

def test_returns_reverse_original(sample):
    a,b,c=sample;df=generate_transactions(a,b,c,1000)
    returned=df[df.transaction_type=='RETURN']
    assert len(returned)>0
    validate_transactions(df,a,b)

def test_config_toggle(sample):
    a,b,c=sample;c={**c,'returns_enabled':False,'promotions_enabled':False}
    df=generate_transactions(a,b,c,20)
    assert (df.transaction_type=='SALE').all()
    assert (df.discount_cents==0).all()
