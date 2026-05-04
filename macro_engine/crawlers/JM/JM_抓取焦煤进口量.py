#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取焦煤进口量
因子: JM_IMPORT = 焦煤月度进口量

公式: 数据采集（无独立计算公式）

当前状态: [WARN] 待修复
- obs_date 逻辑已修正（改为上月最后一天）
- 添加 bounds 检查 [-100000, 100000]
- Header 待完善

订阅优先级: [付费]（L1-L3 均为付费源）
替代付费源: Mysteel / 中国海关总署
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value, DB_PATH
import sqlite3
from common.web_utils import fetch_url
import re
import datetime

FACTOR_CODE = "JM_IMPORT"
SYMBOL = "JM"
# 付费来源: 海关总署数据 / Mysteel(年费)

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
            # 海关数据通常在PDF或二级页面中
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
    today = datetime.date.today()
    pub_date = today
    # 月度进口量数据，obs_date 为上月最后一天
    if today.month == 1:
        obs_date = datetime.date(today.year - 1, 12, 31)
    else:
        obs_date = today.replace(day=1) - datetime.timedelta(days=1)
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    value = fetch_from_customs_gov()
    if value is None:
        value = fetch_from_stats()
    
    if value is not None:
        # Bounds 检查
        expected_lo, expected_hi = -100000.0, 100000.0
        if not (expected_lo <= value <= expected_hi):
            print(f"[WARN] {FACTOR_CODE}={value} 超出bounds[{expected_lo}, {expected_hi}]，跳过")
            return
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=0.8, source='海关总署')
    else:
        # L4: DB兜底
        print("[L4] DB历史回补...")
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source='db_回补')
        else:
            print("[失败] 无免费API可用，海关总署网页待解析。手动录入: 海关总署官网>统计数据>商品贸易")

if __name__ == "__main__":
    main()
