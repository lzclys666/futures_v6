#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M_计算比价.py
因子: M_SPD_NEAR_FAR = 豆粕/橡胶现货比价

公式: M_SPD_NEAR_FAR = 豆粕现货价 / 橡胶现货价

当前状态: [⚠️待修复]
- L1: AKShare futures_spot_price — 接口不稳定，有时返回空
- L2: 无备源
- L3: 无备源
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符

备注: 因子代码M_SPD_NEAR_FAR与实际计算内容(M/RU比价)不匹配，需后续确认
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback
import akshare as ak

SYMBOL = "M"
FACTOR_CODE = "M_SPD_NEAR_FAR"
BOUNDS = (0.1, 20.0)


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    try:
        date_str = obs_date.strftime("%Y%m%d")
        df = ak.futures_spot_price(date=date_str, vars_list=["M", "RU"])
        if df is not None and len(df) > 0:
            row = df[df["symbol"] == "M"]
            ru = df[df["symbol"] == "RU"]
            if len(row) and len(ru):
                ratio = round(float(row.iloc[-1]["spot_price"]) / float(ru.iloc[-1]["spot_price"]), 4)
                if BOUNDS[0] <= ratio <= BOUNDS[1]:
                    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, ratio,
                               source_confidence=1.0, source="akshare_futures_spot_price")
                    print(f"[OK] {FACTOR_CODE}={ratio} obs={obs_date}")
                    return
                else:
                    print(f"[WARN] {FACTOR_CODE}={ratio} out of {BOUNDS}")
    except Exception as e:
        print(f"[L1] {FACTOR_CODE}: {e}")

    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)


if __name__ == "__main__":
    main()
