#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_WTI收盘价.py
因子: FU_WTI_PRICE = WTI原油期货收盘价（美元/桶）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- L1: AKShare energy_oil_hist（东方财富原油历史数据，非国际WTI但高度相关）
- L2: Web scraping from public sources（EIA/金十数据）
- L3: 备用免费数据源
- L4: DB回补
- L5: NULL占位

订阅优先级: 无（免费源）
替代付费源: 无
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value, _get_latest_record
import akshare as ak
import requests
import pandas as pd

FACTOR_CODE = "FU_WTI_PRICE"
SYMBOL = "FU"


def fetch_wti_eastmoney():
    """L1: AKShare energy_oil_hist（东方财富原油数据中心）"""
    try:
        df = ak.energy_oil_hist()
        if df is not None and len(df) > 0:
            # 取最新一行，尝试匹配WTI或Brent相关行
            # energy_oil_hist返回的是国内原油品种历史数据
            df_col_map = {str(c).strip(): c for c in df.columns}
            # 找"日期"和"收盘价"列
            date_col = df_col_map.get('日期', None)
            price_col = df_col_map.get('收盘价', None)
            if date_col and price_col:
                latest = df.iloc[-1]
                val = float(latest[price_col])
                date_str = str(latest[date_col])[:10]
                print(f"[L1] energy_oil_hist: {date_str} -> {val}")
                return val, date_str
    except Exception as e:
        print(f"[L1] energy_oil_hist失败: {e}")
    return None, None


def fetch_wti_jin10():
    """L2: 金十数据 API（国际原油）"""
    try:
        url = "https://cdn.jin10.com/data_center/reports/usa_oil.json"
        r = requests.get(url, timeout=10)
        data = r.json()
        values = data.get("values", {})
        # WTI原油价格
        wti_price = values.get("美国WTI原油价格", [None, None])
        if wti_price and wti_price[0]:
            val = float(wti_price[0])
            date_str = data.get("date", "")[:10]
            print(f"[L2] jin10 WTI: {date_str} -> {val}")
            return val, date_str
    except Exception as e:
        print(f"[L2] jin10失败: {e}")
    return None, None


def fetch_wti_eia():
    """L3: EIA官网免费数据"""
    try:
        url = "https://api.eia.gov/v2/petroleum/pri/spt/data/?api_key=DEMO_KEY&frequency=daily&data[0]=value&facets[product][]=EPCWTI&sort[0][column]=period&sort[0][direction]=desc&length=2"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("response", {}).get("data"):
            latest = data["response"]["data"][0]
            val = float(latest["value"])
            date_str = latest["period"][:10]
            print(f"[L3] EIA WTI: {date_str} -> {val}")
            return val, date_str
    except Exception as e:
        print(f"[L3] EIA失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    val, source = None, None
    # L1
    val, source = fetch_wti_eastmoney()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=1.0, source=f"L1-AKShare-东方财富:{source}")
        return

    # L2
    val, source = fetch_wti_jin10()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=0.9, source=f"L2-金十数据:{source}")
        return

    # L3
    val, source = fetch_wti_eia()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=0.9, source=f"L3-EIA:{source}")
        return

    # L4: DB fallback
    record = _get_latest_record(FACTOR_CODE, SYMBOL)
    if record:
        raw_value, orig_obs_date, orig_source, orig_conf = record
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
                    source_confidence=0.5, source=f"L4回补({orig_source})")
        print(f"[L4] {FACTOR_CODE}={raw_value} 回补成功")
        return

    print(f"[L5] {FACTOR_CODE}: 所有数据源失效，写入NULL占位")
    # NULL占位（source_confidence=0.0 触发豁免写入）
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                source_confidence=0.0, source="L5-NULL占位")


if __name__ == "__main__":
    main()
