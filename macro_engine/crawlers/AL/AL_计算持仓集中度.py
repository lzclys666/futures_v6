#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_计算持仓集中度.py
因子: AL_POS_CONCENTRATION = 沪铝期货前10名会员持仓集中度CR10（%）

公式: CR10 = (前10名会员持仓量 / 总持仓量) × 100

当前状态: [✅正常]
- L1: AKShare get_shfe_rank_table()（L1权威）
- bounds: [0, 100]%
- 注: obs_date Bug已修复（2026-05-05）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates

import akshare as ak

FACTOR_CODE = "AL_POS_CONCENTRATION"
SYMBOL = "AL"
BOUNDS = (0, 100)


def fetch_concentration(obs_date):
    try:
        print("[L1] AKShare get_shfe_rank_table...")
        df = ak.get_shfe_rank_table(date=obs_date.strftime("%Y%m%d"))
        if df is not None and len(df) > 0:
            al_df = df[df["variety"] == "AL"]
            if len(al_df) > 0:
                cols = al_df.columns.tolist()
                vol_col = None
                for c in cols:
                    if "volume" in str(c).lower():
                        vol_col = c
                        break
                if vol_col is None:
                    vol_col = cols[3] if len(cols) > 3 else cols[-1]
                total_vol = float(al_df[vol_col].sum())
                top10_vol = float(al_df.head(10)[vol_col].sum())
                cr10 = round(top10_vol / total_vol * 100, 2) if total_vol > 0 else 0
                if BOUNDS[0] <= cr10 <= BOUNDS[1]:
                    print(f"[L1] 成功: CR10={cr10}%")
                    return cr10, "akshare", 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")

    return None, None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    value, source, confidence = fetch_concentration(obs_date)

    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value,
                   source=source, source_confidence=confidence)
        print(f"[OK] {FACTOR_CODE}={value} 写入成功")
        return

    # L3: 兜底保障
    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                         extra_msg="(持仓集中度)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")


if __name__ == "__main__":
    main()
