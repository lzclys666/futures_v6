#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_DXY美元指数.py
因子: AU_DXY = DXY美元指数（美联储贸易加权广义美元指数）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1a: 新浪财经 hf_DXY | L1b: 金十数据 | L1c: 东方财富
- L2: FRED DTWEXBGS（美联储贸易加权广义美元指数 Broad Dollar Index）
- L3: save_l4_fallback() 兜底
- bounds: [90, 130]（美元指数历史区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
from common.web_utils import fetch_url, fetch_json
from datetime import datetime

FACTOR_CODE = "AU_DXY"
SYMBOL = "AU"
BOUNDS = (90, 130)


def fetch():
    """L1: 多源获取DXY美元指数"""
    # L1a: 新浪财经 DXY
    try:
        html, err = fetch_url(
            'https://hq.sinajs.cn/list=hf_DXY',
            headers={'Referer': 'https://finance.sina.com.cn'},
            timeout=10
        )
        if err:
            raise Exception(err)
        m = re.search(r'"([^"]+)"', html)
        if m:
            parts = m.group(1).split(',')
            if len(parts) >= 1:
                val = float(parts[0])
                if BOUNDS[0] <= val <= BOUNDS[1]:
                    print(f"[L1a] DXY={val} (Sina Finance)")
                    return val, 1.0, "sina_hq_hf_DXY"
    except Exception as e:
        print(f"[L1a] {e}")

    # L1b: 金十数据 flash API
    try:
        data, err = fetch_json(
            'https://flash-api.jin10.com/get_flash_chart_data?max_time=9999999999',
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'X-App-Id': 'jinseof'},
            timeout=10
        )
        if err:
            raise Exception(err)
        for item in data.get('data', []):
            if 'DXY' in str(item) or 'dxy' in str(item):
                m = re.search(r'DXY[^0-9]*([0-9]+\.?[0-9]*)', str(item))
                if m:
                    val = float(m.group(1))
                    if BOUNDS[0] <= val <= BOUNDS[1]:
                        print(f"[L1b] DXY={val} (Jin10)")
                        return val, 1.0, "jin10_flash_api"
    except Exception as e:
        print(f"[L1b] {e}")

    # L1c: 东方财富 DXY CFD
    try:
        data, err = fetch_json(
            'https://push2.eastmoney.com/api/qt/stock/get?secid=106.CFDDXY&fields=f43,f57,f58,f169,f170,f47,f48&ut=fa5fd1943c7b386f172d6893dbfba10b',
            headers={'Referer': 'https://quote.eastmoney.com/'},
            timeout=10
        )
        if err:
            raise Exception(err)
        val = data.get('data', {}).get('f43')
        if val and BOUNDS[0] <= val/100 <= BOUNDS[1]:
            val = val / 100
            print(f"[L1c] DXY={val} (Eastmoney)")
            return val, 1.0, "eastmoney_cfd_dxy"
    except Exception as e:
        print(f"[L1c] {e}")

    return None, None, None


def fetch_l2():
    """L2: FRED DTWEXBGS (美联储贸易加权广义美元指数 Broad Dollar Index)"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS&vintage_date={today}'
        r_text, err = fetch_url(url, timeout=15)
        if err:
            return None, None, None
        lines = r_text.strip().split('\n')
        for line in reversed(lines[1:]):
            parts = line.split(',')
            if len(parts) == 2 and parts[1].strip() != '.':
                val = float(parts[1].strip())
                obs_date = parts[0].strip()
                if BOUNDS[0] <= val <= BOUNDS[1]:
                    print(f"[L2] DTWEXBGS={val} obs={obs_date} (FRED)")
                    return val, 0.9, "FRED_DTWEXBGS"
    except Exception as e:
        print(f"[L2] FRED DTWEXBGS 失败: {e}")
    return None, None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return

    raw_value, conf, src = None, None, None

    # L1
    try:
        raw_value, conf, src = fetch()
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2
    if raw_value is None:
        try:
            raw_value, conf, src = fetch_l2()
        except Exception as e:
            print(f"[L2] 失败: {e}")

    # L3
    if raw_value is None:
        if not save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                                 extra_msg="(DXY美元指数)"):
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
            print(f"[ERR] {FACTOR_CODE} 无数据")
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
               source_confidence=conf, source=src)
    print(f"[OK] {FACTOR_CODE}={raw_value} 写入成功")


if __name__ == "__main__":
    main()
