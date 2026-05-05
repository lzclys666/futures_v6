#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JM_抓取焦煤进口量.py
因子: JM_IMPORT = 焦煤月度进口量

公式: JM_IMPORT = 焦煤进口量（万吨/月）

当前状态: [⚠️待修复]
- L1: 海关总署官网 — 需JS渲染，当前仅获取页面链接
- L2: 国家统计局 — 需JS渲染，暂不可用
- L3: 付费订阅: Mysteel（年费）
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符

数据说明:
- 月度进口量数据，obs_date为上月最后一天
- 海关总署数据通常在PDF或二级页面中，需进一步解析
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
from web_utils import fetch_url
import re
import datetime

SYMBOL = "JM"
FACTOR_CODE = "JM_IMPORT"
BOUNDS = (-100000, 100000)


def fetch_from_customs_gov():
    """L1: 海关总署官网爬取"""
    try:
        print("[L1] 海关总署...")
        url = "http://www.customs.gov.cn/customs/302249/zfxxgk/2799825/302274/302275/index.html"
        html, err = fetch_url(url, timeout=15)
        if not err and len(html) > 500:
            print(f"[L1] 页面获取成功({len(html)}字符)，解析中...")
            links = re.findall(r'href=["\']([^"\']*)["\']', html)
            print(f"[L1] 发现{len(links)}个链接")
            # 海关数据通常在PDF或二级页面中，需进一步解析
    except Exception as e:
        print(f"[L1] 失败: {e}")
    return None


def fetch_from_stats():
    """L2: 国家统计局"""
    try:
        print("[L2] 国家统计局...")
        # data.stats.gov.cn 需JS渲染，暂不可用
    except Exception as e:
        print(f"[L2] 失败: {e}")
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    # 月度进口量数据，obs_date为上月最后一天
    today = datetime.date.today()
    if today.month == 1:
        obs_date = datetime.date(today.year - 1, 12, 31)
    else:
        obs_date = today.replace(day=1) - datetime.timedelta(days=1)

    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1: 海关总署
    value = fetch_from_customs_gov()

    # L2: 国家统计局
    if value is None:
        value = fetch_from_stats()

    if value is not None:
        if not (BOUNDS[0] <= value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={value} out of {BOUNDS}")
            return
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value,
                   source_confidence=0.8, source='海关总署')
        print(f"[OK] {FACTOR_CODE}={value} obs={obs_date}")
        return

    # L3: 付费订阅（Mysteel年费）
    print(f"[跳过] {FACTOR_CODE} 海关总署网页待解析，手动录入: 海关总署>统计数据>商品贸易")

    # L4: DB历史最新值回补
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

    # L5: 不写NULL占位符（SOP§7）


if __name__ == "__main__":
    main()
