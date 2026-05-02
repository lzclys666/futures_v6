#!/usr/bin/env python3
filepath = r'D:\futures_v6\macro_engine\research\W4_single_factor_backtest.py'
content = open(filepath, 'r', encoding='utf-8').read()

# The issue: f-strings with single-quoted string inside braces
# e.g. f'{"-"*60}' or f'\n{"="*60}'
# We need to change the outer quotes to double quotes

import re

# Find all f-strings that look like f'...{'X'*N}...' where outer is single-quoted
# Replace f' with f" and ...{'X'*N}... remains (X can be any char)

def fix_outer_quotes(m):
    full = m.group(0)
    prefix = m.group(1)
    rest = m.group(2)
    # Change outer single to double
    return 'f"' + prefix + rest

# Pattern: f' followed by content containing {'...'} followed by '
# This regex finds f-strings with nested braces containing single-quoted content
# Replace f' with f"
count = 0
new_lines = []
for line in content.split('\n'):
    if "f'" in line and ("f'{" in line) and ("}'" in line):
        # Simple approach: if line has f'{...}...' pattern, fix outer quotes
        # Find f' at start and matching ' at end
        # Replace the first f' with f" and the last ' with "
        # But this is tricky... Let's just do targeted fixes
        if "{'-'" in line or '{"-"' in line or "{'='*" in line or '{"="' in line:
            # These are the problematic ones - nested single quotes in f-string
            # Replace outer single with double
            line = line.replace("f'", 'f"', 1)
            # Find the last single quote that closes the f-string
            # by counting braces
            depth = 0
            start_fix = False
            new_line = []
            for ch in line:
                if ch == '{':
                    depth += 1
                    start_fix = True
                elif ch == '}':
                    depth -= 1
                if start_fix and ch == "'" and depth == 0:
                    new_line.append('"')
                else:
                    new_line.append(ch)
            line = ''.join(new_line)
            count += 1
    new_lines.append(line)

print(f'Fixed {count} lines')
new_content = '\n'.join(new_lines)
open(filepath, 'w', encoding='utf-8').write(new_content)
print('Done')
