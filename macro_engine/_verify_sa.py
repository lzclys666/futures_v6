#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

scripts = [
    'SA_抓取现货价.py','SA_抓取期货日行情.py','SA_抓取近月合约价.py',
    'SA_抓取次月合约价.py','SA_抓取持仓排名.py','SA_抓取纯碱库存_em.py',
    'SA_抓取仓单.py','SA_抓取厂家库存.py','SA_抓取行业开工率.py',
    'SA_抓取产量.py','SA_计算SA_FG比价.py'
]

for name in scripts:
    path = f'D:/futures_v6/macro_engine/crawlers/SA/{name}'
    with open(path, encoding='utf-8') as f:
        content = f.read()
    has_s4 = 'save_l4_fallback(' in content
    # get_latest_value might still be in imports (OK) or in code (BAD)
    import_end = content.find('from common.db_utils import')
    remaining = content[import_end+50:] if import_end >= 0 else content
    has_bad_l4 = 'get_latest_value(' in remaining
    status = 'OK' if has_s4 and not has_bad_l4 else 'BAD'
    print(f'{status}: {name}')
