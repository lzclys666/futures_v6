#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取COMEX黄金库存.py
因子: AG_INV_COMEX_GOLD = COMEX黄金库存（吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- AKShare futures_comex_inventory() 默认返回COMEX黄金库存（吨）
- 数据为周频更新（通常滞后1-2个工作日）
- bounds: [500, 1500] 吨

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak
from datetime import datetime

FACTOR_CODE = "AG_INV_COMEX_GOLD"
SYMBOL = "AG"
EMIN = 500.0
EMAX = 1500.0


def fetch():
    # L1: AKShare COMEX黄金库存
    print("[L1] AKShare futures_comex_inventory(symbol='黄金')...")
    try:
        df = ak.futures_comex_inventory(symbol='黄金')
        if df is not None and not df.empty:
            latest = df.sort_values('日期').iloc[-1]
            stock = float(latest['COMEX黄金库存量-吨'])
            obs_str = str(latest['日期'])[:10]
            data_date = datetime.strptime(obs_str, '%Y-%m-%d').date()
            if not (EMIN <= stock <= EMAX):
                print(f"[L1] COMEX黄金={stock} 超出bounds[{EMIN},{EMAX}]")
                return None, None
            print(f"[L1] COMEX黄金={stock:.3f}吨 (obs={data_date})")
            return stock, data_date
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备源
    print("[L2] 无备源（COMEX黄金库存仅AKShare提供）")

    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    val, data_obs = fetch()

    if val is not None:
        write_obs = data_obs if data_obs else obs_date
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, write_obs, val,
                   source_confidence=1.0, source="akshare_comex_inventory")
        print(f"[OK] {FACTOR_CODE}={val:.3f} 写入成功 (obs={write_obs})")

    # L3: 兜底保障
    if val is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(COMEX黄金库存)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source_confidence=0.0, source="all_sources_failed")
            print(f"[DB] {FACTOR_CODE} NULL占位写入")


if __name__ == "__main__":
    main()
