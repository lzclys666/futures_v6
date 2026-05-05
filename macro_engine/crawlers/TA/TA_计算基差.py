#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算基差
因子: TA_SPD_BASIS = 计算基差

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates
import akshare as ak
import pandas as pd
from datetime import timedelta

FACTOR_CODE = "TA_SPD_BASIS"
SYMBOL = "TA"


def fetch_basis(obs_date):
    """动态获取PTA基差，跳过历史回补"""
    date_str = obs_date.strftime('%Y%m%d')

    # L1a: AKShare futures_spot_price（TA基差数据）
    try:
        df = ak.futures_spot_price(date=date_str, vars_list=["TA"])
        if df is not None and len(df) > 0:
            row = df.iloc[-1]
            # 优先用 near_basis
            if "near_basis" in row.index and pd.notna(row["near_basis"]):
                val = float(row["near_basis"])
                if -200 <= val <= 200:  # 合理基差范围
                    print(f"[L1a] near_basis: {val} 元/吨")
                    return val, 1.0, "akshare_futures_spot_price(near_basis)"
            # 备选：spot - near_contract_price
            if pd.notna(row.get("spot_price")) and pd.notna(row.get("near_contract_price")):
                spot = float(row["spot_price"])
                near = float(row["near_contract_price"])
                val = spot - near
                if -200 <= val <= 200:
                    print(f"[L1a] spot-near: {spot:.0f}-{near:.0f}={val:.0f}")
                    return val, 1.0, "akshare_futures_spot_price(spot-near)"
    except Exception as e:
        print(f"[L1a] {e}")

    # L1b: 手动算（主力期货-现货）
    try:
        df_spot = ak.futures_spot_price(date=date_str, vars_list=["PTA"])
        df_fut = ak.futures_main_sina(symbol="TA0")
        if df_spot is not None and len(df_spot) > 0 and df_fut is not None and len(df_fut) > 0:
            spot = float(df_spot.iloc[-1]["spot_price"])
            # 取最近交易日主力收盘价
            fut_price = float(df_fut.sort_values('日期').iloc[-1]['收盘价'])
            val = spot - fut_price
            if -200 <= val <= 200:
                print(f"[L1b] 现货-期货: {spot:.0f}-{fut_price:.0f}={val:.0f}")
                return val, 0.9, "akshare(现货+TA0)"
    except Exception as e:
        print(f"[L1b] {e}")

    print("[INFO] 无PTA基差数据，基差因子跳过（L4不回补）")
    return None, None, None


def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    # 最多回溯5个交易日找数据
    for delta in range(5):
        check_date = obs_date - timedelta(days=delta)
        print(f"\n=== {FACTOR_CODE} === obs={obs_date} (实际查={check_date})")
        val, conf, src = fetch_basis(check_date)
        if val is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                       source_confidence=conf, source=src)
            print(f"[OK] {FACTOR_CODE}={val:.2f} 写入成功")
            return 0
    print("[L4] TA_SPD_BASIS无数据，跳过（L4不回补基差）")
    return 0


if __name__ == "__main__":
    import argparse
    sys.exit(main())
