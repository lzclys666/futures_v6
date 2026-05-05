#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_国内现货价.py
因子: FU_SPOT_DOMESTIC = 国内燃料油现货价格（元/吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare energy_oil_hist — 国内燃料油现货日行情（收盘价）
- L2: None
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

FACTOR_CODE = "FU_SPOT_DOMESTIC"
SYMBOL = "FU"
BOUNDS = (2000, 12000)


def fetch():
    try:
        df = ak.energy_oil_hist()
        if df is not None and len(df) > 0:
            # 列结构: [调整日期, 开盘价, 收盘价, 最高价, 最低价]
            latest = df.iloc[-1]
            date_val = latest.iloc[0]
            price_val = float(latest.iloc[2])  # 收盘价
            date_str = str(date_val)[:10]
            print(f"[L1] 国内燃料油现货: {date_str} -> {price_val}")
            return price_val, date_str
    except Exception as e:
        print(f"[L1] 国内燃料油现货失败: {e}")
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
                source_confidence=1.0, source='AKShare_energy_oil_hist')
    print(f"[OK] {FACTOR_CODE}={val}")


if __name__ == "__main__":
    main()
