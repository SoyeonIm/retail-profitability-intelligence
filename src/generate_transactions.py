"""Generate deterministic, synthetic retail transaction lines.

Financial amounts are integer NZD cents internally. Returns reference an
original sale line and reverse its realized revenue and cost exactly.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COLS = ['transaction_line_id','transaction_id','transaction_date','store_id',
        'product_id','transaction_type','original_sale_line_id','quantity',
        'unit_price_cents','discount_cents','net_sales_cents','cogs_cents']


def generate_transactions(stores: pd.DataFrame, products: pd.DataFrame,
                          config: dict, sales_per_store_month: int = 120) -> pd.DataFrame:
    if sales_per_store_month < 1:
        raise ValueError('sales_per_store_month must be positive')
    if stores.store_id.duplicated().any() or products.product_id.duplicated().any():
        raise ValueError('Dimension keys must be unique')
    if not {'store_id','open_date'}.issubset(stores) or not {'product_id','base_price_nzd','unit_cost_nzd'}.issubset(products):
        raise ValueError('Required columns missing')
    rng = np.random.default_rng(int(config['random_seed']) + 1001)
    start = pd.Timestamp(config['start_date']); end = pd.Timestamp(config['end_date'])
    if end < start: raise ValueError('end_date precedes start_date')
    months = pd.date_range(start.to_period('M').to_timestamp(), end, freq='MS')
    product_ids = products.product_id.to_numpy()
    prices = np.rint(products.base_price_nzd.to_numpy(dtype=float)*100).astype('int64')
    costs = np.rint(products.unit_cost_nzd.to_numpy(dtype=float)*100).astype('int64')
    if (prices <= 0).any() or (costs < 0).any(): raise ValueError('Invalid product prices/costs')
    rows=[]; counter=0; receipt=0
    for store in stores.sort_values('store_id').itertuples(index=False):
        opened = pd.Timestamp(store.open_date)
        for month in months:
            first=max(month,start,opened)
            last=min(month+pd.offsets.MonthEnd(0),end)
            if first > last: continue
            eligible_days=pd.date_range(first,last,freq='D')
            # One transaction per generated sale line for a transparent v1 grain.
            for _ in range(sales_per_store_month):
                idx=int(rng.integers(0,len(product_ids)))
                day=str(eligible_days[int(rng.integers(0,len(eligible_days)))].date())
                qty=int(rng.choice([1,1,1,2,2,3]))
                gross=int(prices[idx])*qty
                rate=float(rng.choice([0,.05,.10,.15,.20],p=[.65,.10,.12,.08,.05])) if config.get('promotions_enabled',True) else 0.0
                discount=int(round(gross*rate))
                counter+=1;receipt+=1
                sale_id=f'L{counter:09d}'
                sale=dict(transaction_line_id=sale_id,transaction_id=f'T{receipt:09d}',
                          transaction_date=day,store_id=store.store_id,product_id=product_ids[idx],
                          transaction_type='SALE',original_sale_line_id='',quantity=qty,
                          unit_price_cents=int(prices[idx]),discount_cents=discount,
                          net_sales_cents=gross-discount,cogs_cents=int(costs[idx])*qty)
                rows.append(sale)
                # Return entire sale line, on the same day for this v1 simulation.
                if config.get('returns_enabled',True) and rng.random()<.025:
                    counter+=1;receipt+=1
                    rows.append(dict(transaction_line_id=f'L{counter:09d}',transaction_id=f'T{receipt:09d}',
                                     transaction_date=day,store_id=store.store_id,product_id=product_ids[idx],
                                     transaction_type='RETURN',original_sale_line_id=sale_id,quantity=-qty,
                                     unit_price_cents=int(prices[idx]),discount_cents=-discount,
                                     net_sales_cents=-(gross-discount),cogs_cents=-(int(costs[idx])*qty)))
    return pd.DataFrame.from_records(rows,columns=COLS)


def validate_transactions(df: pd.DataFrame, stores: pd.DataFrame, products: pd.DataFrame) -> None:
    if df.empty: raise ValueError('No transactions generated')
    if df.transaction_line_id.duplicated().any(): raise ValueError('Duplicate transaction line IDs')
    if not df.store_id.isin(stores.store_id).all(): raise ValueError('Unknown store')
    if not df.product_id.isin(products.product_id).all(): raise ValueError('Unknown product')
    opening=stores.set_index('store_id').open_date
    if (pd.to_datetime(df.transaction_date).to_numpy() < pd.to_datetime(df.store_id.map(opening)).to_numpy()).any():
        raise ValueError('Transaction before store opening')
    if not ((df.quantity>0).eq(df.transaction_type=='SALE')).all(): raise ValueError('Invalid quantity sign')
    if not ((df.net_sales_cents>0).eq(df.transaction_type=='SALE')).all(): raise ValueError('Invalid revenue sign')
    if not ((df.cogs_cents>=0) & (df.transaction_type=='SALE') | (df.cogs_cents<=0) & (df.transaction_type=='RETURN')).all():
        raise ValueError('Invalid COGS sign')
    sales=df[df.transaction_type=='SALE'].set_index('transaction_line_id')
    returns=df[df.transaction_type=='RETURN']
    if returns.original_sale_line_id.duplicated().any(): raise ValueError('Repeated full return')
    for r in returns.itertuples(index=False):
        if r.original_sale_line_id not in sales.index: raise ValueError('Missing original sale')
        s=sales.loc[r.original_sale_line_id]
        for field in ('store_id','product_id'):
            if getattr(r,field)!=s[field]: raise ValueError('Return dimension mismatch')
        for field in ('quantity','discount_cents','net_sales_cents','cogs_cents'):
            if getattr(r,field)!=-int(s[field]): raise ValueError('Return amount mismatch')


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,default=ROOT/'config/generation.json')
    parser.add_argument('--sales-per-store-month',type=int,default=120)
    args=parser.parse_args()
    config=json.loads(args.config.read_text(encoding='utf-8'))
    stores=pd.read_csv(ROOT/'data/raw/stores.csv')
    products=pd.read_csv(ROOT/'data/raw/products.csv')
    df=generate_transactions(stores,products,config,args.sales_per_store_month)
    validate_transactions(df,stores,products)
    out=ROOT/'data/raw/transactions.csv';out.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(out,index=False)
    monthly=df.assign(month=df.transaction_date.str.slice(0,7)).groupby(['store_id','month'],as_index=False)[['net_sales_cents','cogs_cents']].sum()
    monthly['gross_profit_cents']=monthly.net_sales_cents-monthly.cogs_cents
    monthly.to_csv(ROOT/'data/raw/transaction_month_reconciliation.csv',index=False)
    print(f'Generated {len(df):,} transaction lines ({(df.transaction_type=="RETURN").sum():,} returns).')
    print(f'Store-month aggregates: {len(monthly):,}; net sales NZD {df.net_sales_cents.sum()/100:,.2f}')
    print('Transaction-level arithmetic and return references validated.')

if __name__=='__main__': main()
