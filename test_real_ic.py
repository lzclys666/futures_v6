import sys
sys.path.insert(0, 'D:/futures_v6/macro_engine')
from core.analysis.ic_heatmap_service import IcHeatmapService
from datetime import date

svc = IcHeatmapService()

# 用数据库里真实存在的因子测试
real_factors = ['RU_FUT_OI', 'RU_FX_USDCNY', 'RU_INV_QINGDAO', 'RU_POS_NET']

print('=== Testing real factors ===')
for factor in real_factors:
    series = svc._get_factor_series(factor, 'RU', date(2026,1,1), date(2026,4,28))
    print(f'{factor}: {len(series)} obs', series[:2] if series else 'EMPTY')

print()
print('=== Testing calculate_ic with real factor ===')
result = svc.calculate_ic('RU_FUT_OI', 'RU', date(2026,1,1), date(2026,4,28))
print('calculate_ic RU_FUT_OI:', result)

# 检查 OHLCV 数据
print()
print('=== Checking OHLCV tables ===')
import sqlite3
db = 'D:/futures_v6/macro_engine/pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%ohlcv%'")
tables = cur.fetchall()
print('OHLCV tables:', [t[0] for t in tables])
if tables:
    cur.execute(f"SELECT MIN(trade_date), MAX(trade_date) FROM {tables[0][0]}")
    print(f"Date range for {tables[0][0]}:", cur.fetchone())
conn.close()
