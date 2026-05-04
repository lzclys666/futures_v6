#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TA_抓取汇率.py
因子: TA_CST_USDCNY = USDCNY汇率

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: [付费]（付费源才需要标注）
替代付费源: 具体平台名称
"""
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
from common.web_utils import fetch_url


def fetch_usd_cny_qq():
    """腾讯财经 USDCNY 汇率"""
    try:
        html, err = fetch_url(
            'https://qt.gtimg.cn/q=USDCNY,USDCNH',
            timeout=10
        )
        for line in html.strip().split('\n'):
            if 'USDCNY' in line and 'pv_none' not in line:
                parts = line.split('"')[1].split(',')
                if len(parts) > 1:
                    return float(parts[1])
    except Exception as e:
        print(f"  [L2] 腾讯汇率失败: {e}")
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === TA_USDCNY汇率 === obs={obs_date}")

    # L2: 腾讯
    rate = fetch_usd_cny_qq()
    src = "腾讯财经"

    if rate:
        print(f"  {src} USDCNY: {rate}")
        save_to_db("TA_CST_USDCNY", "TA", pub_date, obs_date, rate, source=src, source_confidence=0.9)
        print(f">>> TA_CST_USDCNY={rate} 写入成功")
    else:
        print("  [L1/L2] 无免费汇率数据")
        val = get_latest_value("TA_CST_USDCNY", "TA")
        if val is not None:
            save_to_db("TA_CST_USDCNY", "TA", pub_date, obs_date, val, source_confidence=0.5, source="db_回补")
            print(f">>> TA_CST_USDCNY={val} L4回补成功")
        else:
            print("FAIL: USDCNY无数据")

if __name__ == "__main__":
    main()
