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
    'SA_计算SA_FG比价.py',
]

for name in scripts:
    path = os.path.join(base, name)
    if not os.path.exists(path):
        print(f'SKIP: {name} not found')
        continue

    with open(path, encoding='utf-8') as f:
        content = f.read()

    # 检查是否使用 get_latest_value（需要修改）
    uses_l4 = 'get_latest_value' in content

    # 检查 AKShare DataFrame 空值处理
    ak_call = re.search(r'ak\.futures_spot_price\([^)]+\)', content)
    has_empty_check = 'empty' in content or 'len(df)' in content or 'df.empty' in content

    # 打印分析
    print(f'{name}:')
    print(f'  使用L4: {uses_l4}')
    print(f'  AKShare: {ak_call.group() if ak_call else "无"}')
    print(f'  空值检查: {has_empty_check}')
    print()
