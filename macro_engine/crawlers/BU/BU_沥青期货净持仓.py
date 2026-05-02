#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沥青期货净持仓
因子: BU_BU_POS_NET = 沥青期货净持仓

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
import pandas as pd

FACTOR_CODE = "BU_BU_POS_NET"
SYMBOL = "BU"

def fetch_shfe_net_position(obs_date):
    try:
        print("[L1] AKShare get_shfe_rank_table...")
        result = ak.get_shfe_rank_table()
        if isinstance(result, dict) and len(result) > 0:
            for date_key, df in result.items():
                if isinstance(df, pd.DataFrame) and len(df) > 0:
                    if 'variety' in df.columns:
                        bu_df = df[df['variety'] == 'BU']
                    elif '品种' in df.columns:
                        bu_df = df[df['品种'] == 'BU']
                    else:
                        bu_df = df
                    
                    if len(bu_df) > 0:
                        cols = bu_df.columns.tolist()
                        buy_col = None
                        sell_col = None
                        for c in cols:
                            c_lower = str(c).lower()
                            if 'buy' in c_lower or '买' in c:
                                buy_col = c
                            if 'sell' in c_lower or '卖' in c:
                                sell_col = c
                        
                        if buy_col and sell_col:
                            net = float(bu_df[buy_col].sum()) - float(bu_df[sell_col].sum())
                        else:
                            vol_col = None
                            for c in cols:
                                if 'volume' in c.lower() or '成交量' in c:
                                    vol_col = c
                            if vol_col:
                                net = float(bu_df[vol_col].sum())
                            else:
                                net = float(bu_df.iloc[:, 1].sum()) if bu_df.shape[1] > 1 else 0
                        
                        print(f"[L1] BU net position: {net:.0f} lots")
                        return net, 'akshare_get_shfe_rank_table', 1.0
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
    value, source, confidence = fetch_shfe_net_position(obs_date)
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[FAIL] {FACTOR_CODE} all sources failed")
