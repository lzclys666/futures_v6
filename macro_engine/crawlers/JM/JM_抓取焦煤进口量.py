#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取焦煤进口量
因子: JM_IMPORT = 抓取焦煤进口量

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""

import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value, DB_PATH

import sqlite3
import requests
import re
import datetime

FACTOR_CODE = "JM_IMPORT"
SYMBOL = "JM"

def fetch_from_customs_gov():
    """L1: 海关总署官网爬取"""
    try:
        print("[L1] 海关总署...")
        url = "http://www.customs.gov.cn/customs/302249/zfxxgk/2799825/302274/302275/index.html"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        if resp.status_code == 200 and len(resp.text) > 500:
            print(f"[L1] 页面获取成功({len(resp.text)}字符)，解析中...")
            links = re.findall(r'href=["\']([^"\']*)["\']', resp.text)
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
    if today.month == 1:
        obs_date = datetime.date(today.year - 1, 12, 31)
    else:
        obs_date = datetime.date(today.year, today.month, 1) - datetime.timedelta(days=1)
    
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    
    value = fetch_from_customs_gov()
    if value is None:
        value = fetch_from_stats()
    
    if value is not None:
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
