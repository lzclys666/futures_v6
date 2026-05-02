#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""精确修复SA脚本的L4 fallback: 保持原obs_date，不覆盖今日记录"""
import os

L4_OLD = """        from common.db_utils import get_latest_value
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
            print(f"[OK] {FACTOR_CODE}={v} L4回补成功")
        else:
            print(f"[WARN] {FACTOR_CODE} 无历史值")

"""

L4_NEW = """        # L4: 保留原始obs_date，不以today obs_date覆盖已有数据
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if ok:
            print(f"[OK] {FACTOR_CODE} L4回补成功(保留原obs_date)")
        else:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值，跳过L4")

"""

# 也要添加 save_l4_fallback 到 import
IMPORT_OLD = "from common.db_utils import ensure_table, save_to_db, get_pit_dates"
IMPORT_NEW = "from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback"

# 有问题的 AKShare 调用（返回DataFrame但没检查empty）
AK_OLD = """    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])
    if df is not None and len(df) > 0:"""

AK_NEW = """    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])
    if df is None or df.empty:"""

scripts = [
    r'D:\futures_v6\macro_engine\crawlers\SA\SA_抓取现货价.py',
    r'D:\futures_v6\macro_engine\crawlers\SA\SA_抓取期货日行情.py',
    r'D:\futures_v6\macro_engine\crawlers\SA\SA_抓取近月合约价.py',
    r'D:\futures_v6\macro_engine\crawlers\SA\SA_抓取次月合约价.py',
    r'D:\futures_v6\macro_engine\crawlers\SA\SA_抓取持仓排名.py',
    r'D:\futures_v6\macro_engine\crawlers\SA\SA_抓取纯碱库存_em.py',
    r'D:\futures_v6\macro_engine\crawlers\SA\SA_抓取仓单.py',
    r'D:\futures_v6\macro_engine\crawlers\SA\SA_抓取厂家库存.py',
    r'D:\futures_v6\macro_engine\crawlers\SA\SA_抓取行业开工率.py',
    r'D:\futures_v6\macro_engine\crawlers\SA\SA_抓取产量.py',
]

fixed = 0
for path in scripts:
    if not os.path.exists(path):
        print(f'SKIP (not found): {os.path.basename(path)}')
        continue

    with open(path, encoding='utf-8') as f:
        content = f.read()

    orig = content

    # 1. 添加 save_l4_fallback 到 import
    if 'save_l4_fallback' not in content:
        content = content.replace(IMPORT_OLD, IMPORT_NEW)

    # 2. 修复 AKShare DataFrame 空值检查（如果缺少的话）
    # 某些脚本用 `if df is not None and len(df) > 0:` 改为 `if df is None or df.empty:`
    content = content.replace(
        '    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is not None and len(df) > 0:',
        '    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])\n    if df is None or df.empty:'
    )

    # 3. 替换 L4 fallback 块
    content = content.replace(L4_OLD, L4_NEW)

    if content != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'FIXED: {os.path.basename(path)}')
        fixed += 1
    else:
        # 可能脚本结构不同，打印实际L4块用于调试
        if 'get_latest_value' in content:
            idx = content.find('get_latest_value')
            snippet = content[max(0,idx-100):idx+300]
            print(f'PARTIAL/CHECK: {os.path.basename(path)}')
            print(f'  L4 snippet: {repr(snippet[:200])}')
        else:
            print(f'NO CHANGE (no L4): {os.path.basename(path)}')

print(f'\nFixed {fixed}/{len(scripts)} scripts')
