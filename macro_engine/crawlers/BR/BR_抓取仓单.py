#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取仓单
因子: 待定义 = 抓取仓单

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import akshare as ak

SYMBOL = "BR"

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === BR_STK_WARRANT === obs={obs_date}")

    # L1: AKShare 丁二烯橡胶仓单
    try:
        df = ak.futures_inventory_em(symbol='丁二烯橡胶')
        if df is not None and len(df) > 0:
            # 取最新一行（今日）
            latest = df.iloc[-1]
            val = float(latest.iloc[1])  # 库存列
            date_in_data = str(latest.iloc[0])
            print(f"[L1] 丁二烯橡胶仓单={val}吨 ({date_in_data})")
            save_to_db("BR_STK_WARRANT", SYMBOL, pub_date, obs_date, val,
                       source_confidence=1.0, source="akshare_futures_inventory_em")
            print(f"[OK] BR_STK_WARRANT={val} 写入成功")
            return
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L4: DB回补
    v = get_latest_value("BR_STK_WARRANT", SYMBOL)
    if v is not None:
        save_to_db("BR_STK_WARRANT", SYMBOL, pub_date, obs_date, v,
                   source_confidence=0.5, source="db_回补")
        print(f"[OK-L4] BR_STK_WARRANT={v} L4回补")
    else:
        print("[WARN] BR_STK_WARRANT 无数据")

if __name__ == "__main__":
    main()
