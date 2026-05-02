#!/usr/bin/env python3
content = open(r'D:\futures_v6\macro_engine\research\W4_single_factor_backtest.py', 'r', encoding='utf-8').read()
# Fix the problematic f-string patterns with nested quotes
content = content.replace("f'\n{'━'*60}'", "'\\n' + '━'*60")
content = content.replace("f'{'━'*60}'", "'━'*60")
open(r'D:\futures_v6\macro_engine\research\W4_single_factor_backtest.py', 'w', encoding='utf-8').write(content)
print('done')
