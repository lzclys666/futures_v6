from config.paths import MACRO_ENGINE
import sys
sys.path.insert(0, 'str(MACRO_ENGINE)')
from core.analysis.ic_heatmap_service import IcHeatmapService
from datetime import date

svc = IcHeatmapService()

# 直接调用 _get_factor_series
print('Calling _get_factor_series...')
series = svc._get_factor_series('RU_FUT_OI', 'RU', date(2026,1,1), date(2026,4,28))
print('Result length:', len(series))
if series:
    print('Sample:', series[:3])

print()
print('Calling calculate_ic...')
result = svc.calculate_ic('RU_FUT_OI', 'RU', date(2026,1,1), date(2026,4,28))
print('Result:', result)
if result:
    print(f'  IC={result.ic_value:.4f}, p={result.ic_significance:.4f}, n={result.sample_size}')

print()
print('=== Checking OHLCV ===')
import sqlite3
db = 'str(MACRO_ENGINE)/pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%ohlcv%'")
tables = [t[0] for t in cur.fetchall()]
print('OHLCV tables:', tables)
if tables:
    cur.execute(f"SELECT * FROM {tables[0]} LIMIT 1")
    cols = [d[0] for d in cur.description]
    print(f"Columns of {tables[0]}: {cols}")
    cur.execute(f"SELECT MIN(trade_date), MAX(trade_date) FROM {tables[0]}")
    print(f"Date range:", cur.fetchone())
conn.close()
