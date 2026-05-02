"""检查 PIT DB 和文件系统中的核心因子"""
import sqlite3, os

DB = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# ic_heatmap 真实列: calc_date, symbol, factor, ic_value, samples, is_mock
print("=== ic_heatmap 完整统计 ===")
cur.execute("SELECT MIN(calc_date), MAX(calc_date), COUNT(DISTINCT symbol), COUNT(DISTINCT factor) FROM ic_heatmap")
r = cur.fetchone()
print(f'  日期: {r[0]} ~ {r[1]}, 品种数: {r[2]}, 因子数: {r[3]}')

cur.execute("SELECT DISTINCT symbol, factor, ic_value, samples, is_mock FROM ic_heatmap ORDER BY symbol, factor")
print("\nic_heatmap 所有记录:")
for r in cur.fetchall():
    print(f'  {r}')

# factor_metadata 完整检查
print("\n=== factor_metadata 全部因子 ===")
cur.execute("SELECT COUNT(*) FROM factor_metadata")
total = cur.fetchone()[0]
print(f'总因子数: {total}')
cur.execute("SELECT factor_code, factor_name, frequency FROM factor_metadata ORDER BY factor_code")
for r in cur.fetchall():
    print(f'  {r}')

# pit_factor_observations 表中是否有 ratio 相关
print("\n=== pit_factor_observations 中的 ratio 因子 ===")
cur.execute("SELECT DISTINCT factor_code FROM pit_factor_observations WHERE factor_code LIKE '%ratio%' OR factor_code LIKE '%Ratio%'")
rows = cur.fetchall()
print(f'共 {len(rows)} 个: {rows}')

# 检查 shared/daily 中的文件
print("\n=== 文件系统中的比价/宏观因子 ===")
shared_dir = r'D:\futures_macro_engine\data\crawlers\shared\daily'
if os.path.exists(shared_dir):
    files = os.listdir(shared_dir)
    ratio_files = [f for f in files if 'ratio' in f.lower() or 'cu_al' in f.lower() or 'au_ag' in f.lower()]
    print(f'  shared/daily 目录共 {len(files)} 个文件')
    for f in ratio_files:
        path = os.path.join(shared_dir, f)
        size = os.path.getsize(path)
        print(f'  {f}: {size} bytes')

# 检查 CU/AL ratio CSV 内容
cu_al_path = r'D:\futures_macro_engine\data\crawlers\shared\daily\CU_AL_ratio.csv'
if os.path.exists(cu_al_path):
    import pandas as pd
    df = pd.read_csv(cu_al_path)
    print(f"\nCU_AL_ratio.csv: {len(df)} 行, 列: {list(df.columns)}")
    print(f"  日期范围: {df.index[0] if hasattr(df,'index') else df.iloc[0,0]} ~ {df.index[-1] if hasattr(df,'index') else df.iloc[-1,0]}")
    print(f"  最新值: {df.iloc[-1].to_dict()}")
else:
    print(f"\nCU_AL_ratio.csv 不存在")

# 检查 AU_AG_ratio_corrected
au_ag_path = r'D:\futures_macro_engine\data\crawlers\_shared\daily\AU_AG_ratio_corrected.csv'
if os.path.exists(au_ag_path):
    import pandas as pd
    df = pd.read_csv(au_ag_path)
    print(f"\nAU_AG_ratio_corrected.csv: {len(df)} 行, 列: {list(df.columns)}")
    print(f"  最新值: {df.iloc[-1].to_dict()}")
else:
    print(f"\nAU_AG_ratio_corrected.csv 不存在")

conn.close()
