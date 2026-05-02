"""分析 JM spread PIT 真实情况"""
import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()

# 1. obs_date != trade_date 的记录数（真正的数据错误）
cur.execute("SELECT COUNT(*) FROM jm_futures_spread WHERE obs_date != trade_date")
mismatch = cur.fetchone()[0]
print(f'obs_date != trade_date: {mismatch}')

# 2. obs_date IS NULL 的记录
cur.execute("SELECT COUNT(*) FROM jm_futures_spread WHERE obs_date IS NULL")
null_obs = cur.fetchone()[0]
print(f'obs_date IS NULL: {null_obs}')

# 3. trade_date IS NULL 的记录
cur.execute("SELECT COUNT(*) FROM jm_futures_spread WHERE trade_date IS NULL")
null_trade = cur.fetchone()[0]
print(f'trade_date IS NULL: {null_trade}')

# 4. obs_date = trade_date 的记录（真正对齐）
cur.execute("SELECT COUNT(*) FROM jm_futures_spread WHERE obs_date = trade_date")
aligned = cur.fetchone()[0]
print(f'obs_date = trade_date: {aligned}')

# 5. 看几个 obs_date != trade_date 的样本（如果有的话）
cur.execute("SELECT obs_date, trade_date, pub_date FROM jm_futures_spread WHERE obs_date != trade_date LIMIT 5")
print('obs_date != trade_date 样本:')
for row in cur.fetchall():
    print(f'  obs={row[0]}, trade={row[1]}, pub={row[2]}')

# 6. 看 obs_date != trade_date 但 trade_date IS NOT NULL 的
cur.execute("SELECT COUNT(*) FROM jm_futures_spread WHERE obs_date != trade_date AND trade_date IS NOT NULL")
mismatch_with_trade = cur.fetchone()[0]
print(f'obs_date != trade_date 且 trade_date IS NOT NULL: {mismatch_with_trade}')

# 7. 原始 obs_date 的值是什么（没被修改前的状态）
# 用另一个JM表来验证逻辑：jm_futures_ohlcv 的 obs_date 情况
cur.execute("SELECT COUNT(*) FROM jm_futures_ohlcv WHERE pub_date > obs_date")
ohlcv_viol = cur.fetchone()[0]
print(f'\njm_futures_ohlcv 违规(pub>obs): {ohlcv_viol}')

conn.close()
