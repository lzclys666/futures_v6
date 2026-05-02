#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""精确替换所有SA脚本的L4块，保持原始obs_date"""
import os

# 每个脚本的 (old_block, new_block) 对
REPLACEMENTS = {
    'SA_抓取近月合约价.py': (
        """    else:
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
            print(f"[OK] {FACTOR_CODE}={v} L4回补成功")
        else:
            print(f"[WARN] {FACTOR_CODE} 无数据源")""",
        """    else:
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if not ok:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")"""
    ),
    'SA_抓取次月合约价.py': (
        """    else:
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
            print(f"[OK] {FACTOR_CODE}={v} L4回补成功")
        else:
            print(f"[WARN] {FACTOR_CODE} 无数据源")""",
        """    else:
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if not ok:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")"""
    ),
    'SA_抓取持仓排名.py': (
        """        v = get_latest_value(fc, SYMBOL)
        if v is not None:
            save_to_db(fc, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
            print(f"[OK] {fc}={v} L4回补成功")""",
        """        ok = save_l4_fallback(fc, SYMBOL, pub_date, obs_date)
        if ok:
            print(f"[OK] {fc} L4回补成功")"""
    ),
    'SA_抓取纯碱库存_em.py': (
        """    else:
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
            print(f"✅ {FACTOR_CODE}={v} L4回补成功")
        else:
            print(f"⚠️  {FACTOR_CODE} 无数据源")""",
        """    else:
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if ok:
            print(f"[OK] {FACTOR_CODE} L4回补成功")
        else:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")"""
    ),
    'SA_抓取仓单.py': (
        """        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
            print(f"✅ {FACTOR_CODE}={v} L4回补成功")
        else:
            print(f"⚠️  {FACTOR_CODE} 无数据源")""",
        """        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if ok:
            print(f"[OK] {FACTOR_CODE} L4回补成功")
        else:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")"""
    ),
    'SA_抓取厂家库存.py': (
        """    val = fetch()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source="db_回补")
        print(f"✅ {FACTOR_CODE}={val} L4回补成功")
    else:
        print(f"⚠️  {FACTOR_CODE} 无历史数据，请手动录入")""",
        """    val = fetch()
    if val is not None:
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if ok:
            print(f"[OK] {FACTOR_CODE} L4回补成功")
        else:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")"""
    ),
    'SA_抓取行业开工率.py': (
        """    val = fetch()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source="db_回补")
        print(f"✅ {FACTOR_CODE}={val} L4回补成功")
    else:
        print(f"⚠️  {FACTOR_CODE} 无历史数据，请手动录入")""",
        """    val = fetch()
    if val is not None:
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if ok:
            print(f"[OK] {FACTOR_CODE} L4回补成功")
        else:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")"""
    ),
    'SA_抓取产量.py': (
        """    val = fetch()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source="db_回补")
        print(f"✅ {FACTOR_CODE}={val} L4回补成功")
    else:
        print(f"⚠️  {FACTOR_CODE} 无历史数据，请手动录入")""",
        """    val = fetch()
    if val is not None:
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if ok:
            print(f"[OK] {FACTOR_CODE} L4回补成功")
        else:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")"""
    ),
}

base = r'D:\futures_v6\macro_engine\crawlers\SA'
fixed = 0
for name, (old, new) in REPLACEMENTS.items():
    path = os.path.join(base, name)
    with open(path, encoding='utf-8') as f:
        content = f.read()
    
    if old not in content:
        print(f'MISMATCH: {name}')
        # 打印实际内容用于调试
        idx = content.find('get_latest_value')
        if idx >= 0:
            print(f'  actual @ {idx}: {repr(content[max(0,idx-100):idx+300])}')
        continue
    
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'FIXED: {name}')
    fixed += 1

print(f'\nFixed {fixed}/{len(REPLACEMENTS)}')
