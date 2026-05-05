#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AO_抓取期货日行情.py
因子: ao_futures_ohlcv = SHFE氧化铝主力合约日行情（AO0）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: akshare futures_zh_daily_sina(symbol="ao0") 获取氧化铝主力合约完整日行情
- 写入 ao_futures_ohlcv 表（OHLCV + volume）
- bounds: 收盘价[2000, 8000]元/吨
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

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pit_data.db')


def ensure_ohlcv_table():
    """确保 ao_futures_ohlcv 表存在"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ao_futures_ohlcv (
            contract TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (contract, date)
        )
    """)
    conn.commit()
    conn.close()


def save_ohlcv(contract, date, open_, high, low, close, volume):
    """写入 ao_futures_ohlcv 表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO ao_futures_ohlcv
        (contract, date, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (contract, date, open_, high, low, close, volume))
    conn.commit()
    conn.close()


def fetch():
    """获取 AO0 主力合约日行情"""
    print("[L1] AKShare futures_zh_daily_sina ao0...")
    df = ak.futures_zh_daily_sina(symbol="ao0")
    if df is None or len(df) == 0:
        print("[L1] ao0 数据为空")
        return None

    row = df.iloc[-1]
    date = str(row['date'])[:10]
    open_ = float(row['open'])
    high = float(row['high'])
    low = float(row['low'])
    close = float(row['close'])
    volume = int(row['volume'])

    if not (2000 <= close <= 8000):
        print(f"[WARN] AO收盘价={close} 超出 bounds[2000,8000]")

    print(f"[L1] AO0 {date}: O={open_} H={high} L={low} C={close} V={volume}")
    return date, open_, high, low, close, volume


def main():
    _, obs_date = get_pit_dates()
    print(f"=== AO期货日行情 === obs={obs_date}")

    ensure_ohlcv_table()
    result = fetch()
    if result:
        date, open_, high, low, close, volume = result
        save_ohlcv("AO0", date, open_, high, low, close, volume)
        print(f"[OK] AO0 {date} 写入 ao_futures_ohlcv")
    else:
        print("[L1] AO0 日行情获取失败")


if __name__ == "__main__":
    main()
