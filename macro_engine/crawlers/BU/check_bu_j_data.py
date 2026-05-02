#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_bu_j_data
因子: 待定义 = check_bu_j_data

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
cursor = conn.cursor()

cursor.execute("SELECT factor_code, symbol, obs_date, raw_value, source, source_confidence FROM pit_factor_observations WHERE symbol='BU' AND raw_value IS NOT NULL ORDER BY obs_date DESC, factor_code LIMIT 20")
bu_rows = cursor.fetchall()
print('=== BU Recent Data ===')
for row in bu_rows:
    print(f'  {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | conf={row[5]}')

cursor.execute("SELECT factor_code, symbol, obs_date, raw_value, source, source_confidence FROM pit_factor_observations WHERE symbol='J' AND raw_value IS NOT NULL ORDER BY obs_date DESC, factor_code LIMIT 20")
j_rows = cursor.fetchall()
print()
print('=== J Recent Data ===')
for row in j_rows:
    print(f'  {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | conf={row[5]}')

cursor.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE symbol='BU' AND raw_value IS NOT NULL")
bu_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE symbol='J' AND raw_value IS NOT NULL")
j_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(DISTINCT factor_code) FROM pit_factor_observations WHERE symbol='BU' AND raw_value IS NOT NULL")
bu_factors = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(DISTINCT factor_code) FROM pit_factor_observations WHERE symbol='J' AND raw_value IS NOT NULL")
j_factors = cursor.fetchone()[0]
print()
print(f'BU factors: {bu_factors}, total rows: {bu_count}')
print(f'J factors: {j_factors}, total rows: {j_count}')
conn.close()
