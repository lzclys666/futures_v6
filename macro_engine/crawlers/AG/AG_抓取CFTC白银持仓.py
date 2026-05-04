#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取CFTC白银持仓.py
因子: AG_POS_CFTC_NET = CFTC白银非商业净持仓（手）

公式: 数据采集（无独立计算公式）

当前状态: [⛔永久跳过]
- L1: AKShare macro_usa_cftc_nc_holding 只包含9种货币数据，无白银
- L2: 无其他免费CFTC白银持仓数据源
- CFTC官网需手动下载，付费数据源
- L3: save_l4_fallback() 也无历史数据

订阅优先级: ★★★（付费）
替代付费源: CFTC官网（每周五发布）/ Bloomberg Terminal
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak

FACTOR_CODE = "AG_POS_CFTC_NET"
SYMBOL = "AG"


def fetch():
    # L1: AKShare CFTC（货币净持仓，非白银）
    print("[L1] AKShare macro_usa_cftc_nc_holding...")
    try:
        df = ak.macro_usa_cftc_nc_holding()
        if df is not None and len(df) > 0:
            # 该接口只包含货币数据，无白银，跳过
            cols = str(df.columns.tolist())
            print(f"[L1] macro_usa_cftc_nc_holding 列: {cols}")
            print("[L1] 该接口仅支持货币品种，无白银CFTC数据")
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备源（CFTC白银数据无免费聚合源）
    print("[L2] 无备源（CFTC白银持仓无免费数据源）")

    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    val, data_obs = fetch()

    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source_confidence=1.0, source="akshare_cftc")
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
        return

    # L3: 兜底保障
    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                         extra_msg="(CFTC白银持仓)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[DB] {FACTOR_CODE} NULL占位写入")
        print(f"[⛔] {FACTOR_CODE} ⛔永久跳过（无免费源: CFTC官网/彭博）")


if __name__ == "__main__":
    main()
