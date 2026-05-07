"""
Stage 2: 注册 CU_AL_ratio 到 PIT DB
"""
import sqlite3
import pandas as pd

conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')

# 1. 写入 factor_metadata
print("=== 1. 注册 CU_AL_ratio 到 factor_metadata ===")
meta_insert = """
INSERT OR REPLACE INTO factor_metadata 
(factor_code, factor_name, direction, frequency, norm_method, is_active)
VALUES (?, ?, ?, ?, ?, ?)
"""
conn.execute(meta_insert, (
    'CU_AL_ratio',
    'CU/AL 期货价比 (沪铜/沪铝)',
    1,      # direction=1: ratio UP -> CU_ret UP (IC=+0.283)
    'daily',
    'mad',
    1
))
conn.commit()
print("  factor_metadata 写入完成")

# 2. 读取 CSV
ratio_df = pd.read_csv(
    r'D:\futures_v6\macro_engine\data\crawlers\shared\daily\CU_AL_ratio.csv',
    parse_dates=['date']
)
print("  CSV 行数: {}".format(len(ratio_df)))

# 3. 写入 pit_factor_observations
print("=== 2. 写入 pit_factor_observations ===")

# 获取交易日历（用于计算 pub_date = 下一个交易日）
trading_days = pd.read_sql(
    "SELECT DISTINCT obs_date FROM pit_factor_observations WHERE factor_code='CU_FUT_CLOSE' ORDER BY obs_date",
    conn
)['obs_date'].tolist()

obs_rows = []
for _, row in ratio_df.iterrows():
    obs_date_str = row['date'].strftime('%Y-%m-%d')
    # PIT 合规：pub_date = 下一个交易日（数据当日收盘后计算，次日可用）
    try:
        idx = trading_days.index(obs_date_str)
        pub_date_str = trading_days[idx + 1] if idx + 1 < len(trading_days) else obs_date_str
    except ValueError:
        from datetime import timedelta
        pub_date_str = (row['date'] + timedelta(days=1)).strftime('%Y-%m-%d')
    obs_rows.append((
        'CU_AL_ratio',
        'CU',                 # symbol: 第一个品种
        pub_date_str,
        obs_date_str,
        float(row['ratio']),
        'CU_AL_ratio_csv',
        0.95                 # source_confidence: CSV 手工计算，置信度 0.95
    ))

conn.executemany(
    "INSERT OR IGNORE INTO pit_factor_observations "
    "(factor_code, symbol, pub_date, obs_date, raw_value, source, source_confidence) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)",
    obs_rows
)
conn.commit()

# 4. 验证
print("=== 3. 验证 ===")
count = pd.read_sql(
    "SELECT COUNT(*) as cnt FROM pit_factor_observations WHERE factor_code='CU_AL_ratio'",
    conn
)['cnt'][0]
print("  写入行数: {}".format(count))

recent = pd.read_sql(
    "SELECT * FROM pit_factor_observations WHERE factor_code='CU_AL_ratio' "
    "ORDER BY obs_date DESC LIMIT 5",
    conn
)
print("  最新5条:")
print(recent.to_string())

oldest = pd.read_sql(
    "SELECT obs_date, raw_value FROM pit_factor_observations WHERE factor_code='CU_AL_ratio' "
    "ORDER BY obs_date ASC LIMIT 3",
    conn
)
print("  最早3条:")
print(oldest.to_string())

conn.close()
print("\n=== 完成 ===")
