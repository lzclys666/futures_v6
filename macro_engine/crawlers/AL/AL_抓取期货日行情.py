#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_抓取期货日行情.py
因子: al_futures_ohlcv = SHFE铝主力合约日行情（AL0）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: akshare futures_zh_daily_sina(symbol="al0") 获取沪铝主力合约完整日行情
- 写入 al_futures_ohlcv 表（OHLCV + volume）
- bounds: 收盘价[15000, 30000]元/吨
- 自动跳过已有日期（INSERT OR REPLACE）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import get_pit_dates
import akshare as ak
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pit_data.db')


def save_ohlcv(contract, date, open_, high, low, close, volume):
    """写入 al_futures_ohlcv 表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO al_futures_ohlcv
        (contract, date, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (contract, date, open_, high, low, close, volume))
    conn.commit()
    conn.close()


def fetch():
    """获取 AL0 主力合约日行情"""
    print("[L1] AKShare futures_zh_daily_sina al0...")
    df = ak.futures_zh_daily_sina(symbol="al0")
    if df is None or len(df) == 0:
        print("[L1] al0 数据为空")
        return None
    
    col_map = {str(c).strip(): c for c in df.columns}
    
    # 取最新一行
    row = df.iloc[-1]
    date = str(row['date'])[:10]
    open_ = float(row['open'])
    high = float(row['high'])
    low = float(row['low'])
    close = float(row['close'])
    volume = int(row['volume'])
    
    # 合理性校验
    if not (15000 <= close <= 30000):
        print(f"[WARN] AL收盘价={close} 超出 bounds[15000,30000]")
    
    print(f"[L1] AL0 {date}: O={open_} H={high} L={low} C={close} V={volume}")
    return date, open_, high, low, close, volume


def main():
    _, obs_date = get_pit_dates()
    print(f"=== AL期货日行情 === obs={obs_date}")

    result = fetch()
    if result:
        date, open_, high, low, close, volume = result
        save_ohlcv("AL0", date, open_, high, low, close, volume)
        print(f"[OK] AL0 {date} 写入 al_futures_ohlcv")
    else:
        print("[L1] AL0 日行情获取失败")


if __name__ == "__main__":
    main()
