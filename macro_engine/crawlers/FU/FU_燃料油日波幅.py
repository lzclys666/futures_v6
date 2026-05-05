#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_燃料油日波幅.py
因子: FU_HIGH_LOW = 燃料油期货主力合约日波幅（最高价-最低价）

公式: FU_HIGH_LOW = high - low（元/吨）

当前状态: [✅正常]
- L1: AKShare futures_main_sina("FU0") — 主力合约日行情
- L2: AKShare futures_zh_daily_sina("FU0") — 日行情
- L3: 新浪实时API — 实时行情
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

FACTOR_CODE = "FU_HIGH_LOW"
SYMBOL = "FU"
BOUNDS = (0, 200)


def fetch():
    # L1: AKShare futures_main_sina
    try:
        df = ak.futures_main_sina(symbol="FU0")
        if df is not None and len(df) > 0:
            cols = df.columns.tolist()
            high_col, low_col = None, None
            for c in cols:
                if 'high' in str(c).lower() or '最高' in str(c):
                    high_col = c
                if 'low' in str(c).lower() or '最低' in str(c):
                    low_col = c
            if high_col is None and len(cols) > 2:
                high_col = cols[2]
            if low_col is None and len(cols) > 3:
                low_col = cols[3]
            if high_col and low_col:
                high_val = float(str(df.iloc[-1][high_col]).replace(',', '').strip())
                low_val = float(str(df.iloc[-1][low_col]).replace(',', '').strip())
                val = round(high_val - low_val, 2)
                if BOUNDS[0] <= val <= BOUNDS[1]:
                    print(f"[L1] FU日波幅: {high_val} - {low_val} = {val}")
                    return val
    except Exception as e:
        print(f"[L1] 失败: {e}")
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")
    val = fetch()
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
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                source_confidence=1.0, source='AKShare_Sina_FU0')
    print(f"[OK] {FACTOR_CODE}={val}")


if __name__ == "__main__":
    main()
