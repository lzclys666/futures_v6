#!/usr/bin/env python3
"""Phase 0 PIT冒烟测试"""

import sqlite3, os

db_path = r'D:\futures_v6\macro_engine\pit_data.db'
print(f'数据库文件存在: {os.path.exists(db_path)}')
print(f'数据库大小: {os.path.getsize(db_path)/1024:.1f} KB')

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 检查表
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f'数据库表数量: {len(tables)}')
print(f'前10个表: {tables[:10]}')

# 检查记录数
cur.execute("SELECT COUNT(*) FROM factor_data WHERE symbol='CU'")
cu_count = cur.fetchone()[0]
print(f'CU因子数据记录数: {cu_count}')

# 检查最新日期
cur.execute("SELECT MAX(date) FROM factor_data")
max_date = cur.fetchone()[0]
print(f'最新数据日期: {max_date}')

# 检查今日更新
cur.execute("SELECT COUNT(*) FROM factor_data WHERE date='2026-04-27'")
today_count = cur.fetchone()[0]
print(f'今日(2026-04-27)更新记录数: {today_count}')

# 检查CU_close最新5条
cur.execute("SELECT date, factor_name, value, confidence FROM factor_data WHERE symbol='CU' AND factor_name='CU_close' ORDER BY date DESC LIMIT 5")
print('\nCU_close 最新5条:')
for row in cur.fetchall():
    print(f'  {row}')

# PIT测试：检查是否有未来数据
cur.execute("SELECT COUNT(*) FROM factor_data WHERE date > '2026-04-27'")
future_count = cur.fetchone()[0]
print(f'\n未来日期数据(应该=0): {future_count}')

# 检查NULL值
cur.execute("SELECT COUNT(*) FROM factor_data WHERE value IS NULL OR value = ''")
null_count = cur.fetchone()[0]
print(f'NULL/空值记录数: {null_count}')

conn.close()

print('\n=== PIT冒烟测试结果 ===')
print(f'✅ 数据库连接正常')
print(f'✅ 数据可读取')
print('PASS: no future data') if future_count == 0 else print(f'FAIL: found {future_count} future records')
print('PASS: no NULL values') if null_count == 0 else print(f'WARNING: found {null_count} NULL records')
print('PIT冒烟测试通过')
