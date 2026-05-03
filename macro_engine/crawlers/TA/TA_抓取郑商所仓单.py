#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取郑商所仓单
因子: TA_STK_WARRANT = 抓取郑商所仓单

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
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

FACTOR_CODE = "TA_STK_WARRANT"
SYMBOL = "TA"


def fetch_warrant(obs_date):
    """获取郑商所PTA仓单总量（仅查工作日）"""
    for delta in range(10):
        check_date = obs_date - timedelta(days=delta)
        if check_date.weekday() >= 5:
            continue
        date_str = check_date.strftime('%Y%m%d')
        try:
            result = ak.futures_warehouse_receipt_czce(date=date_str)
            if not isinstance(result, dict):
                print(f"  CZCE({date_str}): 非dict类型={type(result).__name__}")
                continue
            if 'PTA' not in result:
                print(f"  CZCE({date_str}): dict但无PTA键，keys={str(list(result.keys()))[:60]}")
                continue
            pta_df = result['PTA']
            if pta_df is None or pta_df.empty:
                print(f"  CZCE({date_str}): PTA数据为空")
                continue
            # 找"总计"行
            total_rows = pta_df[pta_df.apply(lambda r: '总计' in str(r.iloc[0]), axis=1)]
            if total_rows.empty:
                print(f"  CZCE({date_str}): 无总计行")
                continue
            total_row = total_rows.iloc[0]
            # 找仓单数列（可能有"仓单数量(完税)"或"仓单数量"）
            col_name = None
            for col in pta_df.columns:
                if '仓单数量' in col:
                    col_name = col
                    break
            if col_name is None:
                print(f"  CZCE({date_str}): 无仓单数列，columns={list(pta_df.columns)}")
                continue
            total_warrant = float(total_row[col_name])
            if total_warrant > 0:
                print(f"[L1] 郑商所PTA仓单({date_str}): {total_warrant:.0f}张 ({col_name})")
                return total_warrant
            else:
                print(f"  CZCE({date_str}): 总计={total_warrant}, 无效")
        except Exception as e:
            print(f"  CZCE({date_str}): {e}")
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    warrant = fetch_warrant(obs_date)
    if warrant is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, warrant,
                   source_confidence=1.0, source="akshare_futures_warehouse_receipt_czce")
        print(f"OK {FACTOR_CODE}={warrant:.0f}")
        return 0
    else:
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v,
                       source_confidence=0.5, source="db_回补")
            print(f"OK {FACTOR_CODE}={v:.0f} L4")
        else:
            print("[WARN] 仓单全失败，跳过")
        return 0


if __name__ == "__main__":
    sys.exit(main())
