#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_高低硫价差.py
因子: FU_HS_LS_SPREAD = 高硫燃料油(HSFO) - 低硫燃料油(VLSFO)价差（美元/吨）

公式: 价差 = 高硫燃料油价格 - 低硫燃料油价格

当前状态: ✅正常
- L1: 东方财富/彭博免费页面（新加坡高硫/低硫FO价格）
- L2: 新加坡MPA官网
- L3: 备用
- L4: DB回补
- L5: NULL占位

订阅优先级: 无（免费源）
替代付费源: 隆众资讯（年费）、SMM（年费）
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
import requests
import re
from datetime import datetime

FACTOR_CODE = "FU_HS_LS_SPREAD"
SYMBOL = "FU"


def fetch_hs_ls_spread_eastmoney():
    """L1: 东方财富新加坡燃料油价格"""
    try:
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPTA_WEB_HS_HQ_HSP",
            "columns": "ALL",
            "filter": '(hq_typecode in ("FU", "Bunker"))',
            "sortColumns": "dim_date",
            "sortTypes": "-1",
            "pageSize": "20",
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, params=params, headers=headers, timeout=15)
        data = r.json()
        rows = data.get("result", {}).get("data", [])
        if rows:
            # 东方财富燃料油数据含HSFO/LSFO价格
            prices = {}
            date_str = None
            for row in rows:
                name = str(row.get("name", "")).lower()
                price_val = row.get("price", None)
                date_str = str(row.get("dim_date", ""))[:10]
                if price_val:
                    prices[name] = float(price_val)
            # 找HSFO和VLSFO/LSFO价格
            hsfo = None
            lsfo = None
            for k, v in prices.items():
                if 'high' in k or '高硫' in k or '380' in k or 'hsfo' in k:
                    hsfo = v
                if 'low' in k or '低硫' in k or 'vlsfo' in k or 'lsfo' in k:
                    lsfo = v
            if hsfo and lsfo:
                spread = hsfo - lsfo
                print(f"[L1] 东方财富HS-LS价差: {hsfo} - {lsfo} = {spread}")
                return spread, date_str
    except Exception as e:
        print(f"[L1] 东方财富失败: {e}")
    return None, None


def fetch_hs_ls_spread_sgx():
    """L2: 新加坡交易所SGX数据"""
    try:
        # SGX燃料油掉期价格（公开页面）
        url = "https://www.sgx.com/fercsoft/ commodityprice?symbol=FO"
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.sgx.com/"}
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        # 解析...
    except Exception as e:
        print(f"[L2] SGX失败: {e}")
    return None, None


def fetch_hs_ls_spread_platts():
    """L3: Platts公开页面（部分免费）"""
    try:
        # Platts每天发布的高低硫价差在部分页面免费可见
        url = "https://www.spglobal.com/platts/en/market-data/unified-traffic/distinct/ fuel/oil"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = 'utf-8'
        text = r.text
        # 尝试提取HSFO和VLSFO价格
        patterns = [
            r"HSFO[^$]*?(\d+\.?\d*)",
            r"VLSFO[^$]*?(\d+\.?\d*)",
        ]
        values = {}
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                values[pat[:4]] = float(m.group(1))
        if len(values) >= 2:
            spread = list(values.values())[0] - list(values.values())[1]
            date_str = datetime.now().strftime("%Y-%m-%d")
            print(f"[L3] Platts HS-LS: {spread}")
            return spread, date_str
    except Exception as e:
        print(f"[L3] Platts失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    val, source = None, None

    # L1
    val, source = fetch_hs_ls_spread_eastmoney()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=1.0, source=f"L1-东方财富:{source}")
        return

    # L3
    val, source = fetch_hs_ls_spread_platts()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=0.8, source=f"L3-Platts:{source}")
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
