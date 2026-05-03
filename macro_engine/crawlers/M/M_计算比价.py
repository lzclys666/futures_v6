#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算比价
因子: 待定义 = 计算比价

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
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import akshare as ak

SYMBOL = "M"

def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print("(auto) === M比价 === obs={}".format(obs_date))
    try:
        date_str = obs_date.strftime("%Y%m%d")
        df = ak.futures_spot_price(date=date_str, vars_list=["M", "RU"])
        if df is not None and len(df) > 0:
            row = df[df["symbol"] == "M"]
            ru = df[df["symbol"] == "RU"]
            if len(row) and len(ru):
                ratio = round(float(row.iloc[-1]["spot_price"]) / float(ru.iloc[-1]["spot_price"]), 4)
                save_to_db("M_SPD_NEAR_FAR", SYMBOL, pub_date, obs_date, ratio, source_confidence=1.0, source="akshare_futures_spot_price")
                print(">>> M_SPD_NEAR_FAR={} 写入成功".format(ratio))
                return
    except Exception as e:
        print("[L1] 失败: {}".format(e))
    v = get_latest_value("M_SPD_NEAR_FAR", SYMBOL)
    if v is not None:
        save_to_db("M_SPD_NEAR_FAR", SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
        print(">>> M_SPD_NEAR_FAR={} L4回补成功".format(v))

if __name__ == "__main__":
    main()
