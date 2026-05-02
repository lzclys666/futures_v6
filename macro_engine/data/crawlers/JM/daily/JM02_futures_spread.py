# -*- coding: utf-8 -*-
"""
JM02_futures_spread.py
焦煤月差采集脚本
数据源: AKShare - futures_zh_daily_sina

采集因子:
- spread_01: 主力-次主力价差 (如 JM2505-JM2506)
- spread_03: 主力-3月价差 (如 JM2505-JM2509)
- spread_05: 主力-5月价差 (如 JM2505-JM2512)

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

# 合约配置 (主力, 次主力, 3月, 5月)
CONTRACT_PAIRS = [
    ('JM2505', 'JM2506', 'spread_01'),  # 主力-次主力
    ('JM2505', 'JM2509', 'spread_03'),  # 主力-3月
    ('JM2505', 'JM2512', 'spread_05'),  # 主力-5月
]


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


def fetch_contract_data(contract: str) -> pd.DataFrame:
    """获取单个合约数据"""
    try:
        df = ak.futures_zh_daily_sina(symbol=contract)
        if df is None or df.empty:
            return pd.DataFrame()
        
        df = df.copy()
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df['settle'] = pd.to_numeric(df['settle'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        return df[['date', 'settle', 'close']].rename(columns={
            'settle': f'{contract}_settle',
            'close': f'{contract}_close'
        })
    except Exception as e:
        logger.error(f'Error fetching {contract}: {e}')
        return pd.DataFrame()


def calculate_spreads() -> pd.DataFrame:
    """计算月差"""
    all_contracts = set()
    for c1, c2, _ in CONTRACT_PAIRS:
        all_contracts.add(c1)
        all_contracts.add(c2)
    
    # 获取所有合约数据
    contract_data = {}
    for contract in all_contracts:
        df = fetch_contract_data(contract)
        if not df.empty:
            contract_data[contract] = df
            logger.info(f'Fetched {contract}: {len(df)} rows')
        else:
            logger.warning(f'No data for {contract}')
    
    if len(contract_data) < 2:
        logger.error('Insufficient contract data')
        return pd.DataFrame()
    
    # 合并数据并计算价差
    # 以主力合约为基准
    main_contract = 'JM2505'
    if main_contract not in contract_data:
        logger.error(f'Main contract {main_contract} not available')
        return pd.DataFrame()
    
    result_df = contract_data[main_contract].copy()
    
    # 合并其他合约
    for contract, df in contract_data.items():
        if contract != main_contract:
            result_df = result_df.merge(df, on='date', how='outer')
    
    # 按日期排序
    result_df = result_df.sort_values('date').reset_index(drop=True)
    
    # 计算各月差
    spreads = {}
    for c1, c2, spread_name in CONTRACT_PAIRS:
        settle_col1 = f'{c1}_settle'
        settle_col2 = f'{c2}_settle'
        
        if settle_col1 in result_df.columns and settle_col2 in result_df.columns:
            result_df[spread_name] = result_df[settle_col1] - result_df[settle_col2]
            spreads[spread_name] = (c1, c2)
    
    logger.info(f'Calculated spreads: {list(spreads.keys())}')
    return result_df


def validate_spread_data(df: pd.DataFrame) -> bool:
    """校验月差数据"""
    if df.empty:
        logger.error('Empty dataframe')
        return False
    
    # 检查是否有计算的月差列
    spread_cols = ['spread_01', 'spread_03', 'spread_05']
    has_spread = any(c in df.columns for c in spread_cols)
    if not has_spread:
        logger.error('No spread columns found')
        return False
    
    # 检查最新数据
    latest = df.iloc[-1]
    for col in spread_cols:
        if col in latest:
            val = latest[col]
            if pd.notna(val):
                # 月差合理范围 (-500, 500)
                if val < -1000 or val > 1000:
                    logger.warning(f'Unusual {col}: {val}')
                else:
                    logger.info(f'{col}: {val:.2f}')
    
    return True


def save_to_sqlite(df: pd.DataFrame, pub_date: str, obs_date: str):
    """保存到SQLite"""
    if df.empty:
        return
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 创建表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jm_futures_spread (
                pub_date TEXT,
                obs_date TEXT,
                trade_date TEXT,
                spread_01 REAL,
                spread_03 REAL,
                spread_05 REAL,
                PRIMARY KEY (pub_date, trade_date)
            )
        ''')
        
        # 插入数据
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO jm_futures_spread 
                (pub_date, obs_date, trade_date, spread_01, spread_03, spread_05)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                pub_date, obs_date, row['date'],
                row.get('spread_01'), row.get('spread_03'), row.get('spread_05')
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
        filename = OUTPUT_DIR / f'JM02_futures_spread_{pub_date}.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f'Saved to {filename}')
    except Exception as e:
        logger.error(f'CSV save error: {e}')


def main():
    """主函数"""
    logger.info('=== JM02_futures_spread 采集开始 ===')
    
    pub_date, obs_date = get_pit_dates()
    logger.info(f'PIT dates: pub_date={pub_date}, obs_date={obs_date}')
    
    # 计算月差
    df = calculate_spreads()
    
    if df.empty or not validate_spread_data(df):
        logger.error('Data validation failed')
        return False
    
    # 保存数据
    save_to_sqlite(df, pub_date, obs_date)
    save_to_csv(df, pub_date)
    
    # 输出摘要
    logger.info('\n=== 采集摘要 ===')
    latest = df.iloc[-1]
    logger.info(f'数据日期范围: {df["date"].min()} ~ {df["date"].max()}')
    logger.info(f'总数据条数: {len(df)}')
    
    for col in ['spread_01', 'spread_03', 'spread_05']:
        if col in latest and pd.notna(latest[col]):
            logger.info(f'{col}: {latest[col]:.2f}')
    
    logger.info('=== 采集完成 ===')
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
