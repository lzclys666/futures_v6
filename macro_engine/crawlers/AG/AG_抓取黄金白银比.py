#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取黄金白银比.py
因子: AG_MACRO_GOLD_SILVER_RATIO = 金银比（SGE黄金现货价/白银现货价）

公式: 金银比 = SGE黄金午市价(元/克) ÷ SGE白银午市价(元/克)

当前状态: [✅正常]
- AKShare spot_golden_benchmark_sge + spot_silver_benchmark_sge 计算金银比
- 白银现货价单位CNY/kg，需÷1000转换为CNY/g
- bounds: [30.0, 100.0]（金银比合理区间30-100）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak
import pandas as pd

FACTOR_CODE = "AG_MACRO_GOLD_SILVER_RATIO"
SYMBOL = "AG"
EMIN = 30.0
EMAX = 100.0


def fetch():
    # L1: SGE黄金+白银现货
    print("[L1] spot_golden_benchmark_sge...")
    try:
        df_gold = ak.spot_golden_benchmark_sge()
        if df_gold is None or df_gold.empty:
            raise ValueError("spot_golden_benchmark_sge 返回空")
        df_gold = df_gold.sort_values(df_gold.columns[0])
        latest_gold = df_gold.iloc[-1]
        gold_date = pd.to_datetime(latest_gold[df_gold.columns[0]]).date()
        gold_price = float(latest_gold[df_gold.columns[1]])
        print(f"  黄金: {gold_date} 午市价={gold_price} CNY/g")
    except Exception as e:
        print(f"[L1] 黄金现货失败: {e}")
        return None, None

    print("[L1] spot_silver_benchmark_sge...")
    try:
        df_silver = ak.spot_silver_benchmark_sge()
        if df_silver is None or df_silver.empty:
            raise ValueError("spot_silver_benchmark_sge 返回空")
        df_silver = df_silver.sort_values(df_silver.columns[0])
        latest_silver = df_silver.iloc[-1]
        silver_date = pd.to_datetime(latest_silver[df_silver.columns[0]]).date()
        silver_price = float(latest_silver[df_silver.columns[1]]) / 1000.0  # CNY/kg → CNY/g
        print(f"  白银: {silver_date} 午市价={silver_price} CNY/g")
        if silver_price <= 0:
            raise ValueError(f"白银价格异常: {silver_price}")
    except Exception as e:
        print(f"[L1] 白银现货失败: {e}")
        return None, None

    obs_date = max(gold_date, silver_date)
    raw_value = round(gold_price / silver_price, 4)
    print(f"[L1] 金银比={raw_value} obs={obs_date}")

    if not (EMIN <= raw_value <= EMAX):
        print(f"[WARN] 金银比{raw_value}超出bounds[{EMIN},{EMAX}]")
        return None, None

    return raw_value, obs_date


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    raw_value, data_obs = fetch()

    if raw_value is not None:
        write_obs = data_obs if data_obs else obs_date
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, write_obs, raw_value,
                   source_confidence=1.0, source="akshare_SGE_金银比")
        print(f"[OK] {FACTOR_CODE}={raw_value} 写入成功 (obs={write_obs})")

    # L3: 兜底保障
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(金银比)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source_confidence=0.0, source="all_sources_failed")
            print(f"[DB] {FACTOR_CODE} NULL占位写入")


if __name__ == "__main__":
    main()
