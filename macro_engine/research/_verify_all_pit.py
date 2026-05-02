"""全库 PIT 逐条复查验证"""
import sqlite3

DB = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

fixed_tables = [
    ('jm',  'jm_futures_ohlcv'),
    ('jm',  'jm_futures_hold_volume'),
    ('jm',  'jm_futures_spread'),
    ('ni',  'ni_futures_hold_volume'),
    ('ni',  'ni_futures_spread'),
    ('rb',  'rb_futures_hold_volume'),
    ('rb',  'rb_futures_spread'),
    ('ru',  'ru_futures_hold_volume'),
    ('ru',  'ru_futures_spread'),
    ('zn',  'zn_futures_hold_volume'),
    ('zn',  'zn_futures_spread'),
]

all_ok = True
for symbol, tbl in fixed_tables:
    total = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    # 剩余违规
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE obs_date != trade_date AND obs_date IS NOT NULL AND trade_date IS NOT NULL")
    violations = cur.fetchone()[0]
    # 随机抽查5条
    cur.execute(f"SELECT obs_date, trade_date, pub_date FROM {tbl} WHERE obs_date IS NOT NULL AND trade_date IS NOT NULL ORDER BY RANDOM() LIMIT 5")
    samples = cur.fetchall()
    
    status = 'PASS' if violations == 0 else 'FAIL'
    print(f'{status} | {symbol:4s} | {tbl:35s} | total={total:5d} | violations={violations}')
    for obs, trade, pub in samples:
        match = 'MATCH' if obs == trade else 'MISMATCH'
        print(f'       {match}: obs={obs} trade={trade} pub={pub}')
    
    if violations > 0:
        all_ok = False

# 全库最终检查
print('\n=== 全库最终状态 ===')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
all_tables = [r[0] for r in cur.fetchall()]
total_violations = 0
for tbl in all_tables:
    cur.execute(f"PRAGMA table_info({tbl})")
    cols = [r[1] for r in cur.fetchall()]
    if 'obs_date' in cols and 'trade_date' in cols:
        cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE obs_date != trade_date AND obs_date IS NOT NULL AND trade_date IS NOT NULL")
        v = cur.fetchone()[0]
        if v > 0:
            print(f'VIOLATION: {tbl}: {v} rows')
            total_violations += v

if total_violations == 0:
    print('全库 0 违规 ✅')
else:
    print(f'全库仍有 {total_violations} 违规 ❌')
    all_ok = False

conn.close()
print(f'\n最终结果: {"全部通过 ✅" if all_ok else "存在问题 ❌"}')
