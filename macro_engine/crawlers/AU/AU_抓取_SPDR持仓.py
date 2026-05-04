#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_SPDR黄金ETF持仓量.py
因子: AU_SPD_GLD = SPDR黄金ETF持仓量（吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1a: 我的钢铁网 | L1b: 东方财富API | L1c: 新浪贵金属
- L2: 无备选源（SPDR持仓数据仅通过SPDR官网/第三方发布）
- L3: save_l4_fallback() 兜底
- bounds: [500, 2000]吨（SPDR持仓历史区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
from common.web_utils import fetch_url, fetch_json

FACTOR_CODE = "AU_SPD_GLD"
SYMBOL = "AU"
BOUNDS = (500, 2000)


def fetch_spdr():
    """L1: 多源获取SPDR黄金持仓（吨）"""

    # L1a: 我的钢铁网 SPDR黄金持仓
    try:
        html, err = fetch_url(
            'https://news.mysteel.com/a/26041709/',
            timeout=10
        )
        if err:
            raise Exception(err)
        text = html
        m = re.search(r'SPD[Rr].*?持仓量[为]?(\d+\.?\d*)\s*吨', text)
        if not m:
            m = re.search(r'持仓[为]?(\d+\.?\d{2})\s*吨', text[:3000])
        if m:
            val = float(m.group(1))
            if BOUNDS[0] <= val <= BOUNDS[1]:
                print(f"[L1a] SPDR GLD={val}吨 (Mysteel)")
                return val, 1.0, "mysteel_spdr_gld"
    except Exception as e:
        print(f"[L1a] {e}")

    # L1b: 东方财富 SPDR持仓数据API
    try:
        data, err = fetch_json(
            'https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_GOLD_ETF_HOLD&columns=ALL&pageNumber=1&pageSize=5',
            headers={'Referer': 'https://data.eastmoney.com/'},
            timeout=10
        )
        if err:
            raise Exception(err)
        for item in data.get('result', {}).get('data', []):
            if 'SPDR' in str(item) or 'GLD' in str(item):
                hold = item.get('F8') or item.get('hold')
                if hold and BOUNDS[0] <= float(hold) <= BOUNDS[1]:
                    val = float(hold)
                    print(f"[L1b] SPDR GLD={val}吨 (Eastmoney API)")
                    return val, 1.0, "eastmoney_gold_etf"
    except Exception as e:
        print(f"[L1b] {e}")

    # L1c: 新浪贵金属
    try:
        html, err = fetch_url(
            'https://hq.sinajs.cn/list=hf_GLD',
            headers={'Referer': 'https://finance.sina.com.cn'},
            timeout=10
        )
        if err:
            raise Exception(err)
        m = re.search(r'"([^"]+)"', html)
        if m:
            parts = m.group(1).split(',')
            for p in parts:
                try:
                    val = float(p)
                    if BOUNDS[0] <= val <= BOUNDS[1]:
                        print(f"[L1c] SPDR GLD={val} (Sina GLD)")
                        return val, 1.0, "sina_hq_hf_GLD"
                except (ValueError, IndexError):
                    pass
    except Exception as e:
        print(f"[L1c] {e}")

    # L2: 无备选源
    print("[L2] 无备选源（SPDR持仓数据来源有限）")
    return None, None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return

    val, conf, src = fetch_spdr()

    # L3
    if val is None:
        if not save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                                 extra_msg="(SPDR黄金ETF持仓量)"):
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
            print(f"[ERR] {FACTOR_CODE} 无数据")
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
               source_confidence=conf, source=src)
    print(f"[OK] {FACTOR_CODE}={val} 写入成功")


if __name__ == "__main__":
    main()
