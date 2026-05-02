"""修复全库所有 obs_date 填错问题"""
import sqlite3

DB = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

tables_to_fix = [
    'ni_futures_hold_volume',
    'ni_futures_spread',
    'rb_futures_hold_volume',
    'rb_futures_spread',
    'ru_futures_hold_volume',
    'ru_futures_spread',
    'zn_futures_hold_volume',
    'zn_futures_spread',
]

total_before = 0
total_fixed = 0

for tbl in tables_to_fix:
    # 修复前数量
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE obs_date != trade_date AND obs_date IS NOT NULL AND trade_date IS NOT NULL")
    before = cur.fetchone()[0]
    total_before += before
    
    # 执行修复
    cur.execute(f'''
        UPDATE {tbl}
        SET obs_date = trade_date
        WHERE obs_date != trade_date
          AND obs_date IS NOT NULL
          AND trade_date IS NOT NULL
    ''')
    fixed = cur.rowcount
    total_fixed += fixed
    
    # 修复后验证
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE obs_date != trade_date AND obs_date IS NOT NULL AND trade_date IS NOT NULL")
    after = cur.fetchone()[0]
    
    print(f'{"OK" if after == 0 else "FAIL"} | {fixed:5d} -> {after:3d} | {tbl}')

conn.commit()
conn.close()

print(f'\n总计: 修复 {total_fixed} 条, 剩余 {sum(1 for t in tables_to_fix)} 表待验证')
print('全库 PIT 修复完成')
