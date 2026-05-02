# -*- coding: utf-8 -*-
"""
JM05_basis_volatility.py
焦煤基差波动率采集脚本
数据源: 基于JM03基差数据计算

采集因子:
- basis_vol_5d: 5日基差波动率 (标准差/均值)
- basis_vol_10d: 10日基差波动率
- basis_vol_20d: 20日基差波动率

说明:
- 依赖JM03的基差数据
- 如基差数据缺失，波动率将标记为NULL

PIT规范:
- pub_date: 脚本运行日期
- obs_date: 数据观测日期（交易日）
"""

import os
import sys
import sqlite3
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(r'D:\futures_v6\macro_engine')
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = PROJECT_ROOT / 'pit_data.db'
OUTPUT_DIR = PROJECT_ROOT / 'data' / 'crawlers' / 'JM' / 'daily'


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


def load_basis_data() -> pd.DataFrame:
    """从数据库加载基差数据"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT trade_date, basis 
            FROM jm_futures_basis 
            WHERE basis IS NOT NULL 
            ORDER BY trade_date
        """
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            logger.warning('No basis data found in database')
        else:
            logger.info(f'Loaded {len(df)} rows of basis data')
            
        return df
    except Exception as e:
        logger.error(f'Error loading basis data: {e}')
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def calculate_volatility(df: pd.DataFrame) -> pd.DataFrame:
    """计算基差波动率"""
    if df.empty:
        return pd.DataFrame()
    
    df = df.copy()
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df.sort_values('trade_date').reset_index(drop=True)
    
    # 计算不同周期的波动率
    windows = [5, 10, 20]
    
    for window in windows:
        col_name = f'basis_vol_{window}d'
        
        # 使用滚动窗口计算标准差/均值
        rolling_std = df['basis'].rolling(window=window, min_periods=3).std()
        rolling_mean = df['basis'].rolling(window=window, min_periods=3).mean()
        
        # 变异系数 (CV) = 标准差 / |均值|
        df[col_name] = np.where(
            rolling_mean.abs() > 0.001,  # 避免除以0
            rolling_std / rolling_mean.abs(),
            np.nan
        )
        
        # 转换为百分比
        df[col_name] = df[col_name] * 100
    
    df['trade_date'] = df['trade_date'].dt.strftime('%Y-%m-%d')
    return df


def validate_volatility(df: pd.DataFrame) -> bool:
    """校验波动率数据"""
    if df.empty:
        logger.error('Empty dataframe')
        return False
    
    latest = df.iloc[-1]
    
    # 检查是否有计算值
    has_value = False
    for col in ['basis_vol_5d', 'basis_vol_10d', 'basis_vol_20d']:
        if col in latest and pd.notna(latest[col]):
            val = latest[col]
            # 波动率合理范围 (0%, 200%)
            if 0 <= val <= 200:
                logger.info(f'{col}: {val:.2f}%')
                has_value = True
            else:
                logger.warning(f'Unusual {col}: {val:.2f}%')
    
    if not has_value:
        logger.warning('No valid volatility values calculated')
        # 不返回False，因为可能是数据不足导致的
    
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
            CREATE TABLE IF NOT EXISTS jm_basis_volatility (
                pub_date TEXT,
                obs_date TEXT,
                trade_date TEXT,
                basis_vol_5d REAL,
                basis_vol_10d REAL,
                basis_vol_20d REAL,
                PRIMARY KEY (pub_date, trade_date)
            )
        ''')
        
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO jm_basis_volatility 
                (pub_date, obs_date, trade_date, basis_vol_5d, basis_vol_10d, basis_vol_20d)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                pub_date, obs_date, row['trade_date'],
                row.get('basis_vol_5d'), row.get('basis_vol_10d'), row.get('basis_vol_20d')
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
        filename = OUTPUT_DIR / f'JM05_basis_volatility_{pub_date}.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f'Saved to {filename}')
    except Exception as e:
        logger.error(f'CSV save error: {e}')


def main():
    """主函数"""
    logger.info('=== JM05_basis_volatility 采集开始 ===')
    
    pub_date, obs_date = get_pit_dates()
    logger.info(f'PIT dates: pub_date={pub_date}, obs_date={obs_date}')
    
    # 加载基差数据
    basis_df = load_basis_data()
    
    if basis_df.empty:
        logger.warning('No basis data available - cannot calculate volatility')
        # 创建空结果标记
        result_df = pd.DataFrame({
            'trade_date': [obs_date],
            'basis_vol_5d': [None],
            'basis_vol_10d': [None],
            'basis_vol_20d': [None],
            'data_status': ['basis_missing']
        })
    else:
        # 计算波动率
        result_df = calculate_volatility(basis_df)
        result_df['data_status'] = 'calculated'
    
    # 校验
    validate_volatility(result_df)
    
    # 保存
    save_to_sqlite(result_df, pub_date, obs_date)
    save_to_csv(result_df, pub_date)
    
    # 摘要
    logger.info('\n=== 采集摘要 ===')
    logger.info(f'数据条数: {len(result_df)}')
    if not basis_df.empty:
        logger.info(f'基差数据范围: {basis_df["trade_date"].min()} ~ {basis_df["trade_date"].max()}')
    else:
        logger.warning('基差数据缺失 - 等待JM03接入Mysteel数据')
    logger.info('=== 采集完成 ===')
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
