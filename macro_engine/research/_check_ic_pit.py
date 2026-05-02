"""检查 PIT DB 中的 IC 数据和 CU/AL 比价因子"""
import sqlite3

DB = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# 1. 检查 ic_heatmap 表
print("=== ic_heatmap 表结构 ===")
cur.execute("PRAGMA table_info(ic_heatmap)")
for r in cur.fetchall():
    print(f'  {r}')

cur.execute("SELECT COUNT(*) FROM ic_heatmap")
count = cur.fetchone()[0]
print(f'  共 {count} 条记录\n')

# 抽样看内容
cur.execute("SELECT * FROM ic_heatmap LIMIT 5")
rows = cur.fetchall()
print("ic_heatmap 示例:")
for r in rows:
    print(f'  {r}')

# 2. 检查 factor_metadata 表中是否有 CU/AL 相关因子
print("\n=== 因子元数据 ===")
cur.execute("SELECT factor_code, factor_name, frequency, is_active FROM factor_metadata LIMIT 20")
for r in cur.fetchall():
    print(f'  {r}')

# 3. 查找 CU/AL 相关记录
print("\n=== 搜索 CU/AL 相关因子 ===")
cur.execute("SELECT * FROM factor_metadata WHERE factor_code LIKE '%CU%' OR factor_name LIKE '%CU%' OR factor_code LIKE '%AL%' OR factor_name LIKE '%AL%'")
for r in cur.fetchall():
    print(f'  {r}')

# 4. 搜索 ratio 相关因子
print("\n=== 搜索 ratio 相关因子 ===")
cur.execute("SELECT * FROM factor_metadata WHERE factor_code LIKE '%ratio%' OR factor_name LIKE '%ratio%'")
for r in cur.fetchall():
    print(f'  {r}')

# 5. 搜索金银比
print("\n=== 搜索 AU/AG 相关因子 ===")
cur.execute("SELECT * FROM factor_metadata WHERE factor_code LIKE '%AU%' OR factor_name LIKE '%AU%' OR factor_code LIKE '%AG%' OR factor_name LIKE '%AG%'")
for r in cur.fetchall():
    print(f'  {r}')

# 6. 统计总因子数和活跃因子数
cur.execute("SELECT COUNT(*), SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END) FROM factor_metadata")
r = cur.fetchone()
print(f"\n因子总数: {r[0]}, 活跃: {r[1]}")

# 7. 检查 ic_heatmap 是否有 IC 值
print("\n=== ic_heatmap 统计 ===")
cur.execute("SELECT MIN(calc_date), MAX(calc_date), COUNT(DISTINCT factor_code) FROM ic_heatmap")
r = cur.fetchone()
print(f'  日期范围: {r[0]} ~ {r[1]}, 因子数: {r[2]}')

# 8. ic_heatmap 中有哪些因子
cur.execute("SELECT DISTINCT factor_code FROM ic_heatmap ORDER BY factor_code LIMIT 30")
print("\nic_heatmap 中的因子:")
for r in cur.fetchall():
    print(f'  {r[0]}')

conn.close()
