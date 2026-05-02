import sys, sqlite3
sys.path.insert(0, 'D:/futures_v6/macro_engine')

db = 'D:/futures_v6/macro_engine/pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# RU 的因子列表
cur.execute("SELECT DISTINCT factor_code FROM pit_factor_observations WHERE symbol='RU' ORDER BY factor_code")
ru_factors = [r[0] for r in cur.fetchall()]
print('RU factors:', ru_factors)
print('Count:', len(ru_factors))

# 最近日期
cur.execute("SELECT MAX(obs_date), factor_code FROM pit_factor_observations WHERE symbol='RU' GROUP BY factor_code ORDER BY MAX(obs_date) DESC LIMIT 10")
print()
print('RU latest obs_dates:')
for row in cur.fetchall():
    print(f'  {row}')

# 检查 OHLCV 数据
cur.execute("SELECT COUNT(*) FROM ru_futures_ohlcv")
print()
print('RU OHLCV rows:', cur.fetchone()[0])

cur.execute("SELECT MIN(trade_date), MAX(trade_date) FROM ru_futures_ohlcv")
print('RU OHLCV date range:', cur.fetchone())

conn.close()
