# -*- coding: utf-8 -*-
"""
collect_real_factors.py
多品种因子采集脚本 (Step 1: spread + hold_volume)
基于 JM02/JM04 脚本通用化, 数据源: AKShare

覆盖品种: JM, RU, RB, ZN, NI
采集因子:
  - 月差 (spread): 主力 vs 近月/3月/5月
  - 持仓量 (hold_volume): 多合约持仓量

PIT 规范:
  - pub_date: 脚本运行日期
  - obs_date: 数据观测日期（最近的交易日）

用法:
  python collect_real_factors.py [--variety JM] [--factor spread|hold_volume|all]
"""

import os
import sys
import sqlite3
import logging
import argparse
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录
PROJECT_ROOT = Path(r'D:\futures_v6\macro_engine')
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import akshare as ak
except ImportError:
    print("[FATAL] AKShare not installed. Run: pip install akshare")
    sys.exit(1)

# 日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = Path(r'D:\futures_v6\macro_engine\pit_data.db')

# ============================================================
# 品种配置
# ============================================================
VARIETY_CONFIG = {
    "JM": {
        "name": "焦煤",
        "main": "JM2505",
        "spread_contracts": {"near": "JM2506", "m3": "JM2509", "m5": "JM2512"},
        "hold_contracts": ["JM2505", "JM2506", "JM2507", "JM2509", "JM2512", "JM2601"],
    },
    "RU": {
        "name": "橡胶",
        "main": "RU2505",
        "spread_contracts": {"near": "RU2506", "m3": "RU2509", "m5": "RU2511"},
        "hold_contracts": ["RU2505", "RU2506", "RU2509", "RU2511", "RU2601"],
    },
    "RB": {
        "name": "螺纹钢",
        "main": "RB2505",
        "spread_contracts": {"near": "RB2506", "m3": "RB2510", "m5": "RB2601"},
        "hold_contracts": ["RB2505", "RB2506", "RB2507", "RB2510", "RB2601"],
    },
    "ZN": {
        "name": "沪锌",
        "main": "ZN2505",
        "spread_contracts": {"near": "ZN2506", "m3": "ZN2508", "m5": "ZN2510"},
        "hold_contracts": ["ZN2505", "ZN2506", "ZN2507", "ZN2508", "ZN2509", "ZN2510"],
    },
    "NI": {
        "name": "沪镍",
        "main": "NI2505",
        "spread_contracts": {"near": "NI2506", "m3": "NI2508", "m5": "NI2510"},
        "hold_contracts": ["NI2505", "NI2506", "NI2507", "NI2508", "NI2509", "NI2510"],
    },
}


# ============================================================
# 工具函数
# ============================================================

def get_pit_dates():
    """获取 PIT 日期"""
    today = datetime.now()
    pub_date = today.strftime('%Y-%m-%d')
    weekday = today.weekday()
    if weekday == 0:
        obs_date = (today - timedelta(days=3)).strftime('%Y-%m-%d')
    elif weekday == 6:
        obs_date = (today - timedelta(days=2)).strftime('%Y-%m-%d')
    else:
        obs_date = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    return pub_date, obs_date


def fetch_contract_data(contract: str) -> pd.DataFrame:
    """
    获取单个合约的日行情 (AKShare futures_zh_daily_sina)
    返回标准化列: date, open, high, low, close, settle, hold, volume
    """
    try:
        df = ak.futures_zh_daily_sina(symbol=contract)
        if df is None or df.empty:
            logger.warning(f'{contract}: no data returned')
            return pd.DataFrame()

        df = df.copy()
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        for col in ['open', 'high', 'low', 'close', 'settle', 'hold', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        logger.error(f'{contract}: fetch failed - {e}')
        return pd.DataFrame()


def get_db_conn():
    """获取数据库连接"""
    return sqlite3.connect(str(DB_PATH), timeout=30)


# ============================================================
# 月差采集 (对应原 JM02)
# ============================================================

def collect_spread(symbol: str) -> bool:
    """
    采集 {symbol} 的月差数据
    输出表: {symbol_lower}_futures_spread
    """
    cfg = VARIETY_CONFIG[symbol]
    main = cfg["main"]
    near = cfg["spread_contracts"]["near"]
    m3 = cfg["spread_contracts"]["m3"]
    m5 = cfg["spread_contracts"]["m5"]

    logger.info(f'=== [{symbol}] 月差采集: {main} vs ({near}, {m3}, {m5}) ===')

    pub_date, obs_date = get_pit_dates()
    logger.info(f'PIT: pub={pub_date}, obs={obs_date}')

    # 获取所有合约数据
    need = [main, near, m3, m5]
    contract_dfs = {}
    for c in need:
        df = fetch_contract_data(c)
        if not df.empty:
            contract_dfs[c] = df
            logger.info(f'  {c}: {len(df)} rows, {df["date"].min()} ~ {df["date"].max()}')

    if main not in contract_dfs:
        logger.error(f'{symbol}: main contract {main} unavailable')
        return False

    # 以主力合约为基准 merge
    result = contract_dfs[main][['date', 'settle']].copy()
    result = result.rename(columns={'settle': f'{main}_settle'})

    for c in [near, m3, m5]:
        if c in contract_dfs:
            sub = contract_dfs[c][['date', 'settle']].rename(columns={'settle': f'{c}_settle'})
            result = result.merge(sub, on='date', how='outer')

    result = result.sort_values('date').reset_index(drop=True)

    # 计算月差 (主力 - 远月)
    labels = {near: "spread_01", m3: "spread_03", m5: "spread_05"}
    for c, label in labels.items():
        col = f'{c}_settle'
        if col in result.columns and f'{main}_settle' in result.columns:
            result[label] = result[f'{main}_settle'] - result[col]

    # 统计
    for col_name in labels.values():
        if col_name in result.columns:
            valid = result[col_name].dropna()
            if len(valid) > 0:
                logger.info(f'  {col_name}: mean={valid.mean():.2f}, std={valid.std():.2f}, n={len(valid)}')
            else:
                logger.warning(f'  {col_name}: all NaN')

    # 写入数据库
    table = f'{symbol.lower()}_futures_spread'
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {table} (
                pub_date TEXT,
                obs_date TEXT,
                trade_date TEXT,
                spread_01 REAL,
                spread_03 REAL,
                spread_05 REAL,
                PRIMARY KEY (pub_date, trade_date)
            )
        ''')
        for _, row in result.iterrows():
            cur.execute(f'''
                INSERT OR REPLACE INTO {table}
                (pub_date, obs_date, trade_date, spread_01, spread_03, spread_05)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                pub_date, obs_date, row['date'],
                row.get('spread_01'), row.get('spread_03'), row.get('spread_05')
            ))
        conn.commit()
        conn.close()
        logger.info(f'{symbol}: saved {len(result)} rows -> {table}')
    except Exception as e:
        logger.error(f'{symbol}: DB write failed - {e}')
        return False

    logger.info(f'{symbol}: spread collection DONE OK')
    return True


# ============================================================
# 持仓量采集 (对应原 JM04)
# ============================================================

def collect_hold_volume(symbol: str) -> bool:
    """
    采集 {symbol} 的多合约持仓量数据
    输出表: {symbol_lower}_futures_hold_volume
    """
    cfg = VARIETY_CONFIG[symbol]
    contracts = cfg["hold_contracts"]

    logger.info(f'=== [{symbol}] 持仓量采集: {len(contracts)} contracts ===')

    pub_date, obs_date = get_pit_dates()
    logger.info(f'PIT: pub={pub_date}, obs={obs_date}')

    all_data = []
    for c in contracts:
        df = fetch_contract_data(c)
        if df.empty:
            logger.warning(f'{symbol}/{c}: skip (no data)')
            continue
        df['contract'] = c
        # 计算持仓变化
        df['hold_change'] = df['hold'].diff()
        all_data.append(df[['date', 'contract', 'hold', 'hold_change', 'volume']])
        latest = df.iloc[-1]
        logger.info(f'  {c}: hold={latest.get("hold","?")}, date={latest.get("date","?")}')

    if not all_data:
        logger.error(f'{symbol}: no contract data collected')
        return False

    combined = pd.concat(all_data, ignore_index=True)

    # 写入数据库
    table = f'{symbol.lower()}_futures_hold_volume'
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {table} (
                pub_date TEXT,
                obs_date TEXT,
                contract TEXT,
                trade_date TEXT,
                hold_volume INTEGER,
                hold_change INTEGER,
                volume INTEGER,
                PRIMARY KEY (pub_date, contract, trade_date)
            )
        ''')
        for _, row in combined.iterrows():
            cur.execute(f'''
                INSERT OR REPLACE INTO {table}
                (pub_date, obs_date, contract, trade_date, hold_volume, hold_change, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                pub_date, obs_date, row['contract'], row['date'],
                int(row['hold']) if pd.notna(row['hold']) else None,
                int(row['hold_change']) if pd.notna(row['hold_change']) else None,
                int(row['volume']) if pd.notna(row['volume']) else None
            ))
        conn.commit()
        conn.close()
        logger.info(f'{symbol}: saved {len(combined)} rows -> {table}')
    except Exception as e:
        logger.error(f'{symbol}: DB write failed - {e}')
        return False

    logger.info(f'{symbol}: hold_volume collection DONE OK')
    return True


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='多品种因子采集脚本 (Step 1)')
    parser.add_argument('--variety', '-v', nargs='+', default=list(VARIETY_CONFIG.keys()),
                        choices=list(VARIETY_CONFIG.keys()),
                        help=f'品种列表 (默认全部: {list(VARIETY_CONFIG.keys())})')
    parser.add_argument('--factor', '-f', default='all',
                        choices=['spread', 'hold_volume', 'all'],
                        help='采集因子类型 (默认 all)')
    args = parser.parse_args()

    logger.info('=' * 60)
    logger.info('多品种因子采集 (Step 1: spread + hold_volume)')
    logger.info(f'品种: {args.variety}  因子: {args.factor}')
    logger.info('=' * 60)

    results = {s: {"spread": None, "hold_volume": None} for s in args.variety}

    for symbol in args.variety:
        if symbol not in VARIETY_CONFIG:
            logger.error(f'Unknown variety: {symbol}')
            continue

        if args.factor in ('spread', 'all'):
            results[symbol]['spread'] = collect_spread(symbol)

        if args.factor in ('hold_volume', 'all'):
            results[symbol]['hold_volume'] = collect_hold_volume(symbol)

    # 汇总报告
    logger.info('')
    logger.info('=' * 60)
    logger.info('采集汇总')
    logger.info('=' * 60)
    for sym, res in results.items():
        spread_ok = 'OK' if res['spread'] else ('FAIL' if res['spread'] is False else '-')
        hv_ok = 'OK' if res['hold_volume'] else ('FAIL' if res['hold_volume'] is False else '-')
        logger.info(f'  {sym} ({VARIETY_CONFIG[sym]["name"]}): spread={spread_ok}  hold_vol={hv_ok}')

    logger.info('=' * 60)
    logger.info('完成')
    logger.info('=' * 60)


if __name__ == '__main__':
    main()
