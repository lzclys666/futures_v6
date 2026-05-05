#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取库存
因子: 待定义 = 抓取库存

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback
import akshare as ak

SYMBOL = "RU"

def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print("(auto) === RU库存 === obs={}".format(obs_date))
    try:
        df = ak.futures_inventory_em(symbol="橡胶")
        if df is not None and len(df) > 0:
            val = float(df.iloc[-1].iloc[1])
            save_to_db("RU_INV_QINGDAO", SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_futures_inventory_em")
            print(">>> RU_INV_QINGDAO={} 写入成功".format(val))
            return
    except Exception as e:
        print("[L1] 失败: {}".format(e))
    save_l4_fallback("RU_INV_QINGDAO", SYMBOL, pub_date, obs_date)

if __name__ == "__main__":
    main()
