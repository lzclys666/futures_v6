# -*- coding: utf-8 -*-
"""
JM03_futures_basis.py
焦煤期现基差采集脚本
数据源: AKShare - futures_zh_daily_sina (期货) + 现货估算

采集因子:
- basis: 基差 = 现货价格 - 期货结算价
- basis_rate: 基差率 = 基差 / 期货结算价 * 100%

说明:
- AKShare无免费日度焦煤现货数据
- 本脚本使用Mysteel现货数据估算（需用户确认账号）
- 如无可用的Mysteel数据，基差将标记为NULL并记录警告

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
MAIN_CONTRACT = 'JM2505'

# 现货价格配置 (元/吨)
# 注意: 以下为示例参考价格，实际需从Mysteel等数据源获取
# 山西吕梁主焦煤(A<11%, S<1%, V<25%, G>85) 出厂含税价
SPOT_PRICE_CONFIG = {
    'source': 'mysteel',  # 待接入
    'region': '山西吕梁',
    'grade': '主焦煤(A<11%, S<1%, V<25%, G>85)',
    'note': '需Mysteel付费账号接入'
}


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


def fetch_futures_data(contract: str) -> pd.DataFrame:
    """获取期货数据"""
    try:
        df = ak.futures_zh_daily_sina(symbol=contract)
        if df is None or df.empty:
            return pd.DataFrame()
        
        df = df.copy()
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df['settle'] = pd.to_numeric(df['settle'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        
        return df[['date', 'settle', 'close']].rename(columns={
            'settle': 'futures_settle',
            'close': 'futures_close'
        })
    except Exception as e:
        logger.error(f'Error fetching futures data: {e}')
        return pd.DataFrame()


def fetch_spot_price_mysteel() -> pd.DataFrame:
    """
    从Mysteel获取现货价格
    注意: 需要付费账号
    """
    logger.warning('Mysteel spot price fetch not implemented - requires paid account')
    logger.info(f'Spot price config: {SPOT_PRICE_CONFIG}')
    
    # TODO: 接入Mysteel API
    # 返回空DataFrame表示数据不可用
    return pd.DataFrame()


def fetch_spot_price_akshare() -> pd.DataFrame:
    """
    尝试从AKShare获取焦煤相关现货数据
    """
    try:
        # 尝试获取煤炭港口价格作为参考
        # 注意: AKShare煤炭数据可能不是日度更新
        df = ak.coal_price_5500()
        if df is not None and not df.empty:
            logger.info(f'Found coal price data: {len(df)} rows')
            return df
    except Exception as e:
        logger.debug(f'AKShare coal price not available: {e}')
    
    return pd.DataFrame()


def calculate_basis(futures_df: pd.DataFrame, spot_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    计算基差
    
    Args:
        futures_df: 期货数据
        spot_df: 现货数据 (可选)
    
    Returns:
        包含基差的DataFrame
    """
    result_df = futures_df.copy()
    
    if spot_df is None or spot_df.empty:
        # 无现货数据，标记为缺失
        logger.warning('No spot price data available - basis will be NULL')
        result_df['spot_price'] = None
        result_df['spot_source'] = 'missing'
        result_df['basis'] = None
        result_df['basis_rate'] = None
        result_df['data_status'] = 'futures_only'
    else:
        # TODO: 实现现货数据合并和基差计算
        # 需要匹配日期并处理不同数据源
        logger.warning('Spot data merge not yet implemented')
        result_df['spot_price'] = None
        result_df['spot_source'] = 'pending'
        result_df['basis'] = None
        result_df['basis_rate'] = None
        result_df['data_status'] = 'pending_integration'
    
    return result_df


def validate_basis_data(df: pd.DataFrame) -> bool:
    """校验基差数据"""
    if df.empty:
        logger.error('Empty dataframe')
        return False
    
    # 检查期货数据
    latest = df.iloc[-1]
    if pd.isna(latest.get('futures_settle')):
        logger.error('Missing futures settlement price')
        return False
    
    # 期货价格合理性检查
    settle = latest['futures_settle']
    if settle < 100 or settle > 5000:
        logger.error(f'Invalid futures price: {settle}')
        return False
    
    logger.info(f'Futures settle price: {settle}')
    
    # 检查基差数据状态
    data_status = latest.get('data_status', 'unknown')
    if data_status == 'futures_only':
        logger.warning('Basis data incomplete - spot price missing')
    elif data_status == 'pending_integration':
        logger.warning('Basis data pending Mysteel integration')
    
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
            CREATE TABLE IF NOT EXISTS jm_futures_basis (
                pub_date TEXT,
                obs_date TEXT,
                trade_date TEXT,
                contract TEXT,
                futures_settle REAL,
                futures_close REAL,
                spot_price REAL,
                spot_source TEXT,
                basis REAL,
                basis_rate REAL,
                data_status TEXT,
                PRIMARY KEY (pub_date, trade_date)
            )
        ''')
        
        # 插入数据
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO jm_futures_basis 
                (pub_date, obs_date, trade_date, contract, futures_settle, futures_close,
                 spot_price, spot_source, basis, basis_rate, data_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pub_date, obs_date, row['date'], MAIN_CONTRACT,
                row.get('futures_settle'), row.get('futures_close'),
                row.get('spot_price'), row.get('spot_source'),
                row.get('basis'), row.get('basis_rate'), row.get('data_status')
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
        filename = OUTPUT_DIR / f'JM03_futures_basis_{pub_date}.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f'Saved to {filename}')
    except Exception as e:
        logger.error(f'CSV save error: {e}')


def main():
    """主函数"""
    logger.info('=== JM03_futures_basis 采集开始 ===')
    logger.info(f'主力合约: {MAIN_CONTRACT}')
    
    pub_date, obs_date = get_pit_dates()
    logger.info(f'PIT dates: pub_date={pub_date}, obs_date={obs_date}')
    
    # 获取期货数据
    futures_df = fetch_futures_data(MAIN_CONTRACT)
    if futures_df.empty:
        logger.error('Failed to fetch futures data')
        return False
    
    logger.info(f'Fetched {len(futures_df)} rows of futures data')
    
    # 尝试获取现货数据
    spot_df = fetch_spot_price_mysteel()
    if spot_df.empty:
        spot_df = fetch_spot_price_akshare()
    
    # 计算基差
    result_df = calculate_basis(futures_df, spot_df)
    
    # 校验数据
    if not validate_basis_data(result_df):
        logger.error('Data validation failed')
        return False
    
    # 保存数据
    save_to_sqlite(result_df, pub_date, obs_date)
    save_to_csv(result_df, pub_date)
    
    # 输出摘要
    logger.info('\n=== 采集摘要 ===')
    latest = result_df.iloc[-1]
    logger.info(f'数据日期范围: {result_df["date"].min()} ~ {result_df["date"].max()}')
    logger.info(f'总数据条数: {len(result_df)}')
    logger.info(f'期货结算价: {latest["futures_settle"]}')
    logger.info(f'数据状态: {latest.get("data_status", "unknown")}')
    
    if latest.get('basis') is not None:
        logger.info(f'基差: {latest["basis"]:.2f}')
        logger.info(f'基差率: {latest["basis_rate"]:.2f}%')
    else:
        logger.warning('基差数据缺失 - 等待Mysteel账号接入')
    
    logger.info('=== 采集完成 ===')
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
