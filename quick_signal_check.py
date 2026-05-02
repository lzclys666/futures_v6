#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

outdir = r'D:\futures_v6\macro_engine\output'
dates = ['20250203', '20250204', '20250205', '20250206', '20250207', '20250210']

print("=== RU signal timeline (first week) ===")
for d in dates:
    fname = f'RU_macro_daily_{d}.csv'
    fpath = os.path.join(outdir, fname)
    if os.path.exists(fpath):
        df = pd.read_csv(fpath)
        summary = df[df['row_type'] == 'SUMMARY'].iloc[0]
        print(f"  {d}: dir={summary['direction']}, score={summary['composite_score']}, conf={summary['confidence']}")
    else:
        print(f"  {d}: no file")

# Date range check
symbols = set()
date_set = set()
for f in os.listdir(outdir):
    if f.endswith('.csv'):
        parts = f.replace('.csv', '').split('_macro_daily_')
        if len(parts) == 2:
            symbols.add(parts[0])
            date_set.add(parts[1])

print(f"\nAll symbols ({len(symbols)}): {sorted(symbols)}")
print(f"Date range: {min(date_set)} ~ {max(date_set)}")

# Check signal direction distribution for each symbol (first 30 dates)
print("\n=== Signal direction distribution (first 30 dates) ===")
for sym in sorted(symbols):
    longs = 0
    shorts = 0
    neutrals = 0
    cnt = 0
    for d in sorted(date_set)[:30]:
        fpath = os.path.join(outdir, f'{sym}_macro_daily_{d}.csv')
        if os.path.exists(fpath):
            try:
                df = pd.read_csv(fpath)
                summary = df[df['row_type'] == 'SUMMARY'].iloc[0]
                d = str(summary['direction']).upper()
                if d == 'LONG':
                    longs += 1
                elif d == 'SHORT':
                    shorts += 1
                else:
                    neutrals += 1
                cnt += 1
            except:
                pass
    if cnt > 0:
        print(f"  {sym}: LONG={longs}, SHORT={shorts}, NEUTRAL={neutrals} (total {cnt})")
