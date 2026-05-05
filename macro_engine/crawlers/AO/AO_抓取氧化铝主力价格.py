#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AO_抓取氧化铝主力价格.py
因子: AO_PRC_AO_FUT = 氧化铝主力合约价格（元/吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_main_sina(symbol="AO") 获取氧化铝主力合约价格
- L2: 新浪 nf_AO0 实时行情
- L3: save_l4_fallback() 兜底
- bounds: [2000, 8000]元/吨

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak
from common.web_utils import fetch_url

FACTOR_CODE = "AO_PRC_AO_FUT"
SYMBOL = "AO"
BOUNDS = (2_000, 8_000)


def fetch():
    # L1: AKShare
    print("[L1] AKShare futures_main_sina AO...")
    try:
        df = ak.futures_main_sina(symbol="AO")
        if df is not None and len(df) > 0:
            val = float(df.iloc[-1]["close"])
            if BOUNDS[0] <= val <= BOUNDS[1]:
                print(f"[L1] 成功: {val:.0f} 元/吨")
                return val, "akshare", 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 新浪
    print("[L2] 新浪 nf_AO0...")
    try:
        html, err = fetch_url("http://hq.sinajs.cn/list=nf_AO0", timeout=10)
        if not err and '"' in html:
            data = html.split('"')[1].split(",")
            if len(data) >= 5:
                val = float(data[4])
                if BOUNDS[0] <= val <= BOUNDS[1]:
                    print(f"[L2] 成功: {val:.0f} 元/吨")
                    return val, "sina", 0.9
    except Exception as e:
        print(f"[L2] 失败: {e}")

    return None, None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    val, source, confidence = fetch()

    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source=source, source_confidence=confidence)
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
        return

    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="(氧化铝价格)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[DB] {FACTOR_CODE} NULL占位写入")
        print(f"[⛔] {FACTOR_CODE} 所有数据源均失败")


if __name__ == "__main__":
    main()
