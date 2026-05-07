#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_高低硫价差.py
因子: FU_HS_LS_SPREAD = 高硫燃料油(HSFO) - 低硫燃料油(VLSFO)价差（美元/吨）

公式: 价差 = HSFO(IFO380) - VLSFO（美元/吨）

当前状态: [⚠️待验证]
- L1 Ship&Bunker HTML选择器依赖页面结构，网站改版会失效
- L2 东方财富报表名为推测，未实测
- L3 SGX ferrous页面可能不含燃料油（属能源品类）

订阅优先级: 无（全部免费源）
替代付费源: 隆众资讯（年费）、SMM（年费）
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
from common.web_utils import fetch_json, fetch_url
from datetime import datetime

FACTOR_CODE = "FU_HS_LS_SPREAD"
SYMBOL = "FU"
BOUNDS = (-200, 300)  # 高硫-低硫价差，当前市场VLSFO溢价(-136正常)


def fetch_hs_ls_spread_shipandbunker():
    """L1: Ship & Bunker 新加坡船舶燃油价格（免费，无需认证）

    抓取 https://shipandbunker.com/prices 页面中新加坡的 VLSFO 和 IFO380(HSFO) 报价。
    返回 (spread, date_str) 或 (None, None)。
    """
    url = "https://shipandbunker.com/prices"
    text, err = fetch_url(url, encoding='utf-8', timeout=20)
    if err:
        print(f"[L1] Ship&Bunker 获取失败: {err}")
        return None, None

    try:
        # 提取新加坡 VLSFO 价格: <th id="row-sg-sin-VLSFO">...<td headers="price-VLSFO">815.00
        vlsfo_match = re.search(
            r'id="row-sg-sin-VLSFO"[^>]*>.*?headers="price-VLSFO">([\d.]+)',
            text, re.DOTALL
        )
        # 提取新加坡 IFO380 (HSFO) 价格
        hsfo_match = re.search(
            r'id="row-sg-sin-IFO380"[^>]*>.*?headers="price-IFO380">([\d.]+)',
            text, re.DOTALL
        )

        if not vlsfo_match or not hsfo_match:
            print("[L1] Ship&Bunker: 未找到新加坡 VLSFO 或 IFO380 数据")
            # 尝试备用页面：新加坡专页
            sg_url = "https://shipandbunker.com/prices/apac/sea/sg-sin-singapore"
            text2, err2 = fetch_url(sg_url, encoding='utf-8', timeout=20)
            if err2:
                print(f"[L1] Ship&Bunker 新加坡专页也失败: {err2}")
                return None, None
            vlsfo_match = re.search(
                r'id="row-sg-sin-VLSFO"[^>]*>.*?headers="price-VLSFO">([\d.]+)',
                text2, re.DOTALL
            )
            hsfo_match = re.search(
                r'id="row-sg-sin-IFO380"[^>]*>.*?headers="price-IFO380">([\d.]+)',
                text2, re.DOTALL
            )
            if not vlsfo_match or not hsfo_match:
                print("[L1] Ship&Bunker: 新加坡专页也未找到数据")
                return None, None

        vlsfo = float(vlsfo_match.group(1))
        hsfo = float(hsfo_match.group(1))

        # 价差 = 高硫 - 低硫
        spread = hsfo - vlsfo
        date_str = datetime.now().strftime("%Y-%m-%d")

        # 基本合理性校验
        if not (BOUNDS[0] <= spread <= BOUNDS[1]):
            print(f"[L1] Ship&Bunker: 价差 {spread} 超出合理范围 {BOUNDS}，丢弃")
            return None, None

        print(f"[L1] Ship&Bunker HSFO({hsfo}) - VLSFO({vlsfo}) = {spread} $/mt")
        return spread, date_str

    except Exception as e:
        print(f"[L1] Ship&Bunker 解析异常: {e}")
        return None, None


def fetch_hs_ls_spread_eastmoney():
    """L2: 东方财富全球大宗商品（备用源）

    尝试从东方财富数据中心获取新加坡燃料油相关报价。
    注意：此 API 的报表名可能变更，如失败则跳过。
    """
    # 尝试多个可能的报表名
    report_names = [
        "RPTA_WEB_COMMODITY_BUNKERPRICE",
        "RPTA_WEB_GLOBALCOMMODITY",
        "RPTA_WEB_INTL_BUNKER",
    ]

    for rpt in report_names:
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": rpt,
            "columns": "ALL",
            "sortColumns": "dim_date",
            "sortTypes": "-1",
            "pageSize": "30",
        }
        data, err = fetch_json(url, params=params, timeout=15)
        if err or not data:
            continue
        if not data.get("success"):
            continue

        try:
            rows = data.get("result", {}).get("data", [])
            if not rows:
                continue

            prices = {}
            date_str = None
            for row in rows:
                name = str(row.get("name", "")).lower()
                price_val = row.get("price", None)
                date_str = str(row.get("dim_date", ""))[:10]
                if price_val:
                    prices[name] = float(price_val)

            hsfo = None
            lsfo = None
            for k, v in prices.items():
                if any(kw in k for kw in ['high', '高硫', '380', 'hsfo', 'ifo380']):
                    hsfo = v
                if any(kw in k for kw in ['low', '低硫', 'vlsfo', 'lsfo']):
                    lsfo = v

            if hsfo and lsfo:
                spread = hsfo - lsfo
                if BOUNDS[0] <= spread <= BOUNDS[1]:
                    print(f"[L2] 东方财富({rpt}) HS-LS: {hsfo} - {lsfo} = {spread}")
                    return spread, date_str
        except Exception as e:
            print(f"[L2] 东方财富({rpt}) 解析失败: {e}")
            continue

    print("[L2] 东方财富: 所有报表均不可用")
    return None, None


def fetch_hs_ls_spread_sgx():
    """L3: SGX 新加坡交易所（备用，通常需 JS 渲染，成功率低）

    尝试从 SGX 获取燃料油期货结算价。
    """
    url = "https://www.sgx.com/derivatives/commodity/ferrous"
    text, err = fetch_url(url, encoding='utf-8', timeout=20)
    if err:
        print(f"[L3] SGX 获取失败: {err}")
        return None, None

    try:
        # 尝试匹配燃料油相关数据
        # SGX 页面通常需要 JS 渲染，纯 HTML 可能没有数据
        hsfo_match = re.search(r'(?:HSFO|380CST|IFO380)[^\d]*?([\d,]+\.?\d*)', text, re.IGNORECASE)
        vlsfo_match = re.search(r'(?:VLSFO|0\.5%S)[^\d]*?([\d,]+\.?\d*)', text, re.IGNORECASE)

        if hsfo_match and vlsfo_match:
            hsfo = float(hsfo_match.group(1).replace(',', ''))
            vlsfo = float(vlsfo_match.group(1).replace(',', ''))
            spread = hsfo - vlsfo
            if BOUNDS[0] <= spread <= BOUNDS[1]:
                date_str = datetime.now().strftime("%Y-%m-%d")
                print(f"[L3] SGX HS-LS: {hsfo} - {vlsfo} = {spread}")
                return spread, date_str

        print("[L3] SGX: 页面无直接数据（需 JS 渲染）")
    except Exception as e:
        print(f"[L3] SGX 解析异常: {e}")

    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    # === L1: Ship & Bunker（首选） ===
    spread, date_str = fetch_hs_ls_spread_shipandbunker()
    if spread is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, spread,
                    source_confidence=0.9, source="Ship&Bunker")
        print(f"[L1] {FACTOR_CODE}={spread} 保存成功 (obs={date_str})")
        return

    # === L2: 东方财富（备用） ===
    spread, date_str = fetch_hs_ls_spread_eastmoney()
    if spread is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, spread,
                    source_confidence=0.7, source="东方财富")
        print(f"[L2] {FACTOR_CODE}={spread} 保存成功 (obs={date_str})")
        return

    # === L3: SGX（备用） ===
    spread, date_str = fetch_hs_ls_spread_sgx()
    if spread is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, spread,
                    source_confidence=0.6, source="SGX")
        print(f"[L3] {FACTOR_CODE}={spread} 保存成功 (obs={date_str})")
        return

    # === L4: DB fallback ===
    print("[跳过] L1/L2/L3 均无数据，尝试 DB 回补")
    from common.db_utils import save_l4_fallback
    ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, str(obs_date))
    if ok:
        return

    print(f"[L5] {FACTOR_CODE}: 无历史数据可回补")


if __name__ == "__main__":
    main()
