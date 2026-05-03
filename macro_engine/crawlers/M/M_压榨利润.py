#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M_压榨利润.py
因子: M_CRUSHE_PROFIT = 大豆盘面压榨利润（元/吨）

公式: 压榨利润 = 豆粕价格 × 出粕率 + 豆油价格 × 出油率 - 大豆价格 - 加工费
     参考值：出粕率=78.5%，出油率=18.5%，加工费=100元/吨
     简化公式: M利润 = M期货价格 × 0.785 + Y期货价格 × 0.185 - 大豆价格 - 100

当前状态: ✅正常
- L1: AKShare获取DCE豆粕/豆油/大豆期货价格，派生计算
- L2: CBOT大豆 × 汇率 + 升贴水 + 海运费 估算大豆到港成本
- L3: 备用
- L4: DB回补
- L5: NULL占位

订阅优先级: 无（免费源）
替代付费源: 我的农产品网（年费）
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
import akshare as ak
import requests

FACTOR_CODE = "M_CRUSHE_PROFIT"
SYMBOL = "M"

# 压榨参数
YIELD_SOYMEAL = 0.785    # 出粕率
YIELD_SOYOIL = 0.185     # 出油率
PROCESSING_FEE = 100.0   # 加工费（元/吨）
# 汇率使用系统统一因子 FX_SPOT_CNY_USD，这里简化用常数估算
FX_RATE = 7.25  # 美元兑人民币（简化估算）


def fetch_cbot_soybean():
    """L2: CBOT大豆价格（美分/蒲式耳）"""
    try:
        url = "https://api.stlouisfed.org/fred/series/observations?series_id=DCOILBRENTEU&limit=1&sort_order=desc&file_type=json&api_key=DEMO_KEY"
        # 金十数据有CBOT大豆
        url2 = "https://cdn.jin10.com/data_center/reports/cbot_ag.json"
        r = requests.get(url2, timeout=10)
        data = r.json()
        values = data.get("values", {})
        soybean = values.get("CBOT大豆", [None, None])
        if soybean and soybean[0]:
            cbot_price = float(soybean[0])  # 美分/蒲式耳
            # 转换为美元/吨：1蒲式耳大豆=60磅=0.0272155吨
            # 1美分/蒲式耳 = 1/60美分/磅，美元/吨 = 美分/蒲式耳 / 0.0272155 / 100
            usd_per_ton = cbot_price / 0.0272155 / 100
            cny_price = usd_per_ton * FX_RATE
            print(f"[L2] CBOT大豆: {cbot_price}美分/蒲式耳 -> {cny_price:.2f}元/吨")
            return cny_price
    except Exception as e:
        print(f"[L2] CBOT大豆获取失败: {e}")
    return None


def fetch_cn_basis():
    """L3: 大豆CNF升贴水（美元/吨）"""
    try:
        # 巴西大豆CNF：通常在120-180美分/蒲式耳
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPTA_WEB_HS_HQ_HSP",
            "columns": "ALL",
            "filter": '(hq_typecode=" soybeans")',
            "sortColumns": "dim_date",
            "sortTypes": "-1",
            "pageSize": "5",
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, params=params, headers=headers, timeout=15)
        data = r.json()
        rows = data.get("result", {}).get("data", [])
        if rows:
            basis = float(rows[0].get("premium", 0))
            print(f"[L3] 大豆升贴水: {basis}美分/蒲式耳")
            return basis
    except Exception as e:
        print(f"[L3] 升贴水失败: {e}")
    return None


def fetch_dce_prices():
    """L1: 获取DCE豆粕(M)、豆油(Y)、大豆(A)期货价格"""
    prices = {}
    try:
        # 豆粕M0
        df_m = ak.futures_main_sina(symbol="M0")
        if df_m is not None and len(df_m) > 0:
            col_map = {str(c).strip(): c for c in df_m.columns}
            close_col = col_map.get('收盘价', None) or col_map.get('最新价', None)
            if close_col:
                prices['M'] = float(df_m.iloc[-1][close_col])
    except Exception as e:
        print(f"[L1] 豆粕M0失败: {e}")
    try:
        # 豆油Y0
        df_y = ak.futures_main_sina(symbol="Y0")
        if df_y is not None and len(df_y) > 0:
            col_map = {str(c).strip(): c for c in df_y.columns}
            close_col = col_map.get('收盘价', None) or col_map.get('最新价', None)
            if close_col:
                prices['Y'] = float(df_y.iloc[-1][close_col])
    except Exception as e:
        print(f"[L1] 豆油Y0失败: {e}")
    try:
        # 大豆A0
        df_a = ak.futures_main_sina(symbol="A0")
        if df_a is not None and len(df_a) > 0:
            col_map = {str(c).strip(): c for c in df_a.columns}
            close_col = col_map.get('收盘价', None) or col_map.get('最新价', None)
            if close_col:
                prices['A'] = float(df_a.iloc[-1][close_col])
    except Exception as e:
        print(f"[L1] 大豆A0失败: {e}")
    return prices


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    # L1: DCE期货价格派生
    prices = fetch_dce_prices()
    if len(prices) >= 2:
        meal_price = prices.get('M', 0)
        oil_price = prices.get('Y', 0)
        soy_price = prices.get('A', prices.get('M', 3500) * 0.35)  #  fallback用豆粕估算

        # 压榨利润 = 豆粕×0.785 + 豆油×0.185 - 大豆价格 - 100
        profit = meal_price * YIELD_SOYMEAL + oil_price * YIELD_SOYOIL - soy_price - PROCESSING_FEE
        print(f"[L1] 压榨利润: {meal_price}×{YIELD_SOYMEAL} + {oil_price}×{YIELD_SOYOIL} - {soy_price} - {PROCESSING_FEE} = {profit:.2f}")
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, profit,
                    source_confidence=1.0, source="L1-DCE期货派生")
        return

    # L2: CBOT大豆 + 汇率
    cbot_price = fetch_cbot_soybean()
    if cbot_price:
        basis = fetch_cn_basis() or 140  # 默认140美分/蒲式耳
        # 美分/蒲式耳 转 美元/吨
        usd_per_ton = cbot_price / 0.0272155 / 100 + basis / 0.0272155 / 100
        cny_soy = usd_per_ton * FX_RATE
        meal_price = prices.get('M', 3500) if prices else 3500
        oil_price = prices.get('Y', 8000) if prices else 8000
        profit = meal_price * YIELD_SOYMEAL + oil_price * YIELD_SOYOIL - cny_soy - PROCESSING_FEE
        print(f"[L2] CBOT压榨利润: {profit:.2f}")
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, profit,
                    source_confidence=0.8, source=f"L2-CBOT×{FX_RATE}")
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
