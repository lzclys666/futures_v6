#!/usr/bin/env python3
import re

filepath = r'D:\futures_v6\macro_engine\research\W4_single_factor_backtest.py'
content = open(filepath, 'r', encoding='utf-8').read()

# Find all f-strings with nested single quotes like f'{'X'*N}'
# Replace with f'{"X"*N}' (use double quotes inside braces)
def fix_fstring(m):
    inner = m.group(1)
    rest = m.group(2)
    return f"f'{{\"{inner}\"{rest}}}'"

# Pattern: f'{'X'*N}' where X is a single char and N is a number
pattern = r"f'\{'([^'])'(\*\d+)\}'"
new_content, n = re.subn(pattern, fix_fstring, content)
print(f'Replaced {n} occurrences')

# Also fix cases without the *N suffix (simple char repetition)
pattern2 = r"f'\{'([^'])'(\*60)\}'"
new_content2, n2 = re.subn(pattern2, fix_fstring, new_content)
print(f'Replaced {n2} more occurrences')

open(filepath, 'w', encoding='utf-8').write(new_content2)
print('Done')
