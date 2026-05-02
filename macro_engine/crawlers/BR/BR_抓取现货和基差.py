#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取现货和基差
因子: 待定义 = 抓取现货和基差

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import akshare as ak
import pandas as pd
from datetime import timedelta

SYMBOL = "BR"


def fetch_br_ref_price(obs_date):
    """获取丁二烯橡胶华东参考价，尝试最近5个工作日"""
    for delta in range(8):
        check = obs_date - timedelta(days=delta)
        if check.weekday() >= 5:
            continue
        date_str = check.strftime('%Y%m%d')
        try:
            df = ak.futures_spot_price(date=date_str, vars_list=["BR"])
            if df is None or df.empty:
                continue
            row = df.iloc[-1]
            ref_price = float(row.get("near_contract_price") or row.get("spot_price") or 0)
            if ref_price <= 0:
                continue
            print(f"  [L1] BR参考价({date_str}): near_contract_price={ref_price}")
            return ref_price, check
        except Exception as e:
            print(f"  [L1] BR参考价({date_str}): {e}")
    return None, None


def fetch_br0_settlement():
    """获取BR0主力合约结算价"""
    try:
        df = ak.futures_main_sina(symbol="BR0")
        if df is None or df.empty:
            return None
        latest = df.iloc[-1]
        settle = float(latest.get("动态结算价") or latest.get("收盘价") or 0)
        date_str = str(latest.get("日期", "N/A"))
        print(f"  [L1] BR0结算价({date_str}): {settle}")
        return settle
    except Exception as e:
        print(f"  [L1] BR0结算价获取失败: {e}")
        return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === BR现货/基差/毛利 === obs={obs_date}")

    # L1: 获取BR参考价
    ref_price, actual_date = fetch_br_ref_price(obs_date)
    if ref_price is None:
        print("  [ERROR] BR参考价获取失败，尝试L4回补")
        v = get_latest_value("BR_SPOT_PRICE", SYMBOL)
        if v is not None:
            save_to_db("BR_REF_PRICE", SYMBOL, pub_date, obs_date, v,
                       source_confidence=0.5, source="db_L4回补")
            print(f"  [L4] BR_SPOT_PRICE={v} 回补成功")
        else:
            print("  [WARN] BR参考价无任何数据")
        return 1

    # L1: 获取BR0结算价并计算基差
    br0_settle = fetch_br0_settlement()
    if br0_settle is None:
        br0_settle = get_latest_value("BR_SPD_BASIS", SYMBOL)
        if br0_settle is not None:
            br0_settle = None  # 不使用旧基差值
        print("  [WARN] BR0结算价获取失败，跳过基差计算")

    # 写BR现货参考价
    save_to_db("BR_SPOT_PRICE", SYMBOL, pub_date, actual_date, ref_price,
               source_confidence=1.0, source="akshare_futures_spot_price(near_contract_price)")
    print(f"  ✅ BR_SPOT_PRICE={ref_price} 写入成功")

    # 计算并写BR基差
    if br0_settle is not None:
        basis = ref_price - br0_settle
        save_to_db("BR_SPD_BASIS", SYMBOL, pub_date, actual_date, basis,
                   source_confidence=1.0, source="手动计算(现货-BR0结算价)")
        print(f"  ✅ BR_SPD_BASIS={basis} (现货{ref_price}-期货结算价{br0_settle})")
    else:
        print("  [SKIP] BR0结算价缺失，跳过基差")

    # 派生BR行业毛利 = 现货参考价 - 丁二烯×0.82 - 3000
    bd_cost = get_latest_value("BR_COST_BD", SYMBOL)
    if bd_cost is None:
        print("  [WARN] 丁二烯成本无数据，跳过毛利计算")
        return 0
    margin = ref_price - bd_cost * 0.82 - 3000
    save_to_db("BR_COST_MARGIN", SYMBOL, pub_date, actual_date, margin,
               source_confidence=0.9, source="派生(现货-BD×0.82-3000)")
    print(f"  ✅ BR_COST_MARGIN={margin:.1f} ({ref_price}-{bd_cost}x0.82-3000)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
