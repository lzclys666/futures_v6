#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

L4_BLOCK_OLD = """        from common.db_utils import get_latest_value
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
            print(f"[OK] {FACTOR_CODE}={v} L4回补成功")
        else:
            print(f"⚠️  {FACTOR_CODE} 无数据源")"""

L4_BLOCK_NEW = """        # L4: 保留原始obs_date，不覆盖已有今日数据
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if ok:
            print(f"[OK] {FACTOR_CODE} L4回补成功")
        else:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")"""

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

IMPORT_ADD = "save_l4_fallback"

for path in scripts:
    name = os.path.basename(path)
    if not os.path.exists(path):
        print(f'SKIP: {name}')
        continue

    with open(path, encoding='utf-8') as f:
        content = f.read()

    orig = content

    # 添加 save_l4_fallback 到 import
    if IMPORT_ADD not in content:
        content = content.replace(
            'from common.db_utils import ensure_table, save_to_db, get_pit_dates',
            'from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback'
        )

    # 替换 L4 block
    if L4_BLOCK_OLD in content:
        content = content.replace(L4_BLOCK_OLD, L4_BLOCK_NEW)
        changed = True
    else:
        changed = False

    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'FIXED: {name}')
    else:
        if 'get_latest_value' in content:
            idx = content.find('get_latest_value')
            snippet = repr(content[max(0,idx-150):idx+350])
            print(f'MISMATCH: {name}')
            print(f'  snippet: {snippet[:300]}')
        else:
            print(f'NO L4: {name}')

print('Done')
