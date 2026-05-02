#!/usr/bin/env python3
filepath = r'D:\futures_v6\macro_engine\research\W4_single_factor_backtest.py'
content = open(filepath, 'r', encoding='utf-8').read()

lines = content.split('\n')
for i, line in enumerate(lines, 1):
    # Find f-strings with single-quoted content inside braces
    if "f'" in line and "{'" in line and ("*60}" in line or "*60}'" in line):
        print(f'Line {i}: {repr(line)}')
