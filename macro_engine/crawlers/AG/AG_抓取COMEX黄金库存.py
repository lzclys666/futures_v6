#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取COMEX黄金库存.py
因子: AG_INV_COMEX_GOLD = COMEX黄金库存（吨）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- AKShare futures_comex_inventory() 默认返回COMEX黄金库存（吨）
- 数据为周频更新（通常滞后1-2个工作日）
- bounds: [500, 1500] 吨

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import akshare as ak

FACTOR_CODE = "AG_INV_COMEX_GOLD"
SYMBOL = "AG"
MIN_VALUE = 500
MAX_VALUE = 1500

def fetch():
    print("[L1] AKShare futures_comex_inventory(symbol='黄金')...")
    try:
        df = ak.futures_comex_inventory(symbol='黄金')
        if df is not None and not df.empty:
            latest = df.sort_values('日期').iloc[-1]
            stock = float(latest['COMEX黄金库存量-吨'])
            obs_str = str(latest['日期'])[:10]
            if MIN_VALUE <= stock <= MAX_VALUE:
                print(f"[L1] COMEX黄金={stock:.3f}吨 (obs={obs_str})")
                return stock, obs_str
            else:
                print(f"[L1] COMEX黄金={stock} 超出范围[{MIN_VALUE}~{MAX_VALUE}]")
    except Exception as e:
        print(f"[L1] 失败: {e}")
    return None, None

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")
    val, data_date = fetch()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_comex_inventory")
        print(f"[OK] {FACTOR_CODE}={val:.3f} 写入成功")
    else:
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
            print(f"[OK] {FACTOR_CODE}={v} L4回补成功")

if __name__ == "__main__":
    main()
