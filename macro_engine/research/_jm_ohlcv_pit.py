"""检查 jm_futures_ohlcv PIT 状态"""
import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()

# ohlcv 表结构
cur.execute("PRAGMA table_info(jm_futures_ohlcv)")
print('jm_futures_ohlcv 列:', [r[1] for r in cur.fetchall()])

# 总记录
cur.execute("SELECT COUNT(*) FROM jm_futures_ohlcv")
total = cur.fetchone()[0]
print(f'总记录: {total}')

# obs_date != trade_date 的记录
cur.execute("SELECT COUNT(*) FROM jm_futures_ohlcv WHERE obs_date != trade_date")
mismatch = cur.fetchone()[0]
print(f'obs_date != trade_date: {mismatch}')

# obs_date IS NULL
cur.execute("SELECT COUNT(*) FROM jm_futures_ohlcv WHERE obs_date IS NULL")
null_obs = cur.fetchone()[0]
print(f'obs_date IS NULL: {null_obs}')

# trade_date IS NULL
cur.execute("SELECT COUNT(*) FROM jm_futures_ohlcv WHERE trade_date IS NULL")
null_trade = cur.fetchone()[0]
print(f'trade_date IS NULL: {null_trade}')

# obs_date = trade_date 且 obs_date IS NOT NULL
cur.execute("SELECT COUNT(*) FROM jm_futures_ohlcv WHERE obs_date = trade_date AND obs_date IS NOT NULL")
aligned = cur.fetchone()[0]
print(f'obs_date = trade_date: {aligned}')

# obs_date != trade_date 且 trade_date IS NOT NULL（需要修复的）
cur.execute("SELECT COUNT(*) FROM jm_futures_ohlcv WHERE obs_date != trade_date AND trade_date IS NOT NULL")
fixable = cur.fetchone()[0]
print(f'obs_date != trade_date 且 trade_date非空（需修复）: {fixable}')

# 样本
cur.execute("SELECT obs_date, trade_date, pub_date, open, high, low, close FROM jm_futures_ohlcv WHERE obs_date != trade_date LIMIT 5")
print('\n需修复样本:')
for row in cur.fetchall():
    print(f'  obs={row[0]}, trade={row[1]}, pub={row[2]}, O={row[3]}, H={row[4]}, L={row[5]}, C={row[6]}')

conn.close()
