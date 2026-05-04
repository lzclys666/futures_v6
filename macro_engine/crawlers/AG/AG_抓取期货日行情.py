#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取期货日行情.py
因子: AG_FUT_CLOSE = 沪银期货收盘价（元/千克）
       AG_POS_NET = 沪银期货持仓量（手）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- AKShare futures_main_sina("AG0") 返回沪银主力合约完整行情
- 收盘价提取 "收盘" 字段，写入 AG_FUT_CLOSE
- 持仓量提取 "持仓量" 字段，写入 AG_POS_NET
- bounds: 收盘价[4000, 10000]元/kg, 持仓量[100000, 2000000]手

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak

SYMBOL = "AG"
EMIN_CLOSE = 10000.0
EMAX_CLOSE = 25000.0
EMIN_OI = 100000.0
EMAX_OI = 2000000.0


def fetch():
    # L1: AKShare 新浪期货AG0
    print("[L1] AKShare futures_main_sina AG0...")
    try:
        df = ak.futures_main_sina(symbol="AG0")
        if df is None or len(df) == 0:
            raise ValueError("返回空数据")
        col_map = {str(c).strip(): c for c in df.columns}
        row = df.iloc[-1]
        result = {}

        # 收盘价
        for close_name in ["收盘价", "最新价", "昨收"]:
            if close_name in col_map:
                val = float(row[col_map[close_name]])
                if EMIN_CLOSE <= val <= EMAX_CLOSE:
                    result["AG_FUT_CLOSE"] = val
                    print(f"[L1] AG收盘价={val}")
                else:
                    print(f"[WARN] AG收盘价={val} 超出bounds[{EMIN_CLOSE},{EMAX_CLOSE}]")
                break

        # 持仓量
        if "持仓量" in col_map:
            val = float(row[col_map["持仓量"]])
            if EMIN_OI <= val <= EMAX_OI:
                result["AG_POS_NET"] = val
                print(f"[L1] AG持仓量={val}")
            else:
                print(f"[WARN] AG持仓量={val} 超出bounds[{EMIN_OI},{EMAX_OI}]")

        return result
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备源
    print("[L2] 无备源")

    return {}


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== AG期货日行情 === obs={obs_date}")

    vals = fetch()

    for fc, val in vals.items():
        save_to_db(fc, SYMBOL, pub_date, obs_date, val,
                   source_confidence=1.0, source="akshare_futures_main_sina")
        print(f"[OK] {fc}={val} 写入成功")

    # L3: 兜底保障
    if not vals:
        if save_l4_fallback("AG_POS_NET", SYMBOL, pub_date, obs_date,
                             extra_msg="(AG持仓量)"):
            pass
        else:
            save_to_db("AG_POS_NET", SYMBOL, pub_date, obs_date, None,
                       source_confidence=0.0, source="all_sources_failed")
            print(f"[DB] AG_POS_NET NULL占位写入")


if __name__ == "__main__":
    main()
