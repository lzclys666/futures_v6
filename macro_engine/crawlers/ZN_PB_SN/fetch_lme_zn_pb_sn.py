#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_lme_zn_pb_sn
因子: 待定义 = fetch_lme_zn_pb_sn

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""

import sys
import os
from datetime import date
import pandas as pd

# Add crawlers path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import akshare as ak

# 目标品种配置
SYMBOLS = {
    'ZN': {'code': 'ZSD', 'csv_path': r'D:\futures_v6\macro_engine\data\crawlers\ZN\daily\ZN_LME_3M.csv'},
    'PB': {'code': 'PBD', 'csv_path': r'D:\futures_v6\macro_engine\data\crawlers\PB\daily\PB_LME_3M.csv'},
    'SN': {'code': 'SND', 'csv_path': r'D:\futures_v6\macro_engine\data\crawlers\SN\daily\SN_LME_3M.csv'},
}

today = date.today().strftime('%Y-%m-%d')
results = {}

for name, cfg in SYMBOLS.items():
    code = cfg['code']
    csv_path = cfg['csv_path']
    print(f'\n--- {name} ({code}) ---')
    
    try:
        df = ak.futures_foreign_commodity_realtime([code])
        print(f'Raw columns: {list(df.columns)}')
        print(f'Raw data:\n{df}')
        
        if df is not None and len(df) > 0:
            latest = float(df['最新价'].values[0])
            yesterday_settle = float(df['昨日结算价'].values[0])
            spread_diff = round(yesterday_settle - latest, 4)
            print(f'最新价: {latest}, 昨日结算: {yesterday_settle}, 升贴水代理: {spread_diff}')
            results[name] = {'symbol': code, 'latest': latest, 'yesterday_settle': yesterday_settle, 'spread_diff': spread_diff, 'csv_path': csv_path}
        else:
            print(f'No data returned for {code}')
            results[name] = None
    except Exception as e:
        print(f'Error fetching {code}: {e}')
        import traceback
        traceback.print_exc()
        results[name] = None

print('\n' + '=' * 60)
print('采集完成 - Summary')
print('=' * 60)
for name, data in results.items():
    if data:
        print(f'{name}: latest={data["latest"]}, yesterday_settle={data["yesterday_settle"]}, spread_diff={data["spread_diff"]}')
    else:
        print(f'{name}: FAILED')
print('=' * 60)

# Write to CSV files (append mode)
rows_written = 0
for name, data in results.items():
    if data is None:
        continue
    
    csv_path = data['csv_path']
    row = f'{today},{data["symbol"]},{data["latest"]},{data["yesterday_settle"]},{data["spread_diff"]}\n'
    
    # Check if file exists and has content
    file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    
    with open(csv_path, 'a', encoding='utf-8') as f:
        if not file_exists:
            f.write('date,symbol,latest,yesterday_settle,spread_diff\n')
        f.write(row)
    
    rows_written += 1
    print(f'Written to {csv_path}: {row.strip()}')

print(f'\nTotal rows written: {rows_written}')
