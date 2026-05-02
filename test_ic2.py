import sys
sys.path.insert(0, 'D:/futures_v6/macro_engine')
from core.analysis.ic_heatmap_service import IcHeatmapService
from datetime import date

svc = IcHeatmapService()

# 检查方法
print('Methods:', [m for m in dir(svc) if '_get' in m])

# 用数据库里真实存在的因子测试
real_factors = ['RU_FUT_OI', 'RU_FX_USDCNY', 'RU_INV_QINGDAO']

print()
print('=== Testing _get_factor_series ===')
for factor in real_factors:
    series = svc._get_factor_series(factor, 'RU', date(2026,1,1), date(2026,4,28))
    print(f'{factor}: {len(series)} obs', end='')
    if series:
        print(f', sample: {series[:2]}')
    else:
        print()

print()
print('=== Testing calculate_ic with real factor ===')
for factor in real_factors:
    result = svc.calculate_ic(factor, 'RU', date(2026,1,1), date(2026,4,28))
    if result:
        print(f'{factor}: IC={result.ic_value:.4f}, p={result.ic_significance:.4f}, n={result.sample_size}')
    else:
        print(f'{factor}: None (insufficient data)')

print()
print('=== Checking OHLCV tables ===')
import sqlite3
db = 'D:/futures_v6/macro_engine/pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%ohlcv%'")
tables = [t[0] for t in cur.fetchall()]
print('OHLCV tables:', tables)
if tables:
    cur.execute(f"SELECT MIN(trade_date), MAX(trade_date) FROM {tables[0]}")
    print(f"Date range for {tables[0]}:", cur.fetchone())
    cur.execute(f"SELECT * FROM {tables[0]} LIMIT 2")
    cols = [d[0] for d in cur.description]
    print(f"Columns: {cols}")
conn.close()
