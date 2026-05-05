#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取上期所螺纹钢仓单
因子: RB_INV_SHFE = 抓取上期所螺纹钢仓单

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
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback

import akshare as ak

FACTOR_CODE = "RB_INV_SHFE"
SYMBOL = "RB"

def fetch_shfe_receipt(obs_date):
    # L1: AKShare 上期所仓单
    try:
        print(f"[L1] AKShare futures_shfe_warehouse_receipt obs={obs_date}...")
        date_str = obs_date.strftime("%Y%m%d") if hasattr(obs_date, 'strftime') else obs_date.replace("-", "")
        df = ak.futures_shfe_warehouse_receipt(date=date_str)
        if df is not None and len(df) > 0:
            cols = df.columns.tolist()
            rb_col = None
            for c in cols:
                if '螺纹' in str(c) or 'RB' in str(c):
                    rb_col = c; break
            if rb_col is None:
                # 查找所有含数字的列
                for c in cols:
                    if any(x in str(c) for x in ['仓单', '库存', '吨']):
                        rb_col = c; break
                if rb_col is None:
                    rb_col = cols[-1]
            val = df.iloc[-1][rb_col]
            if isinstance(val, str):
                val = val.replace(',', '').strip()
            val = float(val)
            if 0 <= val <= 1000000:
                print(f"[L1] 成功: {val:.0f} 吨")
                return val, 'akshare', 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")
    
    # L2: 上期所官网爬取
    try:
        print("[L2] 上期所官网...")
        # TODO: 上期所官网仓单数据爬取
    except Exception as e:
        print(f"[L2] 失败: {e}")
    
    # L4: DB回补 (moved to main)
    return None, None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("非交易日，跳过"); exit(0)
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, source, confidence = fetch_shfe_receipt(obs_date)
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
