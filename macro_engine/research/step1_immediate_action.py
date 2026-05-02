import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime

print("=" * 80)
print("第一步：立即执行 - 失效品种处理")
print("=" * 80)

# 连接参数数据库
db_path = r'D:\futures_v6\macro_engine\data\parameter_db.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 标记失效品种
print("\n[1] 标记失效品种...")
failed_varieties = ['SN', 'AO', 'LC', 'AU', 'M', 'BR']

for variety in failed_varieties:
    # 更新状态为失效
    cursor.execute('''
        UPDATE optimal_parameters 
        SET weight_decay = 0.0, updated_at = ?
        WHERE variety = ? AND factor = 'momentum'
    ''', (datetime.now(), variety))
    
    print(f"  [OK] {variety} 已标记为失效（权重设为0）")

# 2. 对SN、AO、LC设置特殊权重（20%）
print("\n[2] 设置降低权重品种...")
reduce_weight_varieties = ['SN', 'LC']

for variety in reduce_weight_varieties:
    cursor.execute('''
        UPDATE optimal_parameters 
        SET weight_decay = 0.2, updated_at = ?
        WHERE variety = ? AND factor = 'momentum'
    ''', (datetime.now(), variety))
    
    print(f"  [OK] {variety} 权重降至20%")

# 3. 验证更新
print("\n[3] 验证数据库更新...")
cursor.execute('''
    SELECT variety, factor, ic_window, hold_period, weight_decay, ir, updated_at
    FROM optimal_parameters
    WHERE variety IN ('SN', 'AO', 'LC', 'AU', 'M', 'BR')
    ORDER BY variety
''')

results = cursor.fetchall()
print("\n| 品种 | 因子 | IC窗口 | 持有期 | 权重 | IR | 更新时间 |")
print("|------|------|--------|--------|------|-----|----------|")
for row in results:
    print(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]:.4f} | {row[6]} |")

conn.commit()
conn.close()

print("\n[OK] 第一步完成！")
print("\n已处理品种：")
print("  - SN: 权重降至20%")
print("  - LC: 权重降至20%")
print("  - AO: 暂停交易（权重=0）")
print("  - AU: 暂停交易（权重=0）")
print("  - M: 暂停交易（权重=0）")
print("  - BR: 暂停交易（权重=0）")

print("\n" + "=" * 80)
print("下一步：开发新因子（AU、M）或测试反转信号（BR）")
print("=" * 80)
