"""
Patch macro_history_backfill.py - robust approach using actual file content.
"""
SCRIPT = r'C:\Users\Administrator\.qclaw\workspace-agent-63961edb\scripts\macro_history_backfill.py'

with open(SCRIPT, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# STEP A: Find exact lines around AG return block
# ============================================================
lines = content.split('\n')
print(f"File has {len(lines)} lines")

# Find the line with 'ag_au_ag_ratio",    ag_au_ag_ratio'
for i, line in enumerate(lines):
    if 'ag_au_ag_ratio' in line and 'return' in lines[i-1] and '}' in line:
        print(f"Found AG return dict at line {i+1}: {repr(line[:80])}")
        return_start = i - 7  # 'return {' is 8 lines before
        return_end = i + 1   # include the closing '}'
        print(f"Return block: lines {return_start+1} to {return_end+1}")
        print("Content:")
        for j in range(return_start, return_end+1):
            print(f"  {j+1}: {repr(lines[j])}")
        break

# ============================================================
# STEP B: Replace the AG return block with new code
# ============================================================
# Lines to insert BEFORE 'return {'
new_before_lines = [
    '',
    '        # 浠垮叡璁??涓?10澶╃殑鏃ユ湡鏌ヨ礋鍊?    gold_close = None',
    '        for delta in range(0, 10):',
    '            check = (datetime.strptime(d_iso, "%Y-%m-%d") - timedelta(days=delta)).strftime("%Y-%m-%d")',
    '            if check in _GOLD_FUTURES_CACHE:',
    '                gold_close = _GOLD_FUTURES_CACHE[check]',
    '                break',
    '        silver_close = None',
    '        for delta in range(0, 10):',
    '            check = (datetime.strptime(d_iso, "%Y-%m-%d") - timedelta(days=delta)).strftime("%Y-%m-%d")',
    '            if check in _SILVER_FUTURES_CACHE:',
    '                silver_close = _SILVER_FUTURES_CACHE[check]',
    '                break',
    '        cu_close = None',
    '        for delta in range(0, 10):',
    '            check = (datetime.strptime(d_iso, "%Y-%m-%d") - timedelta(days=delta)).strftime("%Y-%m-%d")',
    '            if check in _CU_FUTURES_CACHE:',
    '                cu_close = _CU_FUTURES_CACHE[check]',
    '                break',
    '',
    '        # 鏍规嵁鐪熷疄鏈哄惎鍜岄噾铔?璁′换涓轰互涓嬫牴鎹?    # ag0: CNY/kg, au0: CNY/g * 31.1035 = CNY/kg',
    '        ag_au_real_ratio = None',
    '        if gold_close is not None and silver_close is not None and gold_close > 0:',
    '            gold_kg = gold_close * 31.1035  # CNY/g -> CNY/kg',
    '            ag_au_real_ratio = silver_close / gold_kg',
    '',
]

# New return dict lines (replacing lines return_start to return_end)
new_return_lines = [
    '        return {',
    '            "lme_cu_inventory":   cu_inv,',
    '            "lme_cu_chg_rate":   cu_inv_chg_rate,',
    '            "china_pmi":          pmi_val,',
    '            "usdcny":             fx,',
    '            "industrial_ip":     ip_val,',
    '            "cb_gold_chg":       cb_gold,',
    '            "gold_futures_close": gold_close,',
    '            "silver_futures_close": silver_close,',
    '            "cu_futures_close":   cu_close,',
    '            "ag_au_real_ratio":  ag_au_real_ratio,',
    '        }',
]

# Build the replacement
new_lines = lines[:return_start] + new_before_lines + new_return_lines + lines[return_end+1:]
print(f"New file will have {len(new_lines)} lines")

# ============================================================
# STEP C: Update proxy handlers - find exact text first
# ============================================================
new_content = '\n'.join(new_lines)

# Find the lme_cu_inventory_inv proxy section
idx1 = new_content.find('elif proxy == "lme_cu_inventory_inv"')
idx2 = new_content.find('elif proxy == "ag_au_ag_ratio"', idx1)
print(f"lme_cu_inventory_inv proxy: idx {idx1} to {idx2}")

# Show the actual text
proxy_block = new_content[idx1:idx2]
print("Proxy block to replace:")
print(repr(proxy_block[:500]))

# Build new proxy block
new_proxy_block = '''    elif proxy == "lme_cu_inventory_inv":
        cu_price = raw_data.get("cu_futures_close")
        if cu_price is not None:
            return cu_price
        chg = raw_data.get("lme_cu_chg_rate")
        if chg is not None:
            return -chg
        v = raw_data.get("lme_cu_inventory")
        if v is None:
            return None
        return -(v / 100000.0)

    elif proxy == "ag_au_ag_ratio":
        v = raw_data.get("ag_au_real_ratio")
        return v
'''

if proxy_block in new_content:
    new_content = new_content.replace(proxy_block, new_proxy_block)
    print("Step C: Updated proxy handlers - OK")
else:
    print("ERROR: Proxy block not found")
    raise SystemExit(1)

# Write back
with open(SCRIPT, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("DONE - file written successfully!")
print(f"Total size: {len(new_content)} chars")
