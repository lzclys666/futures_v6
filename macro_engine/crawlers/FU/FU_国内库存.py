#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_国内库存.py
因子: FU_DCE_INV = 国内燃料油期货交易所库存（吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_inventory_em(symbol='fu') — DCE燃料油库存
- L2: None（无其他免费库存源）
- L3: None
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符

订阅优先级: 无（免费源）
替代付费源: 无
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
import akshare as ak

FACTOR_CODE = "FU_DCE_INV"
SYMBOL = "FU"
BOUNDS = (0, 500000)


def fetch():
    # L1: AKShare DCE燃料油库存
    try:
        df = ak.futures_inventory_em(symbol='fu')
        if df is not None and len(df) > 0:
            cols = df.columns.tolist()
            # 找日期列和库存值列
            date_col = None
            val_col = None
            for c in cols:
                if 'date' in str(c).lower() or '日期' in str(c):
                    date_col = c
                if c not in [date_col] and df[c].dtype in ['float64', 'int64']:
                    if val_col is None:
                        val_col = c
            if val_col is None and len(cols) > 1:
                val_col = cols[1]
            if date_col and val_col:
                latest = df.iloc[-1]
                val = float(latest[val_col])
                date_str = str(latest[date_col])[:10]
                print(f"[L1] DCE燃料油库存: {date_str} -> {val}")
                return val, date_str
    except Exception as e:
        print(f"[L1] DCE库存失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")
    val, obs_dt = fetch()
    if val is None:
        record = _get_latest_record(FACTOR_CODE, SYMBOL)
        if record:
            raw_value, orig_obs_date, orig_source, orig_conf = record
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
                        source_confidence=0.5, source=f"L4回补({orig_source})")
            print(f"[L4] {FACTOR_CODE}={raw_value} 回补成功")
            return
        print(f"[L5] {FACTOR_CODE}: 所有数据源失效，不写占位符")
        return
    if obs_dt:
        obs_date = obs_dt
    if not (BOUNDS[0] <= val <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={val} out of {BOUNDS}")
        return
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                source_confidence=1.0, source='akshare_futures_inventory_em')
    print(f"[OK] {FACTOR_CODE}={val}")


if __name__ == "__main__":
    main()
