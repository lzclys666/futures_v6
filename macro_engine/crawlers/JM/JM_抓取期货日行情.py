#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JM_抓取期货日行情.py
因子: jm_futures_ohlcv = DCE焦煤期货主力合约日行情（JM0）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: akshare futures_zh_daily_sina(symbol="jm0") 获取焦煤主力合约完整日行情
- 写入 jm_futures_ohlcv 表（OHLCV + volume + hold + settle）
- bounds: 收盘价[800, 2000]元/吨
- 自动跳过已有日期（INSERT OR REPLACE）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os, sqlite3
from datetime import datetime, date, timedelta
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import get_pit_dates
import akshare as ak
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pit_data.db')


def save_ohlcv(pub_date, obs_date, contract, trade_date, open_, high, low, close, volume, hold, settle):
    """写入 jm_futures_ohlcv 表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO jm_futures_ohlcv
        (pub_date, obs_date, contract, trade_date, open, high, low, close, volume, hold, settle)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (pub_date, obs_date, contract, trade_date, open_, high, low, close, volume, hold, settle))
    conn.commit()
    conn.close()


def fetch_history(start_date, end_date):
    """批量获取历史数据"""
    print(f"[L1] 获取 JM0 历史数据 {start_date} ~ {end_date}...")
    df = ak.futures_zh_daily_sina(symbol="jm0")
    if df is None or len(df) == 0:
        print("[L1] jm0 数据为空")
        return 0
    
    df['date'] = pd.to_datetime(df['date'])
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    df = df[(df['date'] >= start) & (df['date'] <= end)]
    
    today = date.today().strftime('%Y-%m-%d')
    count = 0
    for _, row in df.iterrows():
        trade_date = str(row['date'])[:10]
        save_ohlcv(
            pub_date=today,
            obs_date=trade_date,
            contract='JM0',
            trade_date=trade_date,
            open_=float(row['open']),
            high=float(row['high']),
            low=float(row['low']),
            close=float(row['close']),
            volume=int(row['volume']),
            hold=int(row['hold']),
            settle=float(row['settle'])
        )
        count += 1
    print(f"[L1] 写入 {count} 条 JM0 历史数据")
    return count


def fetch_today():
    """获取今日数据"""
    print("[L1] AKShare futures_zh_daily_sina jm0...")
    df = ak.futures_zh_daily_sina(symbol="jm0")
    if df is None or len(df) == 0:
        print("[L1] jm0 数据为空")
        return False
    
    today = date.today().strftime('%Y-%m-%d')
    row = df.iloc[-1]
    trade_date = str(row['date'])[:10]
    
    close = float(row['close'])
    if not (800 <= close <= 2000):
        print(f"[WARN] JM0收盘价={close} 超出 bounds[800,2000]")
    
    save_ohlcv(
        pub_date=today,
        obs_date=trade_date,
        contract='JM0',
        trade_date=trade_date,
        open_=float(row['open']),
        high=float(row['high']),
        low=float(row['low']),
        close=close,
        volume=int(row['volume']),
        hold=int(row['hold']),
        settle=float(row['settle'])
    )
    print(f"[OK] JM0 {trade_date} 写入 jm_futures_ohlcv")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--backfill', action='store_true', help='回补历史数据')
    parser.add_argument('--start', type=str, default='2026-04-25', help='回补开始日期')
    parser.add_argument('--end', type=str, default=None, help='回补结束日期')
    args = parser.parse_args()
    
    if args.backfill:
        end = args.end or date.today().strftime('%Y-%m-%d')
        fetch_history(args.start, end)
    else:
        fetch_today()


if __name__ == "__main__":
    main()
