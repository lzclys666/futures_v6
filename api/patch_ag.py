"""
Robust patch for macro_history_backfill.py AG section.
Finds exact line numbers and replaces content.
"""
SCRIPT = r'C:\Users\Administrator\.qclaw\workspace-agent-63961edb\scripts\macro_history_backfill.py'

with open(SCRIPT, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
print(f"File: {len(lines)} lines")

# Find the 5th 'return {' (AG section's return) - it's at line 909 (1-indexed)
# We can count them
return_count = 0
ag_return_line = None
for i, line in enumerate(lines):
    if 'return {' in line:
        return_count += 1
        if return_count == 5:
            ag_return_line = i
            print(f"Found AG return {{ at line {i+1}")
            # Show surrounding context
            for j in range(i, min(i+12, len(lines))):
                print(f"  {j+1}: {repr(lines[j][:100])}")
            break

if ag_return_line is None:
    print("ERROR: Could not find AG return block")
    raise SystemExit(1)

# The return block ends at the line with just '        }'
# Let's find it: starting from ag_return_line+1, find the line with '        }'
# that closes the return dict (not the fallback '    return {}')
ag_return_end = None
for j in range(ag_return_line + 1, min(ag_return_line + 15, len(lines))):
    stripped = lines[j].strip()
    if stripped == '}':
        ag_return_end = j
        print(f"Return dict closes at line {j+1}")
        break

if ag_return_end is None:
    print("ERROR: Could not find closing brace")
    raise SystemExit(1)

# Now build the new code block
# Lines to insert between '        return {' and the old dict content
new_before_return = '''\
        # 浠垮叡璁??涓?10澶╃殑鏃ユ湡鏌ヨ礋鍊?
        gold_close = None
        for delta in range(0, 10):
            check = (datetime.strptime(d_iso, "%Y-%m-%d") - timedelta(days=delta)).strftime("%Y-%m-%d")
            if check in _GOLD_FUTURES_CACHE:
                gold_close = _GOLD_FUTURES_CACHE[check]
                break
        silver_close = None
        for delta in range(0, 10):
            check = (datetime.strptime(d_iso, "%Y-%m-%d") - timedelta(days=delta)).strftime("%Y-%m-%d")
            if check in _SILVER_FUTURES_CACHE:
                silver_close = _SILVER_FUTURES_CACHE[check]
                break
        cu_close = None
        for delta in range(0, 10):
            check = (datetime.strptime(d_iso, "%Y-%m-%d") - timedelta(days=delta)).strftime("%Y-%m-%d")
            if check in _CU_FUTURES_CACHE:
                cu_close = _CU_FUTURES_CACHE[check]
                break

        # 鏍规嵁鐪熷疄鏈哄惎鍜岄噾铔?璁′换涓轰互涓嬫牴鎹?
        # ag0: CNY/kg, au0: CNY/g * 31.1035 = CNY/kg
        ag_au_real_ratio = None
        if gold_close is not None and silver_close is not None and gold_close > 0:
            gold_kg = gold_close * 31.1035  # CNY/g -> CNY/kg
            ag_au_real_ratio = silver_close / gold_kg

'''

# New return dict content (replaces lines ag_return_line+1 to ag_return_end-1)
new_return_dict = '''\
            "lme_cu_inventory":   cu_inv,
            "lme_cu_chg_rate":   cu_inv_chg_rate,
            "china_pmi":          pmi_val,
            "usdcny":             fx,
            "industrial_ip":     ip_val,
            "cb_gold_chg":       cb_gold,
            "gold_futures_close": gold_close,
            "silver_futures_close": silver_close,
            "cu_futures_close":   cu_close,
            "ag_au_real_ratio":  ag_au_real_ratio,
'''

# Build new lines
# Keep lines 0 to ag_return_line (inclusive) = up to and including '        return {'
# Then add new_before_return
# Then add new_return_dict  
# Then add lines[ag_return_end] (the closing brace) and everything after
new_lines = (
    lines[:ag_return_line + 1] +           # up to and including '        return {'
    [new_before_return] +
    ['            ' + l for l in new_return_dict.strip().split('\n')] +
    lines[ag_return_end:]
)

print(f"Original lines: {len(lines)}")
print(f"New lines: {len(new_lines)}")

new_content = '\n'.join(new_lines)

# ============================================================
# Update proxy handlers
# ============================================================
# Find and replace the lme_cu_inventory_inv proxy
idx_start = new_content.find('    elif proxy == "lme_cu_inventory_inv":')
idx_end = new_content.find('    elif proxy == "ag_au_ag_ratio":', idx_start)

if idx_start == -1 or idx_end == -1:
    print(f"ERROR: Proxy handlers not found: lme_cu_inventory_inv={idx_start}, ag_au_ag_ratio={idx_end}")
    raise SystemExit(1)

old_proxy = new_content[idx_start:idx_end]
print("Found proxy block, replacing...")

new_proxy = '''    elif proxy == "lme_cu_inventory_inv":
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

new_content = new_content.replace(old_proxy, new_proxy)
print("Proxy block updated - OK")

# Write back
with open(SCRIPT, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Written: {len(new_content)} chars")
print("DONE!")
