import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# 1. 找出所有 NULL 因子
cur.execute('''
    SELECT symbol, factor_code, MAX(obs_date) as latest
    FROM pit_factor_observations 
    WHERE raw_value IS NULL 
    GROUP BY symbol, factor_code
    ORDER BY symbol, factor_code
''')
nulls = cur.fetchall()

print(f"=== NULL 因子统计 ===")
print(f"总计: {len(nulls)} 个\n")

by_symbol = {}
for sym, fc, od in nulls:
    by_symbol.setdefault(sym, []).append((fc, od))

for sym in sorted(by_symbol.keys()):
    factors = by_symbol[sym]
    print(f"{sym} ({len(factors)} 个 NULL):")
    for fc, od in factors:
        print(f"  {fc} | 最新: {od}")
    print()

# 2. 检查 ETL cron
print("=== ETL 定时任务检查 ===")
import subprocess
result = subprocess.run(['schtasks', '/query', '/tn', 'FuturesMacro_ETL', '/fo', 'LIST'], 
                       capture_output=True, text=True, encoding='gbk')
if result.returncode == 0:
    print("ETL 定时任务: 存在")
    print(result.stdout[:500])
else:
    print("ETL 定时任务: 不存在")
    result2 = subprocess.run(['schtasks', '/query', '/fo', 'LIST'], 
                           capture_output=True, text=True, encoding='gbk')
    # 搜索所有包含 Futures 的任务
    for line in result2.stdout.split('\n'):
        if 'Futures' in line or 'futures' in line:
            print(f"  找到: {line.strip()}")

# 3. 检查 ETL 脚本是否存在
etl_scripts = [
    r'D:\futures_v6\macro_engine\scripts\factor_collector_main.py',
    r'D:\futures_v6\macro_engine\scripts\etl_crawler_main.py',
    r'D:\futures_v6\macro_engine\scripts\etl_main.py',
]
print("\n=== ETL 脚本检查 ===")
for p in etl_scripts:
    exists = os.path.exists(p)
    print(f"  {os.path.basename(p)}: {'存在' if exists else '不存在'}")

conn.close()
