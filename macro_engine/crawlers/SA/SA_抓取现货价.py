#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取现货价
因子: sa_spot_price = 抓取现货价

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
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

FACTOR_CODE = "sa_spot_price"
SYMBOL = "SA"

def fetch(obs_date):
    print(f"[L1] AKShare futures_spot_price obs={obs_date}...")
    date_str = obs_date.strftime("%Y%m%d") if hasattr(obs_date, 'strftime') else obs_date.replace("-", "")
    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])
    if df is not None and not df.empty:
        row = df.iloc[-1]
        val = float(row["spot_price"])
        print(f"[L1] SA现货价: {val} 元/吨")
        return val, "akshare_futures_spot_price", 1.0
    return None, None, None

def main():
    import argparse
    auto = argparse.ArgumentParser().parse_known_args()[0]
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")
    val, src, conf = fetch(obs_date)
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, src, conf)
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
    else:
        print(f"[L4] DB回补...")
        # L4: 保留原始obs_date，不覆盖已有今日数据
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if ok:
            print(f"[OK] {FACTOR_CODE} L4回补成功")
        else:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")

if __name__ == "__main__":
    main()
