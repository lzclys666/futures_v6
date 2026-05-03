#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回填历史数据
因子: 待定义 = 回填历史数据

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

WORK_DIR = r'D:\futures_v6\macro_engine'
sys.path.insert(0, os.path.join(WORK_DIR, 'crawlers', 'common'))
os.chdir(WORK_DIR)

import sqlite3
import akshare as ak
import pandas as pd
from datetime import date, timedelta

# ===================== DB写入 =====================
DB_PATH = os.path.join(WORK_DIR, 'pit_data.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def save(conn, factor, symbol, pub_date, obs_date, raw_value, source='akshare_bulk', conf=1.0):
    try:
        conn.execute("""
            INSERT OR REPLACE INTO pit_factor_observations
            (factor_code, symbol, pub_date, obs_date, raw_value, source, source_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [factor, symbol, str(pub_date), str(obs_date), raw_value, source, conf])
    except Exception as e:
        print(f"  [WARN] DB写入失败 {factor}@{obs_date}: {e}")

def ensure_schema(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pit_factor_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factor_code TEXT NOT NULL,
            symbol TEXT NOT NULL,
            pub_date TEXT NOT NULL,
            obs_date TEXT NOT NULL,
            raw_value REAL,
            source TEXT,
            source_confidence REAL,
            UNIQUE(factor_code, symbol, obs_date)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_obs ON pit_factor_observations(factor_code, symbol, obs_date)")
    conn.commit()

# ===================== 数据获取 =====================
def fetch_nr0():
    """NR主力合约历史行情"""
    print("[1/4] 获取NR0历史行情...")
    df = ak.futures_main_sina(symbol="NR0")
    df['obs_date'] = pd.to_datetime(df['日期']).dt.date
    df = df.sort_values('obs_date').reset_index(drop=True)
    df['close'] = pd.to_numeric(df['收盘价'], errors='coerce')
    df['oi'] = pd.to_numeric(df['持仓量'], errors='coerce')
    print(f"    NR0: {len(df)}行, {df['obs_date'].min()} → {df['obs_date'].max()}")
    return df[['obs_date', 'close', 'oi']]

def fetch_ru0():
    """RU主力合约历史行情（用于比价）"""
    print("[2/4] 获取RU0历史行情...")
    df = ak.futures_main_sina(symbol="RU0")
    df['obs_date'] = pd.to_datetime(df['日期']).dt.date
    df = df.sort_values('obs_date').reset_index(drop=True)
    df['close'] = pd.to_numeric(df['收盘价'], errors='coerce')
    print(f"    RU0: {len(df)}行, {df['obs_date'].min()} → {df['obs_date'].max()}")
    return df[['obs_date', 'close']]

def fetch_bdi():
    """BDI波罗的海指数"""
    print("[3/4] 获取BDI历史数据...")
    df = ak.macro_shipping_bdi()
    df['obs_date'] = pd.to_datetime(df['日期']).dt.date
    df = df.sort_values('obs_date').reset_index(drop=True)
    df['bdi'] = pd.to_numeric(df['最新值'], errors='coerce')
    print(f"    BDI: {len(df)}行, {df['obs_date'].min()} → {df['obs_date'].max()}")
    return df[['obs_date', 'bdi']]

def fetch_ine_inventory():
    """INE NR橡胶库存"""
    print("[4/4] 获取INE NR库存...")
    try:
        df = ak.futures_inventory_em(symbol="nr")
        df['obs_date'] = pd.to_datetime(df['日期']).dt.date
        df = df.sort_values('obs_date').reset_index(drop=True)
        df['inv'] = pd.to_numeric(df['库存'], errors='coerce')
        print(f"    INE库存: {len(df)}行, {df['obs_date'].min()} → {df['obs_date'].max()}")
        return df[['obs_date', 'inv']]
    except Exception as e:
        print(f"    INE库存获取失败: {e}")
        return pd.DataFrame(columns=['obs_date', 'inv'])

# ===================== 主回填逻辑 =====================
def main():
    START = date(2023, 1, 1)
    END = date(2026, 4, 17)
    SYMBOL = "NR"

    print("=" * 55)
    print(f"NR历史数据回填  {START} → {END}")
    print("=" * 55)

    conn = get_connection()
    ensure_schema(conn)

    # 批量获取数据
    nr0 = fetch_nr0()
    ru0 = fetch_ru0()
    bdi = fetch_bdi()
    inv = fetch_ine_inventory()

    # 合并NR0 + RU0
    merged = nr0.merge(ru0, on='obs_date', how='left', suffixes=('_nr', '_ru'))

    # BDI和库存也merge进来
    merged = merged.merge(bdi, on='obs_date', how='left')

    # 只保留回填区间
    merged = merged[(merged['obs_date'] >= START) & (merged['obs_date'] <= END)]

    # 过滤交易日期（NR价格不为空）
    merged = merged.dropna(subset=['close_nr'])

    print(f"\n写入区间: {START} → {END}, 可交易天数: {len(merged)}")

    total = 0
    for _, row in merged.iterrows():
        obs = row['obs_date']
        pub = obs  # pub_date=obs_date (回填规范)

        # NR_FUT_CLOSE
        if pd.notna(row['close_nr']):
            v = float(row['close_nr'])
            if 8000 <= v <= 30000:
                save(conn, "NR_FUT_CLOSE", SYMBOL, pub, obs, v, "NR0_akshare", 1.0)
                total += 1

        # NR_POS_OPEN_INT (持仓量)
        if pd.notna(row['oi']):
            v = float(row['oi'])
            if 5000 <= v <= 300000:
                save(conn, "NR_POS_OPEN_INT", SYMBOL, pub, obs, v, "NR0_akshare", 1.0)
                total += 1

        # NR_FUT_OI (同持仓量)
        if pd.notna(row['oi']):
            v = float(row['oi'])
            if 5000 <= v <= 300000:
                save(conn, "NR_FUT_OI", SYMBOL, pub, obs, v, "NR0_akshare", 1.0)
                total += 1

        # NR_SPD_CONTRACT (收盘价)
        if pd.notna(row['close_nr']):
            v = float(row['close_nr'])
            if 8000 <= v <= 30000:
                save(conn, "NR_SPD_CONTRACT", SYMBOL, pub, obs, v, "NR0_akshare", 0.9)
                total += 1

        # NR_SPD_RU_NR (比价)
        if pd.notna(row['close_nr']) and pd.notna(row['close_ru']):
            nr_v = float(row['close_nr'])
            ru_v = float(row['close_ru'])
            if ru_v > 0:
                ratio = round(nr_v / ru_v, 4)
                if 0.5 <= ratio <= 1.5:
                    save(conn, "NR_SPD_RU_NR", SYMBOL, pub, obs, ratio, "NR0+RU0_akshare", 1.0)
                    total += 1

        # NR_FREIGHT_BDI
        if pd.notna(row['bdi']):
            v = float(row['bdi'])
            if 200 <= v <= 15000:
                save(conn, "NR_FREIGHT_BDI", SYMBOL, pub, obs, v, "BDI_akshare", 1.0)
                total += 1

    # INE NR库存单独写（库存数据较短，单独处理）
    for _, row in inv.iterrows():
        obs = row['obs_date']
        if obs < START or obs > END:
            continue
        if pd.notna(row['inv']):
            v = float(row['inv'])
            if 5000 <= v <= 200000:
                save(conn, "NR_INV_TOTAL", SYMBOL, obs, obs, v, "INE_inventory_akshare", 1.0)
                total += 1

    conn.commit()

    # 验证结果
    cur = conn.cursor()
    cur.execute("""
        SELECT factor_code, MIN(obs_date), MAX(obs_date), COUNT(*)
        FROM pit_factor_observations
        WHERE symbol=? AND obs_date>=?
        GROUP BY factor_code ORDER BY factor_code
    """, [SYMBOL, str(START)])
    print("\n写入结果:")
    print(f"{'因子':<25} {'起始':<12} {'结束':<12} {'行数':>6}")
    print("-" * 60)
    for r in cur.fetchall():
        print(f"{r[0]:<25} {r[1]:<12} {r[2]:<12} {r[3]:>6}")
    print(f"\n总写入: {total}行")
    conn.close()

if __name__ == "__main__":
    main()
