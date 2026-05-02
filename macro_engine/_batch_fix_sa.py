#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量修复 SA 脚本的 L4 fallback 逻辑"""
import os, re

base = r'D:\futures_v6\macro_engine\crawlers\SA'
scripts = [
    'SA_抓取现货价.py',
    'SA_抓取期货日行情.py',
    'SA_抓取近月合约价.py',
    'SA_抓取次月合约价.py',
    'SA_抓取持仓排名.py',
    'SA_抓取纯碱库存_em.py',
    'SA_抓取仓单.py',
    'SA_抓取厂家库存.py',
    'SA_抓取行业开工率.py',
    'SA_抓取产量.py',
]

# 旧 L4 模式（多种写法）
OLD_L4_PATTERNS = [
    # 模式1: get_latest_value + save_to_db with db_回补
    re.compile(
        r'        v = get_latest_value\([^)]+\)\n'
        r'        if v is not None:\n'
        r'            save_to_db\([^)]+source="db_回补"[^)]+\)',
        re.DOTALL
    ),
    # 模式2: 简单版本
    re.compile(
        r'        v = get_latest_value\([^)]+\)\n'
        r'        if v is not None:\n'
        r'            save_to_db\([^)]+\)',
        re.DOTALL
    ),
]

NEW_L4 = '        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)'

# 需要添加空 DataFrame 检查的 AKShare 调用模式
AK_EMPTY_PATTERNS = [
    re.compile(r'(\s+)(df = ak\.futures_spot_price\([^)]+\))\s*\n(\s+)try:'),
    re.compile(r'(\s+)(df = ak\.futures_inventory_em\([^)]+\))\s*\n(\s+)try:'),
]

def add_empty_check(content):
    """为 DataFrame 调用添加 .empty 检查"""
    def replacer(m):
        indent, call, newline, try_indent = m.group(1), m.group(2), m.group(3), m.group(3)
        return f'{indent}{call}\n{indent}if df.empty:\n{indent}    raise ValueError("AKShare返回空DataFrame")\n{newline}try:'
    
    new_content = content
    for pattern in AK_EMPTY_PATTERNS:
        new_content = pattern.sub(replacer, new_content)
    return new_content

def fix_l4(content):
    """替换 L4 fallback 逻辑"""
    new_content = content
    for pattern in OLD_L4_PATTERNS:
        new_content = pattern.sub(NEW_L4, new_content)
    return new_content

def fix_import(content):
    """确保导入了 save_l4_fallback"""
    if 'save_l4_fallback' in content:
        return content
    # 找到 import 行，添加 save_l4_fallback
    old = 'from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value'
    new = 'from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value, save_l4_fallback'
    if old in content:
        content = content.replace(old, new)
    return content

def fix_script(name):
    path = os.path.join(base, name)
    with open(path, encoding='utf-8') as f:
        content = f.read()

    orig = content
    
    # 1. 添加空 DataFrame 检查
    content = add_empty_check(content)
    
    # 2. 修复 L4 fallback
    content = fix_l4(content)
    
    # 3. 添加 save_l4_fallback 导入
    content = fix_import(content)
    
    if content != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'FIXED: {name}')
    else:
        print(f'NO CHANGE: {name}')

for name in scripts:
    fix_script(name)

print('Done')
