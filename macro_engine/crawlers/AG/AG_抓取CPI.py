#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取CPI.py
因子: AG_MACRO_US_CPI_YOY = 美国CPI同比（%）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- AKShare macro_usa_cpi_yoy 返回美国CPI同比数据（月频）
- 数据来源: 美国劳工统计局（BLS）
- bounds: [0, 15]%

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak

FACTOR_CODE = "AG_MACRO_US_CPI_YOY"
SYMBOL = "AG"
EMIN = 0.0
EMAX = 15.0


def fetch():
    # L1: AKShare 美国CPI
    print("[L1] AKShare macro_usa_cpi_yoy...")
    try:
        df = ak.macro_usa_cpi_yoy()
        if df is not None and len(df) > 0:
            val = float(df.iloc[-1].iloc[-1])
            print(f"[L1] US CPI={val}%")
            if not (EMIN <= val <= EMAX):
                print(f"[WARN] CPI={val}% 超出bounds[{EMIN},{EMAX}]")
                return None, None
            return val, None  # CPI为月频，使用obs_date
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备源（BLS CPI数据仅AKShare提供）
    print("[L2] 无备源（美国CPI仅AKShare/BLS提供）")

    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    val, _ = fetch()

    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source_confidence=1.0, source="akshare_macro_usa_cpi_yoy")
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")

    # L3: 兜底保障
    if val is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(美国CPI)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source_confidence=0.0, source="all_sources_failed")
            print(f"[DB] {FACTOR_CODE} NULL占位写入")


if __name__ == "__main__":
    main()
