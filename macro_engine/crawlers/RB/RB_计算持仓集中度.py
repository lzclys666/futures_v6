#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算持仓集中度
因子: RB_POS_CONCENTRATION = 计算持仓集中度

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

FACTOR_CODE = "RB_POS_CONCENTRATION"
SYMBOL = "RB"

def fetch_concentration():
    # L1: AKShare 上期所持仓排名
    try:
        print("[L1] AKShare get_shfe_rank_table...")
        df = ak.get_shfe_rank_table()
        if df is not None and len(df) > 0:
            rb_df = df[df['variety'] == 'RB']
            if len(rb_df) > 0:
                # 找volume列，计算CR10
                cols = rb_df.columns.tolist()
                vol_col = None
                for c in cols:
                    if 'volume' in str(c).lower() or '成交量' in str(c):
                        vol_col = c; break
                if vol_col is None:
                    vol_col = cols[3] if len(cols) > 3 else cols[-1]
                
                total_vol = float(rb_df[vol_col].sum())
                top10_vol = float(rb_df.head(10)[vol_col].sum())
                cr10 = (top10_vol / total_vol * 100) if total_vol > 0 else 0
                
                if 0 < cr10 < 100:
                    print(f"[L1] 成功: CR10={cr10:.2f}%")
                    return cr10, 'akshare', 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")
    
    # L4: DB回补
    print("[L4] DB历史回补...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None:
        print(f"[L4] 兜底: {val}")
        return val, 'db_回补', 0.5
    return None, None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("非交易日，跳过"); exit(0)
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, source, confidence = fetch_concentration()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[失败] {FACTOR_CODE} 所有数据源均失败")
