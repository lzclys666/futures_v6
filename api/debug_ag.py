with open(r'C:\Users\Administrator\.qclaw\workspace-agent-63961edb\scripts\macro_history_backfill.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'ag_au_ag_ratio' in line:
        prev_line = lines[i-1] if i > 0 else ''
        has_return = 'return' in prev_line
        has_brace = '}' in line
        print(f'Line {i+1}: return_in_prev={has_return}, brace_in_curr={has_brace}')
        print(f'  Prev ({i}): {repr(prev_line[:80])}')
        print(f'  Curr ({i+1}): {repr(line[:80])}')
