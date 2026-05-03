#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
焦炭期货净持仓
因子: J_J_POS_NET = 焦炭期货净持仓

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak

FACTOR_CODE = "J_J_POS_NET"
SYMBOL = "J"

def fetch_dce_net_position(obs_date):
    date_str = obs_date.strftime("%Y%m%d")
    
    try:
        print(f"[L1] AKShare futures_dce_position_rank date={date_str}...")
        result = ak.futures_dce_position_rank(date=date_str, vars_list=['J'])
        if result is not None:
            if isinstance(result, dict):
                for k, v in result.items():
                    if hasattr(v, 'shape') and v.shape[0] > 0:
                        df = v
                        print(f"[L1] J position data: {df.shape}")
                        if 'volume' in df.columns or '成交量' in df.columns:
                            vol_col = 'volume' if 'volume' in df.columns else '成交量'
                            net = float(df[vol_col].sum())
                            print(f"[L1] J net position: {net:.0f} lots")
                            return net, 'akshare_futures_dce_position_rank', 1.0
    except Exception as e:
        print(f"[L1] Failed: {e}")
    
    print("[L4] DB history fallback...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None:
        print(f"[L4] Fallback: {val}")
        return val, 'db_fallback', 0.5
    return None, None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, source, confidence = fetch_dce_net_position(obs_date)
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        # Null 占位写入
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None, source_confidence=0.0, source="all_sources_failed")
        print(f"[DB] 因子 {FACTOR_CODE} NULL 占位写入")
