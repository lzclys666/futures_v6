#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BR_抓取现货和基差.py
因子: BR_SPOT_PRICE = 丁二烯橡胶华东参考价（元/吨）
      BR_SPD_BASIS = 丁二烯橡胶基差（元/吨）= 现货价 - BR0期货结算价
      BR_COST_MARGIN = 丁二烯橡胶毛利（元/吨）= 现货价 - 丁二烯成本×0.82 - 3000

公式:
  BR_SPD_BASIS = BR_SPOT_PRICE - BR0结算价
  BR_COST_MARGIN = BR_SPOT_PRICE - BR_COST_BD × 0.82 - 3000

当前状态: [✅正常]
- L1: AKShare futures_spot_price(date, vars_list=['BR']) + futures_main_sina('BR0')
- L2: 无备选源（现货价/期货结算价仅有AKShare聚合，无直接免费API）
- L3: save_l4_fallback() 兜底
- bounds: BR_SPOT_PRICE=[8000,30000], BR_SPD_BASIS=[-2000,5000], BR_COST_MARGIN=[-5000,10000]

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates, get_latest_value

import akshare as ak
import pandas as pd
from datetime import timedelta

FACTOR_CODE_SPOT = "BR_SPOT_PRICE"
FACTOR_CODE_BASIS = "BR_SPD_BASIS"
FACTOR_CODE_MARGIN = "BR_COST_MARGIN"
SYMBOL = "BR"
BOUNDS_SPOT = (8000.0, 30000.0)
BOUNDS_BASIS = (-2000.0, 5000.0)
BOUNDS_MARGIN = (-5000.0, 10000.0)


def fetch_spot_price(obs_date):
    """L1: AKShare 丁二烯橡胶现货价（尝试最近5个工作日）"""
    print("[L1] AKShare futures_spot_price(vars_list=['BR'])...")
    for delta in range(8):
        check = obs_date - timedelta(days=delta)
        if check.weekday() >= 5:
            continue
        date_str = check.strftime("%Y%m%d")
        try:
            df = ak.futures_spot_price(date=date_str, vars_list=["BR"])
            if df is None or df.empty:
                continue
            latest = df.sort_values("date").iloc[-1]
            raw_value = float(latest["spot_price"])
            if raw_value <= 0:
                continue
            actual_date = pd.to_datetime(latest["date"]).date()
            print(f"[L1] BR现货价={raw_value} (date={date_str})")
            return raw_value, actual_date
        except Exception as e:
            print(f"[L1] {date_str}: {e}")
    # L2: 无备选源
    print("[L2] 无备选源（现货价仅有AKShare聚合，无直接免费API）")
    return None, None


def fetch_br0_settlement(obs_date):
    """L1: AKShare BR0期货结算价"""
    print("[L1] AKShare futures_main_sina(symbol='BR0')...")
    try:
        df = ak.futures_main_sina(symbol="BR0")
        if df is None or df.empty:
            raise ValueError("empty")
        latest = df.sort_values("日期").iloc[-1]
        settle = float(latest.get("动态结算价") or latest.get("收盘价") or 0)
        if settle <= 0:
            raise ValueError("结算价<=0")
        return settle
    except Exception as e:
        print(f"[L1] BR0结算价失败: {e}")
    # L2: 无备选源
    print("[L2] 无备选源（期货结算价仅有AKShare，无备选接口）")
    return None


if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); sys.exit(0)

    ensure_table()
    print(f"=== BR现货/基差/毛利 === pub={pub_date} obs={obs_date}")

    # L1: BR现货价
    ref_price, actual_date = fetch_spot_price(obs_date)
    if ref_price is None:
        # L3: save_l4_fallback
        if save_l4_fallback(FACTOR_CODE_SPOT, SYMBOL, pub_date, obs_date,
                             extra_msg="(BR现货价)"):
            pass
        else:
            print("[WARN] BR_SPOT_PRICE 所有数据源均失败")
        sys.exit(0)

    # bounds 检查
    if not (BOUNDS_SPOT[0] <= ref_price <= BOUNDS_SPOT[1]):
        print(f"[WARN] BR_SPOT_PRICE={ref_price} 超出bounds{BOUNDS_SPOT}，跳过")
        sys.exit(0)

    # 写BR现货价
    save_to_db(FACTOR_CODE_SPOT, SYMBOL, pub_date, actual_date, ref_price,
               source="akshare_futures_spot_price", source_confidence=1.0)
    print(f"[OK] BR_SPOT_PRICE={ref_price}")

    # L1: BR0结算价 -> 计算基差
    br0_settle = fetch_br0_settlement(obs_date)
    if br0_settle is not None:
        basis = round(ref_price - br0_settle, 2)
        if BOUNDS_BASIS[0] <= basis <= BOUNDS_BASIS[1]:
            save_to_db(FACTOR_CODE_BASIS, SYMBOL, pub_date, actual_date, basis,
                       source="akshare_futures_main_sina", source_confidence=1.0)
            print(f"[OK] BR_SPD_BASIS={basis} (现货{ref_price}-期货结算价{br0_settle})")
        else:
            print(f"[WARN] BR_SPD_BASIS={basis} 超出bounds{BOUNDS_BASIS}，跳过")
    else:
        print("[WARN] BR0结算价缺失，跳过基差")

    # 派生: 毛利 = 现货 - 丁二烯成本×0.82 - 3000
    bd_cost = get_latest_value("BR_COST_BD", SYMBOL)
    if bd_cost is not None:
        margin = round(ref_price - bd_cost * 0.82 - 3000, 2)
        if BOUNDS_MARGIN[0] <= margin <= BOUNDS_MARGIN[1]:
            save_to_db(FACTOR_CODE_MARGIN, SYMBOL, pub_date, actual_date, margin,
                       source="派生计算", source_confidence=0.8)
            print(f"[OK] BR_COST_MARGIN={margin} (现货{ref_price}-{bd_cost}*0.82-3000)")
        else:
            print(f"[WARN] BR_COST_MARGIN={margin} 超出bounds{BOUNDS_MARGIN}，跳过")
    else:
        print("[WARN] BR_COST_BD无数据，跳过毛利计算")
