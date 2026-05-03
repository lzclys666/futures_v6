#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_抓取LME铝库存.py
因子: AL_INV_LME = LME铝库存（吨）

公式: 数据采集（无独立计算公式）

当前状态: [OK]正常
- 数据源: AKShare macro_euro_lme_stock（欧洲LME库存，含铝分品种）
- 采集逻辑: 查找列名含'aluminum'/'al'的列，取最新一行数值
- bounds: [0, 5000000]吨（LME铝库存历史最高约500万吨）

订阅优先级: ★★（LME库存为公开数据，AKShare为L2聚合）
替代付费源: LME官网（免费，需解析）
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak

FACTOR_CODE = "AL_INV_LME"
SYMBOL = "AL"
BOUNDS = (0, 5_000_000)


def fetch_lme_inventory():
    # L1: macro_euro_lme_stock (欧洲LME库存)
    try:
        print("[L1] AKShare macro_euro_lme_stock...")
        df = ak.macro_euro_lme_stock()
        if df is not None and len(df) > 0:
            cols = df.columns.tolist()
            # 查找铝相关列
            al_col = None
            for c in cols:
                c_lower = str(c).lower()
                if "aluminum" in c_lower or "al " in c_lower:
                    al_col = c
                    break
            if al_col is None:
                # 回退：取数值列最后一列
                for c in cols:
                    if df[c].dtype in ("float64", "int64"):
                        al_col = c
                        break
            if al_col is None:
                al_col = cols[-1]
            val = df.iloc[-1][al_col]
            if isinstance(val, str):
                val = val.replace(",", "").strip()
            val = float(val)
            if BOUNDS[0] <= val <= BOUNDS[1]:
                print(f"[L1] 成功: {val:.0f} 吨")
                return val, "akshare", 0.9
            else:
                print(f"[L1] 值{val}超出bounds{BOUNDS}，跳过")
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L4回补
    print("[L4] DB历史回补...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None:
        print(f"[L4] 兜底: {val}")
        return val, "db_回补", 0.5
    return None, None, None


if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); exit(0)
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, source, confidence = fetch_lme_inventory()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value,
                   source=source, source_confidence=confidence)
    else:
        print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")
