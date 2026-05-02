#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复 SA 脚本的 AKShare DataFrame 条件判断（条件反了导致空DataFrame时走错误分支）"""
import os, re

base = r'D:\futures_v6\macro_engine\crawlers\SA'

# 每个脚本的修复：(old_pattern, new_pattern)
FIXES = {
    'SA_抓取现货价.py': [
        ('    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is None or df.empty:\n        row = df.iloc[-1]',  # buggy
         '    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is not None and not df.empty:\n        row = df.iloc[-1]'),
    ],
    'SA_抓取期货日行情.py': [
        ('    df = ak.futures_daily(date=date_str, symbol_list=["SA"])\n    if df is None or len(df) == 0:\n        print("[L1] AKShare无数据，尝试备用...")\n        vals = []',
         '    df = ak.futures_daily(date=date_str, symbol_list=["SA"])\n    if df is not None and len(df) > 0:\n        vals = [...]  # 正常处理\n    else:\n        print("[L1] AKShare无数据...")\n        vals = []'),
    ],
    'SA_抓取近月合约价.py': [
        ('    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is None or df.empty:\n        row = df.iloc[0]',
         '    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is not None and not df.empty:\n        row = df.iloc[0]'),
    ],
    'SA_抓取次月合约价.py': [
        ('    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is None or df.empty:\n        row = df.iloc[0]',
         '    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is not None and not df.empty:\n        row = df.iloc[0]'),
    ],
}

# SA_抓取期货日行情.py 比较复杂，需要逐行处理

scripts_simple = {
    'SA_抓取现货价.py': [
        ('    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is None or df.empty:\n        row = df.iloc[-1]\n        val = float(row["spot_price"])',
         '    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is not None and not df.empty:\n        row = df.iloc[-1]\n        val = float(row["spot_price"])'),
    ],
    'SA_抓取近月合约价.py': [
        ('    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is None or df.empty:\n        row = df.iloc[0]\n        val = float(row["close"])',
         '    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is not None and not df.empty:\n        row = df.iloc[0]\n        val = float(row["close"])'),
    ],
    'SA_抓取次月合约价.py': [
        ('    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is None or df.empty:\n        row = df.iloc[0]\n        val = float(row["close"])',
         '    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is not None and not df.empty:\n        row = df.iloc[0]\n        val = float(row["close"])'),
    ],
}

for name, fixes in scripts_simple.items():
    path = os.path.join(base, name)
    with open(path, encoding='utf-8') as f:
        content = f.read()
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            print(f'FIXED condition in {name}')
        else:
            print(f'NOT FOUND in {name}: {repr(old[:50])}')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# SA_抓取期货日行情.py 需要特殊处理
path = os.path.join(base, 'SA_抓取期货日行情.py')
with open(path, encoding='utf-8') as f:
    content = f.read()

# 查找并修复条件
old = '    df = ak.futures_daily(date=date_str, symbol_list=["SA"])\n    if df is None or len(df) == 0:\n        print("[L1] AKShare无数据，尝试备用...")\n        vals = []'
new = '    df = ak.futures_daily(date=date_str, symbol_list=["SA"])\n    if df is not None and len(df) > 0:'
if old in content:
    content = content.replace(old, new)
    print('FIXED condition in SA_抓取期货日行情.py')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
else:
    print('NOT FOUND in SA_抓取期货日行情.py')

print('Done')
