"""Estimate the client's WACC.

Run from the repo root:   python code/wacc.py
Reads:  inputs/assumptions.csv
Writes: outputs/wacc.csv (one row; the columns are listed in README.md)

Owner: the developer. Beta is estimated here from market data; every other
input (rf, mrp, rd, tax, w_e, w_d) comes from the analyst's assumptions.csv.
"""
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

CLIENT = 'EQIX'  # Equinix, per README.md
MKT = 'SPY'
YEARS = 5

INPUTS = Path('inputs/assumptions.csv')
OUTPUT = Path('outputs/wacc.csv')
REQUIRED = ['rf', 'mrp', 'rd', 'tax', 'w_e', 'w_d']
COLS = ['ticker', 'asof', 'beta', 'rf', 'mrp', 'cost_of_equity', 'rd', 'tax', 'w_e', 'w_d', 'wacc']


def load_assumptions(path=INPUTS):
    """Read the analyst's inputs into a dict of floats, with clear errors for anything
    missing, non-numeric, or obviously in the wrong units (e.g. 4 instead of 0.04)."""
    if not path.exists():
        sys.exit(f'Missing {path}. Run from the repo root, and make sure the analyst file exists.')
    df = pd.read_csv(path)
    for col in ('item', 'value'):
        if col not in df.columns:
            sys.exit(f'{path} needs an "{col}" column (found: {list(df.columns)})')
    df['item'] = df['item'].astype(str).str.strip()
    a = df.set_index('item')['value']

    missing = [k for k in REQUIRED if k not in a.index or pd.isna(a[k])]
    if missing:
        sys.exit(f'{path} is missing values for: {", ".join(missing)}')

    out = {}
    for k in REQUIRED:
        try:
            out[k] = float(a[k])
        except (TypeError, ValueError):
            sys.exit(f'{path}: "{k}" must be a number in decimal units (0.05 = 5%), got {a[k]!r}')
        if not 0 <= out[k] <= 1:
            sys.exit(f'{path}: "{k}" = {out[k]} is outside 0-1. Use decimals (0.05 = 5%), not percents.')

    if 'source' in df.columns and df['source'].astype(str).str.contains('TODO').any():
        print('WARNING: some sources in assumptions.csv still say TODO; '
              'these are placeholder inputs, not final Equinix numbers.\n')
    return out


def get_returns(ticker, mkt=MKT, years=YEARS):
    """Daily returns for the client and the market over the last `years` years.
    Returns a DataFrame with two columns, named ticker and mkt, and no missing values."""
    end = pd.Timestamp.today().normalize()
    start = end - pd.DateOffset(years=years)
    px = yf.download([ticker, mkt], start=start, end=end, auto_adjust=True, progress=False)['Close']
    if px.empty or ticker not in px or mkt not in px:
        sys.exit(f'Could not download prices for {ticker} and {mkt}. Check your internet connection.')
    return px[[ticker, mkt]].pct_change().dropna()


def estimate_beta(rets, ticker, mkt=MKT):
    """Equity beta: cov(stock, market) / var(market)."""
    return rets[ticker].cov(rets[mkt]) / rets[mkt].var()


def compute_wacc(beta, a):
    """a is a dict of assumptions: rf, mrp, rd, tax, w_e, w_d.
    Returns a dict with cost_of_equity and wacc (and the inputs), matching the README's columns."""
    cost_of_equity = a['rf'] + beta * a['mrp']
    wacc = a['w_e'] * cost_of_equity + a['w_d'] * a['rd'] * (1 - a['tax'])
    return {'rf': a['rf'], 'mrp': a['mrp'], 'cost_of_equity': cost_of_equity,
            'rd': a['rd'], 'tax': a['tax'], 'w_e': a['w_e'], 'w_d': a['w_d'], 'wacc': wacc}


if __name__ == '__main__':
    a = load_assumptions()
    assert abs(a['w_e'] + a['w_d'] - 1) < 1e-6, \
        f"weights must sum to 1 (w_e={a['w_e']} + w_d={a['w_d']} = {a['w_e'] + a['w_d']})"

    rets = get_returns(CLIENT)
    assert len(rets) > 1000, f'expected about 5 years of daily returns, got {len(rets)}'

    beta = estimate_beta(rets, CLIENT)
    out = compute_wacc(beta, a)
    out = {'ticker': CLIENT, 'asof': rets.index.max().date(), 'beta': beta, **out}

    assert 0 < out['wacc'] < 0.25, f"WACC = {out['wacc']:.4f} is outside 0-25%: check the inputs"
    OUTPUT.parent.mkdir(exist_ok=True)
    pd.DataFrame([out])[COLS].to_csv(OUTPUT, index=False)
    print(pd.DataFrame([out])[COLS].T)
