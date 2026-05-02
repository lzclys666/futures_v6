"""全库 PIT 扫描：检查所有品种表的 obs_date vs trade_date 对齐问题"""
import sqlite3

DB = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# 获取所有表
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
all_tables = [r[0] for r in cur.fetchall()]
print(f'全库共 {len(all_tables)} 个表\n')

# 分类
summary = []
for tbl in all_tables:
    # 获取列
    cur.execute(f"PRAGMA table_info({tbl})")
    cols = {r[1]: r[2] for r in cur.fetchall()}  # col_name -> type
    
    if 'obs_date' not in cols:
        continue
    
    has_trade = 'trade_date' in cols
    total = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    
    if has_trade:
        # 有 trade_date：检查 obs_date != trade_date
        cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE obs_date != trade_date AND obs_date IS NOT NULL AND trade_date IS NOT NULL")
        mismatch = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE obs_date IS NULL")
        null_obs = cur.fetchone()[0]
        fixable = mismatch
        status = 'BUG' if mismatch > 0 else 'OK'
    else:
        # 无 trade_date：检查 obs_date IS NULL
        cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE obs_date IS NULL")
        null_obs = cur.fetchone()[0]
        fixable = null_obs
        status = 'NULL' if null_obs > 0 else 'OK'
    
    summary.append({
        'table': tbl,
        'total': total,
        'fixable': fixable,
        'null_obs': null_obs,
        'has_trade': has_trade,
        'status': status
    })
    print(f'{status:6s} | {fixable:5d} | {total:6d} | {tbl}')

# 汇总需要修复的表
bug_tables = [s for s in summary if s['status'] == 'BUG']
print(f'\n=== 需要修复: {len(bug_tables)} 个表 ===')
for s in bug_tables:
    print(f'  {s["table"]}: {s["fixable"]}/{s["total"]} 条错误')

conn.close()
