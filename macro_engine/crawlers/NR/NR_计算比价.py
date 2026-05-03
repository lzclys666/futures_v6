#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算比价
因子: NR_SPD_RU_NR = 计算比价

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

SYMBOL = "NR"
FACTOR_CODE = "NR_SPD_RU_NR"


def fetch_ratio(obs_date_str):
    """
    获取 NR/RU 比价。
    L1: NR0 期货主力 / RU0 期货主力（日线）
    返回: (ratio_float, source_str) 或 (None, None)
    """
    # L1: 期货主力日线
    try:
        nr_df = ak.futures_zh_daily_sina(symbol="NR0")
        ru_df = ak.futures_zh_daily_sina(symbol="RU0")
        if nr_df is not None and ru_df is not None and len(nr_df) > 0 and len(ru_df) > 0:
            # 取最新收盘价
            nr_price = float(nr_df.iloc[-1]["close"])
            ru_price = float(ru_df.iloc[-1]["close"])
            if ru_price > 0:
                ratio = round(nr_price / ru_price, 4)
                print(f"  [L1] NR0={nr_price} / RU0={ru_price} = {ratio}")
                return ratio, "NR期货主力/RU期货主力(akshare)"
    except Exception as e:
        print(f"  [L1] NR/RU 期货主力失败: {e}")

    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    # obs_date 可能是 YYYYMMDD 整数或 YYYY-MM-DD 字符串
    obs_str = str(obs_date).replace("-", "")

    # L1: 取比价
    ratio, src = fetch_ratio(obs_str)

    if ratio is not None:
        # 合理性校验（NR/RU 比价正常范围 0.6~1.5）
        if not (0.3 <= ratio <= 3.0):
            print(f"  警告: 比价 {ratio} 超出合理范围[0.3, 3.0]，跳过写入")
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, ratio, src, 1.0)
            print(f">>> {FACTOR_CODE}={ratio} 写入成功")
            return

    # L4: 数据库回补（仅在 L1 失败时）
    print("  [L4] L1失败，尝试数据库回补...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None and 0.3 <= val <= 3.0:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source="db_回补")
        print(f">>> {FACTOR_CODE}={val} L4回补成功")
    else:
        print(f"FAIL: NR/RU 比价无数据（无有效回补值 val={val}）")


if __name__ == "__main__":
    main()
