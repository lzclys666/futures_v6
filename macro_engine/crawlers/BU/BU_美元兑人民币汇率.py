#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_美元兑人民币汇率.py
因子: BU_BU_FX_USDCNY = 美元兑人民币汇率

公式: 数据采集（无独立计算公式）

当前状态: [OK]正常
- 数据源: AKShare fx_spot_quote()（L1）+ 新浪财经 hq.sinajs.cn/list=USDCNY（L2备用）
- 采集逻辑: fx_spot_quote的USD/CNY买报价/卖报价取均值
- obs_date: 数据日期（北京时间）
- bounds: [6.5, 7.5]（USD/CNY合理区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
from common.web_utils import fetch_url, fetch_json

import akshare as ak
import pandas as pd

FACTOR_CODE = "BU_BU_FX_USDCNY"
SYMBOL = "BU"
BOUNDS = (6.5, 7.5)


def fetch_akshare():
    """L1: AKShare fx_spot_quote"""
    print("[L1] AKShare fx_spot_quote()...")
    df = ak.fx_spot_quote()
    if df is None or df.empty:
        raise ValueError("empty")
    # 列名: ['货币对', '买报价', '卖报价']
    usd_row = df[df["货币对"].astype(str).str.contains("USD")]
    if usd_row.empty:
        raise ValueError("no USD pair")
    row = usd_row.iloc[-1]
    bid = float(row["买报价"])
    ask = float(row["卖报价"])
    if bid <= 0 or ask <= 0 or pd.isna(bid) or pd.isna(ask):
        raise ValueError(f"USD/CNY报价异常 bid={bid} ask={ask}")
    return (bid + ask) / 2


def fetch_sina():
    """L2: 新浪财经实时汇率"""
    print("[L2] 新浪 hq.sinajs.cn/list=USDCNY...")
    headers = {
        "Referer": "https://finance.sina.com.cn"
    }
    html, err = fetch_url("https://hq.sinajs.cn/list=USDCNY", headers=headers, timeout=10)
    if err:
        raise ValueError(err)
    text = html
    # 格式: var hq_str_USDCNY="02:58:07,6.8268,6.8278,6.8279,11,6.8278,6.8279,6.8268,6.8273,美元人民币,2026-05-02";
    import re
    m = re.search(r'hq_str_USDCNY="[^,]+,([^,]+),([^,]+)', text)
    if not m:
        raise ValueError("无法解析Sina响应")
    bid = float(m.group(1))
    ask = float(m.group(2))
    if bid <= 0 or ask <= 0:
        raise ValueError(f"Sina USD/CNY异常 bid={bid} ask={ask}")
    return (bid + ask) / 2


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()

    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); sys.exit(0)

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    raw_value = None
    for fetch_fn, tag in [(fetch_akshare, "[L1]"), (fetch_sina, "[L2]")]:
        try:
            raw_value = fetch_fn()
            break
        except Exception as e:
            print(f"{tag} 失败: {e}")

    if raw_value is None:
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            print(f"[L4] 兜底: {val}")
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                       source="db_回补", source_confidence=0.5)
        else:
            print(f"[WARN] {FACTOR_CODE} 所有数据源均失败")
        sys.exit(0)

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        sys.exit(0)

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
               source="akshare_fx_spot_quote", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value}")
