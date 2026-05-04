#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取白银ETF持仓.py
因子: AG_DEM_ETF_HOLDING = 白银ETF持仓总量（吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- AKShare macro_cons_silver 返回白银ETF总库存（吨）
- 数据来源: 全球主要白银ETF汇总持仓
- bounds: [0, 50000] 吨

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak
from datetime import datetime

FACTOR_CODE = "AG_DEM_ETF_HOLDING"
SYMBOL = "AG"
EMIN = 0.0
EMAX = 50000.0


def fetch():
    # L1: AKShare 白银ETF持仓
    print("[L1] AKShare macro_cons_silver...")
    try:
        df = ak.macro_cons_silver()
        if df is not None and len(df) > 0:
            row = df.iloc[-1]
            val = float(row['总库存'])
            obs_str = str(row['日期'])[:10]
            data_date = datetime.strptime(obs_str, '%Y-%m-%d').date()
            print(f"[L1] 白银ETF持仓={val:.2f}吨 (obs={data_date})")
            return val, data_date
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备源
    print("[L2] 无备源（白银ETF持仓仅AKShare提供）")

    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    val, data_obs = fetch()

    if val is not None:
        write_obs = data_obs if data_obs else obs_date
        if not (EMIN <= val <= EMAX):
            print(f"[WARN] {FACTOR_CODE}={val} 超出bounds[{EMIN},{EMAX}]，跳过写入")
            val = None
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, write_obs, val,
                       source_confidence=1.0, source="akshare_macro_cons_silver")
            print(f"[OK] {FACTOR_CODE}={val:.2f} 写入成功 (obs={write_obs})")

    # L3: 兜底保障
    if val is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(白银ETF持仓)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source_confidence=0.0, source="all_sources_failed")
            print(f"[DB] {FACTOR_CODE} NULL占位写入")


if __name__ == "__main__":
    main()
