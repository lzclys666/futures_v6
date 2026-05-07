#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Y_豆油期货净持仓.py
因子: Y_POS_NET = 大商所豆油前20净持仓（手）

公式: 多头持仓 - 空头持仓（前20名合计）

当前状态: [⛔永久跳过]
- L1: AKShare futures_dce_position_rank — DCE网站412反爬，BadZipFile
- L2: AKShare get_dce_rank_table — 同样被DCE反爬阻断
- 不写占位符，不做L4回补

备注: DCE（大连商品交易所）网站对爬虫实施412反爬策略（JS挑战+WAF），
内网无法部署浏览器环境（无Chrome/Edge/Chromium），无法绕过。
此问题影响所有DCE品种（LH/PP/EG/J/M/Y等），非脚本问题。
2026-05-06 PM决定：跳过DCE净持仓，按P2标准推进。
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "Y_POS_NET"
SYM = "Y"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: DCE网站412反爬，内网无法部署浏览器环境而暂不获取")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
