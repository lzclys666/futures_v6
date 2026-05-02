# -*- coding: utf-8 -*-
"""
JM04_futures_hold_volume.py
焦煤期货持仓量采集脚本
数据源: AKShare - futures_zh_daily_sina (日行情中的hold字段)

采集因子:
- hold_volume: 持仓量（手）
- hold_change: 持仓量变化（相比上一日）

PIT规范:
- pub_date: 脚本运行日期
- obs_date: 数据观测日期（交易日）
"""

import os
import sys
import sqlite3
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(r'D:\futures_v6\macro_engine')
sys.path.insert(0, str(PROJECT_ROOT))

import akshare as ak

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = PROJECT_ROOT / 'pit_data.db'
OUTPUT_DIR = PROJECT_ROOT / 'data' / 'crawlers' / 'JM' / 'daily'
CONTRACTS = ['JM2505', 'JM2506', 'JM2507', 'JM2509', 'JM2512', 'JM2601']


def get_pit_dates():
    """获取PIT日期"""
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


def fetch_hold_volume(contract: str) -> pd.DataFrame:
    """获取持仓量数据"""
    try:
        df = ak.futures_zh_daily_sina(symbol=contract)
        if df is None or df.empty:
            return pd.DataFrame()
        
        df = df.copy()
        df['contract'] = contract
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df['hold'] = pd.to_numeric(df['hold'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        
        # 计算持仓变化
        df['hold_change'] = df['hold'].diff()
        
        return df[['date', 'contract', 'hold', 'hold_change', 'volume']]
    except Exception as e:
        logger.error(f'Error fetching {contract}: {e}')
        return pd.DataFrame()


def validate_data(df: pd.DataFrame) -> bool:
    """数据校验"""
    if df.empty:
        logger.error('Empty dataframe')
        return False
    
    latest = df.iloc[-1]
    if pd.isna(latest.get('hold')):
        logger.error('Missing hold volume')
        return False
    
    hold = latest['hold']
    if hold < 0 or hold > 1000000:
        logger.error(f'Invalid hold volume: {hold}')
        return False
    
    logger.info(f'Hold volume validation passed: {hold}')
    return True


def save_to_sqlite(df: pd.DataFrame, pub_date: str, obs_date: str):
    """保存到SQLite"""
    if df.empty:
        return
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jm_futures_hold_volume (
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
        
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO jm_futures_hold_volume 
                (pub_date, obs_date, contract, trade_date, hold_volume, hold_change, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                pub_date, obs_date, row['contract'], row['date'],
                int(row['hold']) if pd.notna(row['hold']) else None,
                int(row['hold_change']) if pd.notna(row['hold_change']) else None,
                int(row['volume']) if pd.notna(row['volume']) else None
            ))
        
        conn.commit()
        logger.info(f'Saved {len(df)} rows to database')
    except Exception as e:
        logger.error(f'Database error: {e}')
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def save_to_csv(df: pd.DataFrame, pub_date: str):
    """保存到CSV"""
    if df.empty:
        return
    
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filename = OUTPUT_DIR / f'JM04_futures_hold_volume_{pub_date}.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f'Saved to {filename}')
    except Exception as e:
        logger.error(f'CSV save error: {e}')


def main():
    """主函数"""
    logger.info('=== JM04_futures_hold_volume 采集开始 ===')
    
    pub_date, obs_date = get_pit_dates()
    logger.info(f'PIT dates: pub_date={pub_date}, obs_date={obs_date}')
    
    all_data = []
    
    for contract in CONTRACTS:
        df = fetch_hold_volume(contract)
        if not df.empty and validate_data(df):
            all_data.append(df)
            latest = df.iloc[-1]
            logger.info(f'{contract}: hold={latest["hold"]}, change={latest["hold_change"]}')
        else:
            logger.warning(f'Skipping invalid data for {contract}')
    
    if not all_data:
        logger.error('No valid data collected')
        return False
    
    combined_df = pd.concat(all_data, ignore_index=True)
    
    save_to_sqlite(combined_df, pub_date, obs_date)
    save_to_csv(combined_df, pub_date)
    
    logger.info('\n=== 采集摘要 ===')
    logger.info(f'合约数: {len(all_data)}')
    logger.info(f'总数据条数: {len(combined_df)}')
    logger.info('=== 采集完成 ===')
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
