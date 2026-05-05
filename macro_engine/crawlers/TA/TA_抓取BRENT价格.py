#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取BRENT价格
因子: TA_CST_BRENT = 抓取BRENT价格

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
from common.web_utils import fetch_url, fetch_json
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback
import pandas as pd
from datetime import datetime

FACTOR_CODE = "TA_CST_BRENT"
SYMBOL = "TA"
MIN_VALUE = 55.0   # BRENT合理区间下限（OPEC+调控下限）
MAX_VALUE = 120.0  # BRENT合理区间上限（2024年后高价时代）


def fetch_fred_brent(obs_date):
    """L1: FRED Brent Crude (MCOILBRENTEU) 月度数据"""
    try:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id=MCOILBRENTEU&vintage_date={obs_date.strftime('%Y-%m-%d')}"
        html, err = fetch_url(url, timeout=10)
        if err:
            return None
        lines = html.strip().split('\n')
        rows = []
        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) == 2 and parts[1].strip():
                try:
                    d = pd.to_datetime(parts[0].strip())
                    v = float(parts[1].strip())
                    rows.append((d, v))
                except (ValueError, IndexError):
                    continue
        if not rows:
            return None
        rows.sort(key=lambda x: x[0])
        for d, v in reversed(rows):
            if d <= pd.Timestamp(obs_date):
                age = (pd.Timestamp(obs_date) - d).days
                print(f"[L1] FRED Brent: {d.strftime('%Y-%m-%d')} = ${v:.2f} (滞后{age}天)")
                if MIN_VALUE <= v <= MAX_VALUE:
                    return v, 0.85, f"FRED_MCOILBRENTEU({d.strftime('%Y-%m-%d')})"
                else:
                    print(f"  [WARN] FRED ${v:.2f} 超出合理范围[{MIN_VALUE},{MAX_VALUE}]，跳过")
                    return None
        return None
    except Exception as e:
        print(f"[L1] FRED失败: {e}")
        return None


def fetch_eia_brent():
    """L2: EIA Brent (demo_key免注册)"""
    try:
        url = (
            "https://api.eia.gov/v2/petroleum/pri/spt/data/"
            "?api_key=DEMO_KEY"
            "&frequency=daily"
            "&data[0]=value"
            "&facets[product][]=EPCBRENT"
            "&sort[0][column]=period&sort[0][direction]=desc"
            "&length=3"
        )
        data, err = fetch_json(url, timeout=10)
        if err:
            return None
        if 'response' in data and 'data' in data['response']:
            for item in data['response']['data'][:1]:
                v = float(item['value'])
                period = item['period']
                print(f"[L2] EIA Brent: {period} = ${v:.2f}")
                if MIN_VALUE <= v <= MAX_VALUE:
                    return v, 0.8, f"EIA_EPCBRENT({period})"
                else:
                    print(f"  [WARN] EIA ${v:.2f} 超出合理范围[{MIN_VALUE},{MAX_VALUE}]，跳过")
        return None
    except Exception as e:
        print(f"[L2] EIA失败: {e}")
        return None


def fetch_yahoo_brent():
    """L3: Yahoo Finance Brent Crude Futures (BZ=F)"""
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/BZ=F"
        params = {"interval": "1d", "range": "5d", "includePrePost": "false"}
        data, err = fetch_json(url, params=params, timeout=10)
        if err:
            return None
        result = data.get("chart", {}).get("result", [])
        if result:
            quotes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
            if quotes and quotes[-1] is not None:
                v = float(quotes[-1])
                print(f"[L3] Yahoo Brent Futures: BZ=F = ${v:.2f}")
                if MIN_VALUE <= v <= MAX_VALUE:
                    return v, 0.9, "YahooFinance_BZ=F"
        return None
    except Exception as e:
        print(f"[L3] Yahoo失败: {e}")
        return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} (Brent原油) === obs={obs_date}")

    result = None

    # L1: FRED (月度，滞后约30天)
    r1 = fetch_fred_brent(obs_date)
    if r1:
        result = r1

    # L2: EIA (每日，可能有几天延迟)
    if not result:
        r2 = fetch_eia_brent()
        if r2:
            result = r2

    # L3: Yahoo Finance BZ=F (近日期货)
    if not result:
        r3 = fetch_yahoo_brent()
        if r3:
            result = r3

    # L4: 历史回补（BRENT无免费可靠源，依赖L4维持连续性）
    if not result:
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

    if result:
        val, conf, src = result
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source_confidence=conf, source=src)
        print(f"[OK] {FACTOR_CODE}=${val:.2f} 写入成功")
        return 0
    else:
        print("[WARN] BRENT全数据源失败，跳过")
        return 0  # 不退出失败，避免run_all中断


if __name__ == "__main__":
    sys.exit(main())
