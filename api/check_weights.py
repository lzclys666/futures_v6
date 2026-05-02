import re

with open(r'C:\Users\Administrator\.qclaw\workspace-agent-63961edb\scripts\macro_scoring_engine.py', encoding='utf-8') as f:
    content = f.read()

symbols = ['RU', 'CU', 'AU', 'AG']
for sym in symbols:
    pattern = f'"{sym}": \\[(.*?)\\]'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        section = match.group(0)
        # Find factor_code and weight pairs
        factors = re.findall(r'"factor_code":\s*"([^"]+)".*?"weight":\s*(\d+\.\d+)', section, re.DOTALL)
        print(f'\n{sym}:')
        total = 0
        for fc, w in factors:
            total += float(w)
            print(f'  {fc}: {w}')
        print(f'  TOTAL: {total:.2f}')
