#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取COMEX白银库存.py
因子: AG_INV_COMEX_SILVER = COMEX白银库存（吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- AKShare futures_comex_inventory(symbol='白银') 返回COMEX白银库存（吨）
- 注意：默认参数symbol=None返回黄金数据，需显式传入symbol='白银'
- bounds: [5000, 50000] 吨（COMEX白银库存合理范围）

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

FACTOR_CODE = "AG_INV_COMEX_SILVER"
SYMBOL = "AG"
EMIN = 5000.0
EMAX = 50000.0


def fetch():
    # L1: AKShare COMEX白银库存
    print("[L1] AKShare futures_comex_inventory(symbol='白银')...")
    try:
        df = ak.futures_comex_inventory(symbol='白银')
        if df is not None and len(df) > 0:
            row = df.iloc[-1]
            val = float(row['COMEX白银库存量-吨'])
            data_date_str = str(row['日期'])[:10]
            data_date = datetime.strptime(data_date_str, '%Y-%m-%d').date()
            print(f"[L1] COMEX白银库存={val:.3f}吨 (obs={data_date})")
            return val, data_date
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备源
    print("[L2] 无备源（COMEX库存仅AKShare提供）")

    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    val, data_obs = fetch()

    if val is not None:
        # 使用数据的实际观测日期
        write_obs = data_obs if data_obs else obs_date
        # bounds校验
        if not (EMIN <= val <= EMAX):
            print(f"[WARN] {FACTOR_CODE}={val} 超出bounds[{EMIN},{EMAX}]，跳过写入")
            val = None
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, write_obs, val,
                       source_confidence=1.0, source="akshare_comex_inventory")
            print(f"[OK] {FACTOR_CODE}={val:.3f} 写入成功 (obs={write_obs})")

    # L3: 兜底保障 - save_l4_fallback保留原始obs_date
    if val is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(COMEX白银库存)"):
            pass  # 回补成功
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source_confidence=0.0, source="all_sources_failed")
            print(f"[DB] {FACTOR_CODE} NULL占位写入")


if __name__ == "__main__":
    main()
