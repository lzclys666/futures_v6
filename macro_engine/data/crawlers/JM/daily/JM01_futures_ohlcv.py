# -*- coding: utf-8 -*-
"""
JM01_futures_ohlcv.py
焦煤期货日行情（OHLCV）采集脚本
数据源: AKShare - futures_zh_daily_sina

采集因子:
- open: 开盘价
- high: 最高价  
- low: 最低价
- close: 收盘价
- volume: 成交量
- hold: 持仓量
- settle: 结算价

PIT规范:
- pub_date: 脚本运行日期
- obs_date: 数据观测日期（交易日）
"""

import os
import sys
import json
import sqlite3
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(r'D:\futures_v6\macro_engine')
sys.path.insert(0, str(PROJECT_ROOT))

import akshare as ak

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置
DB_PATH = PROJECT_ROOT / 'pit_data.db'
OUTPUT_DIR = PROJECT_ROOT / 'data' / 'crawlers' / 'JM' / 'daily'
CONTRACTS = ['JM2505', 'JM2506', 'JM2507', 'JM2509', 'JM2512', 'JM2601']  # 主力合约列表


def get_pit_dates():
    """获取PIT日期"""
    today = datetime.now()
    pub_date = today.strftime('%Y-%m-%d')
    
    # 计算obs_date: 周一回退到上周五
    weekday = today.weekday()
    if weekday == 0:  # 周一
        obs_date = (today - timedelta(days=3)).strftime('%Y-%m-%d')
    elif weekday == 6:  # 周日
        obs_date = (today - timedelta(days=2)).strftime('%Y-%m-%d')
    else:
        obs_date = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    
    return pub_date, obs_date


def fetch_jm_ohlcv(contract: str) -> pd.DataFrame:
    """
    获取焦煤期货日行情数据
    
    Args:
        contract: 合约代码，如 JM2505
        
    Returns:
        DataFrame with OHLCV data
    """
    try:
        df = ak.futures_zh_daily_sina(symbol=contract)
        if df is None or df.empty:
            logger.warning(f'No data returned for {contract}')
            return pd.DataFrame()
        
        # 数据清洗
        df = df.copy()
        df['contract'] = contract
        df['variety'] = 'JM'
        
        # 确保数值类型
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'hold', 'settle']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 日期格式统一
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        logger.info(f'Fetched {len(df)} rows for {contract}')
        return df
        
    except Exception as e:
        logger.error(f'Error fetching {contract}: {e}')
        return pd.DataFrame()


def validate_data(df: pd.DataFrame) -> bool:
    """数据合理性校验"""
    if df.empty:
        logger.error('Empty dataframe')
        return False
    
    # 检查必要列
    required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        logger.error(f'Missing columns: {missing_cols}')
        return False
    
    # 价格范围校验 (焦煤正常价格区间 500-3000)
    latest = df.iloc[-1]
    for col in ['open', 'high', 'low', 'close']:
        if col in latest:
            val = latest[col]
            if pd.isna(val) or val < 100 or val > 5000:
                logger.error(f'Invalid {col}: {val}')
                return False
    
    # 成交量非负
    if latest.get('volume', 0) < 0:
        logger.error(f'Negative volume: {latest.get("volume")}')
        return False
    
    logger.info('Data validation passed')
    return True


def save_to_sqlite(df: pd.DataFrame, pub_date: str, obs_date: str):
    """保存数据到SQLite"""
    if df.empty:
        return
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 创建表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jm_futures_ohlcv (
                pub_date TEXT,
                obs_date TEXT,
                contract TEXT,
                trade_date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                hold INTEGER,
                settle REAL,
                PRIMARY KEY (pub_date, contract, trade_date)
            )
        ''')
        
        # 插入数据
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO jm_futures_ohlcv 
                (pub_date, obs_date, contract, trade_date, open, high, low, close, volume, hold, settle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pub_date, obs_date, row['contract'], row['date'],
                row.get('open'), row.get('high'), row.get('low'), 
                row.get('close'), row.get('volume'), row.get('hold'), row.get('settle')
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
    """保存数据到CSV备份"""
    if df.empty:
        return
    
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filename = OUTPUT_DIR / f'JM01_futures_ohlcv_{pub_date}.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f'Saved to {filename}')
    except Exception as e:
        logger.error(f'CSV save error: {e}')


def main():
    """主函数"""
    logger.info('=== JM01_futures_ohlcv 采集开始 ===')
    
    pub_date, obs_date = get_pit_dates()
    logger.info(f'PIT dates: pub_date={pub_date}, obs_date={obs_date}')
    
    all_data = []
    
    # 采集各合约数据
    for contract in CONTRACTS:
        df = fetch_jm_ohlcv(contract)
        if not df.empty and validate_data(df):
            all_data.append(df)
        else:
            logger.warning(f'Skipping invalid data for {contract}')
    
    if not all_data:
        logger.error('No valid data collected')
        return False
    
    # 合并数据
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # 保存数据
    save_to_sqlite(combined_df, pub_date, obs_date)
    save_to_csv(combined_df, pub_date)
    
    # 输出摘要
    logger.info('\n=== 采集摘要 ===')
    logger.info(f'合约数: {len(all_data)}')
    logger.info(f'总数据条数: {len(combined_df)}')
    for contract in combined_df['contract'].unique():
        contract_df = combined_df[combined_df['contract'] == contract]
        latest = contract_df.iloc[-1]
        logger.info(f'{contract}: 最新日期={latest["date"]}, 收盘={latest["close"]}, 持仓={latest["hold"]}')
    
    logger.info('=== 采集完成 ===')
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
