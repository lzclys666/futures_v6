#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_金银比_AUAG.py
因子: AU_SPD_AUAG = 金银比（SGE黄金现货/白银现货）

公式: AU_SPD_AUAG = AU_SPOT_SGE / (AG_SPOT_SGE / 1000)
      即 黄金现货价(元/克) / 白银现货价(元/克)
      SGE白银现货单位是 CNY/kg，需除以1000转为 CNY/g

当前状态: [✅正常]
- L1: AKShare spot_golden_benchmark_sge() + spot_silver_benchmark_sge()，source_confidence=1.0
- L2: 无备选源（上海金交所独家的金银价格，缺乏公开聚合平台）
- L3: save_l4_fallback() 兜底
- bounds: [30, 100]（金银比历史区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates

import akshare as ak
import pandas as pd

FACTOR_CODE = "AU_SPD_AUAG"
SYMBOL = "AU"
BOUNDS = (30.0, 100.0)


def fetch():
    """L1: AKShare SGE黄金+白银现货价比"""
    print("[L1] AKShare spot_golden/silver_benchmark_sge()...")
    df_gold = ak.spot_golden_benchmark_sge()
    if df_gold is None or df_gold.empty:
        raise ValueError("gold spot empty")
    df_gold = df_gold.sort_values("交易时间")
    latest_gold = df_gold.iloc[-1]
    gold_price = float(latest_gold["晚盘价"])  # CNY/g
    gold_date = pd.to_datetime(latest_gold["交易时间"]).date()

    df_silver = ak.spot_silver_benchmark_sge()
    if df_silver is None or df_silver.empty:
        raise ValueError("silver spot empty")
    df_silver = df_silver.sort_values("交易时间")
    latest_silver = df_silver.iloc[-1]
    # SGE白银现货单位是 CNY/kg，需除以1000转为 CNY/g
    silver_price = float(latest_silver["晚盘价"]) / 1000.0  # CNY/g
    silver_date = pd.to_datetime(latest_silver["交易时间"]).date()

    obs_date = max(gold_date, silver_date)
    raw_value = round(gold_price / silver_price, 4)
    print(f"[L1] gold={gold_price} CNY/g, silver={silver_price*1000} CNY/kg, ratio={raw_value}")
    return raw_value, obs_date


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    raw_value, data_obs_date = None, None

    # L1
    try:
        raw_value, data_obs_date = fetch()
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备选源（上海金交所独有的金银价格，缺乏公开聚合平台）
    if raw_value is None:
        print("[L2] 无备选源（上海金交所独有的金银价格，缺乏公开聚合平台）")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(金银比)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
            print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")
        return

    # bounds校验
    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(金银比)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, data_obs_date, raw_value,
               source="akshare", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={data_obs_date}")


if __name__ == "__main__":
    main()
