#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取净持仓.py
因子: AG_POS_NET = 白银期货持仓量（手）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- AKShare futures_main_sina(symbol='AG0') 获取白银期货AG0持仓量（手）
- 注意：AG_POS_NET同时由AG_抓取期货日行情.py写入，存在重复写入
- bounds: [100000, 2000000] 手

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak

FACTOR_CODE = "AG_POS_NET"
SYMBOL = "AG"
EMIN = 100000.0
EMAX = 2000000.0


def fetch():
    # L1: AKShare 新浪期货AG0持仓量
    print("[L1] AKShare futures_main_sina AG0...")
    try:
        df = ak.futures_main_sina(symbol="AG0")
        if df is None or len(df) == 0:
            raise ValueError("返回空数据")
        col_map = {str(c).strip(): c for c in df.columns}
        if "持仓量" in col_map:
            val = float(df.iloc[-1][col_map["持仓量"]])
            if not (EMIN <= val <= EMAX):
                print(f"[WARN] AG持仓量={val} 超出bounds[{EMIN},{EMAX}]")
                return None, None
            print(f"[L1] AG持仓量={val}")
            return val, None  # 期货日频，使用obs_date
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备源（新浪期货AG0为主要来源）
    print("[L2] 无备源")

    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    val, _ = fetch()

    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source_confidence=1.0, source="akshare_futures_main_sina")
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")

    # L3: 兜底保障
    if val is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(白银持仓量)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source_confidence=0.0, source="all_sources_failed")
            print(f"[DB] {FACTOR_CODE} NULL占位写入")


if __name__ == "__main__":
    main()
