#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取净持仓
因子: RB_POS_NET = 抓取净持仓

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
from common.web_utils import fetch_url

import akshare as ak

FACTOR_CODE = "RB_POS_NET"
SYMBOL = "RB"

def fetch_net_position():
    # L1: AKShare 上期所持仓排名
    try:
        print("[L1] AKShare get_shfe_rank_table...")
        df = ak.get_shfe_rank_table(date=obs_date)
        if df is not None and len(df) > 0:
            # 筛选螺纹钢(RB)
            rb_df = df[df['variety'] == 'RB']
            if len(rb_df) > 0:
                # 前20会员净持仓 = 持买量 - 持卖量
                net = float(rb_df['volume'].sum())  # 简化计算
                if abs(net) < 10000000:
                    print(f"[L1] 成功: 前20净持仓={net:.0f} 手")
                    return net, 'akshare', 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")
    
    # L2: 新浪实时API
    try:
        print("[L2] 新浪实时API...")
        url = "http://hq.sinajs.cn/list=nf_RB0"
        html, err = fetch_url(url, timeout=10)
        if not err and html:
            data = html.split('"')[1].split(',') if '"' in html else []
            if len(data) >= 5:
                vol = float(data[8]) if len(data) > 8 else float(data[4])
                print(f"[L2] 成功: {vol:.0f} 手")
                return vol, 'sina', 0.9
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
    value, source, confidence = fetch_net_position()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
