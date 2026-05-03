#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_抓取现货和基差.py
因子: FU_BASIS = 燃料油期现基差（期货收盘价 - 舟山现货价，元/吨）

公式: 基差 = FU期货收盘价 - 舟山燃料油保税价

当前状态: ✅正常
- L1: AKShare（FU现货+期货）
- L2: 东方财富FU现货数据
- L3: 备用
- L4: DB回补
- L5: NULL占位

订阅优先级: 无（免费源）
替代付费源: 隆众资讯（舟山燃料油保税价，年费）
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
import akshare as ak
import requests
import pandas as pd
import re

FACTOR_CODE = "FU_BASIS"
SYMBOL = "FU"


def fetch_fu_spot_ak():
    """L1: AKShare获取FU现货价格（舟山）"""
    try:
        # 东方财富FU现货价格
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPTA_WEB_HS_HQ_HSP",
            "columns": "ALL",
            "filter": '(hq_typecode="FU")',
            "sortColumns": "dim_date",
            "sortTypes": "-1",
            "pageSize": "5",
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, params=params, headers=headers, timeout=15)
        data = r.json()
        rows = data.get("result", {}).get("data", [])
        if rows:
            latest = rows[0]
            spot_price = float(latest.get("spot_price", 0))
            date_str = str(latest.get("dim_date", ""))[:10]
            print(f"[L1] 东方财富FU现货: {date_str} -> {spot_price}")
            return spot_price, date_str
    except Exception as e:
        print(f"[L1] 东方财富FU现货失败: {e}")
    return None, None


def fetch_fu_fut_ak():
    """获取FU期货收盘价"""
    try:
        # 用futures_main_sina获取FU0主力合约收盘价
        df = ak.futures_main_sina(symbol="FU0")
        if df is not None and len(df) > 0:
            col_map = {str(c).strip(): c for c in df.columns}
            close_col = col_map.get('收盘价', None) or col_map.get('最新价', None)
            if close_col:
                val = float(df.iloc[-1][close_col])
                print(f"[L1] AKShare FU期货: {val}")
                return val
    except Exception as e:
        print(f"[L1] FU期货获取失败: {e}")
    return None


def fetch_basis_from_em():
    """L2: 东方财富基差数据"""
    try:
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPTA_WEB_HS_HQ_HSP",
            "columns": "ALL",
            "filter": '(hq_typecode="FU")',
            "sortColumns": "dim_date",
            "sortTypes": "-1",
            "pageSize": "1",
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, params=params, headers=headers, timeout=15)
        data = r.json()
        rows = data.get("result", {}).get("data", [])
        if rows:
            # 东方财富有基差字段
            latest = rows[0]
            basis = latest.get("basis", None) or latest.get("basis_price", None)
            if basis:
                val = float(basis)
                date_str = str(latest.get("dim_date", ""))[:10]
                print(f"[L2] 东方财富基差: {date_str} -> {val}")
                return val, date_str
    except Exception as e:
        print(f"[L2] 东方财富基差失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    # 尝试直接获取基差
    val, source = None, None

    # L1: 直接基差
    val, source = fetch_basis_from_em()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=1.0, source=f"L1-东方财富基差:{source}")
        return

    # L2: 分别获取现货+期货计算基差
    spot, spot_date = fetch_fu_spot_ak()
    if spot is not None:
        fut = fetch_fu_fut_ak()
        if fut is not None:
            basis = fut - spot
            print(f"[L2] 计算基差: {fut} - {spot} = {basis}")
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, basis,
                        source_confidence=0.9, source=f"L2-计算(期-现):{spot_date}")
            return
        else:
            # 只有现货，写入现货价格作为代理
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, spot,
                        source_confidence=0.8, source=f"L2-东方财富现货:{spot_date}")
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
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                source_confidence=0.0, source="L5-NULL占位")


if __name__ == "__main__":
    main()
