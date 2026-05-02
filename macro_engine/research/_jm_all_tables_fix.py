"""全面检查所有 JM 相关表的 PIT 状态"""
import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
cur = conn.cursor()

# 找出所有 jm_ 开头的表
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'jm_%'")
tables = [r[0] for r in cur.fetchall()]
print(f'JM相关表: {tables}\n')

for tbl in tables:
    # 获取列名
    cur.execute(f"PRAGMA table_info({tbl})")
    cols = [r[1] for r in cur.fetchall()]
    has_obs = 'obs_date' in cols
    has_trade = 'trade_date' in cols
    has_pub = 'pub_date' in cols
    
    if not has_obs:
        print(f'{tbl}: 无 obs_date 列，跳过')
        continue
    
    # 总记录
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    total = cur.fetchone()[0]
    
    if has_trade:
        # 有 trade_date：检查 obs_date != trade_date
        cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE obs_date != trade_date")
        mismatch = cur.fetchone()[0]
        fixable = mismatch
        status = f'需修复 {mismatch}/{total}' if mismatch > 0 else 'OK'
    else:
        # 无 trade_date：检查 obs_date IS NULL
        cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE obs_date IS NULL")
        null_obs = cur.fetchone()[0]
        fixable = null_obs
        status = f'obs_date IS NULL: {null_obs}/{total}' if null_obs > 0 else 'OK'
    
    print(f'{tbl}: {status}')
    print(f'  列: {cols}')

conn.close()
