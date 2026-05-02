"""Clean fix for macro_history_backfill.py AG section."""
SCRIPT = r'C:\Users\Administrator\.qclaw\workspace-agent-63961edb\scripts\macro_history_backfill.py'

with open(SCRIPT, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Fix 1: Remove line 909 (idx 908) - the first broken 'return {'
# The computation code starts at line 910 (idx 909) and goes to line 936 (idx 935)
# Line 937 (idx 936) has the second 'return {' which is correct

# Fix 2: Fix corrupted lines 950-953 (idx 949-952)
# These should be:
#   Line 950: '    # 返回空字典\n'
#   Line 951: '    return {}\n'

new_lines = []
skip_first_return = False
for i, line in enumerate(lines):
    idx = i + 1  # 1-indexed
    
    # Fix 1: Skip line 909 (first 'return {' before computation code)
    if idx == 909:
        skip_first_return = True
        continue
    
    # Fix 2: Replace corrupted lines 950-953
    if idx == 950:
        new_lines.append('    # 返回空字典\n')
        continue
    if idx == 951:
        new_lines.append('\n')
        continue
    if idx == 952:
        # Skip this corrupted line - it's part of the comment that got split
        continue
    if idx == 953:
        new_lines.append('    return {}\n')
        continue
    
    new_lines.append(line)

new_content = ''.join(new_lines)
print(f"New lines: {len(new_lines)}")

# Verify
import ast
try:
    ast.parse(new_content)
    print("SYNTAX OK!")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    lines2 = new_content.split('\n')
    for j in range(max(0, e.lineno-3), min(len(lines2), e.lineno+5)):
        print(f"  {j+1}: {repr(lines2[j][:100])}")
    raise SystemExit(1)

with open(SCRIPT, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Written {len(new_content)} chars")
print("DONE!")
