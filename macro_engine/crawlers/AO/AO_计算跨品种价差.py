#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AO_计算跨品种价差.py
因子: AO_SPD_AL_AO = 铝-氧化铝跨品种价差（元/吨）

公式: 价差 = 沪铝主力价格 - 氧化铝主力价格

当前状态: [✅正常]
- L1: AKShare futures_main_sina（免费权威）
- L2: 新浪 nf_AL0/nf_AO0 实时行情（免费聚合）
- bounds: [5000, 25000]元/吨（铝价远高于氧化铝价）
- 注: 价差=AL价格-AO价格

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

FACTOR_CODE = "AO_SPD_AL_AO"
SYMBOL = "AO"
BOUNDS = (5_000, 25_000)


def fetch_spread():
    # L1: AKShare（免费权威）
    try:
        print("[L1] AKShare futures_main_sina AL & AO...")
        df_al = ak.futures_main_sina(symbol="AL")
        df_ao = ak.futures_main_sina(symbol="AO")
        if df_al is not None and df_ao is not None:
            p_al = float(df_al.iloc[-1]["close"])
            p_ao = float(df_ao.iloc[-1]["close"])
            spread = round(p_al - p_ao, 2)
            if BOUNDS[0] <= spread <= BOUNDS[1]:
                print(f"[L1] 成功: AL-AO={spread} (AL={p_al:.0f}, AO={p_ao:.0f})")
                return spread, "akshare", 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 新浪（免费聚合源）
    try:
        print("[L2] 新浪 nf_AL0 & nf_AO0...")
        html, err = fetch_url(
            "http://hq.sinajs.cn/list=nf_AL0,nf_AO0",
            timeout=10
        )
        if not err and html:
            lines = html.strip().split("\n")
            prices = []
            for line in lines:
                if '"' in line:
                    parts = line.split('"')[1].split(",")
                    if len(parts) >= 5:
                        prices.append(float(parts[4]))
            if len(prices) >= 2:
                spread = round(prices[0] - prices[1], 2)
                if BOUNDS[0] <= spread <= BOUNDS[1]:
                    print(f"[L2] 成功: AL-AO={spread} (AL={prices[0]:.0f}, AO={prices[1]:.0f})")
                    return spread, "sina", 0.9
    except Exception as e:
        print(f"[L2] 失败: {e}")

    return None, None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    value, source, confidence = fetch_spread()

    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value,
                   source=source, source_confidence=confidence)
        print(f"[OK] {FACTOR_CODE}={value} 写入成功")
        return

    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="(跨品种价差)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")


if __name__ == "__main__":
    main()
