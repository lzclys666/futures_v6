"""
Patch macro_history_backfill.py - targeted edit approach.
"""
import re

SCRIPT = r'C:\Users\Administrator\.qclaw\workspace-agent-63961edb\scripts\macro_history_backfill.py'

with open(SCRIPT, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# ============================================================
# Step 3: Find and replace AG return block (lines 909-917, 1-indexed)
# ============================================================
# Build the old return block as a single string
old_block = ''.join(lines[908:917])  # 0-indexed: 908-916 inclusive

print("Old block:")
print(repr(old_block[:200]))

# The new block to insert BEFORE the return statement
new_block_before = '''        # 浠垮叡璁??涓?10澶╃殑鏃ユ湡鏌ヨ礋鍊?
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

new_return_dict = '''        return {
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
        }

'''

new_block = new_block_before + new_return_dict

if old_block in ''.join(lines):
    print("Found old block in file")
else:
    print("ERROR: Old block not found!")
    print("Looking for 'ag_au_ag_ratio' in lines[908]...")
    print(repr(''.join(lines[908:920])))
    raise SystemExit(1)

# Replace lines 909-917 (0-indexed: 908-916) with new block
new_lines = lines[:908] + [new_block] + lines[917:]
print(f"Original file: {len(lines)} lines")
print(f"New file: {len(new_lines)} lines")

# ============================================================
# Step 4: Update proxy handlers
# ============================================================
file_content = ''.join(new_lines)

# Update AG_CU_PRICE (lme_cu_inventory_inv) proxy
old_cu_proxy = '''    elif proxy == "lme_cu_inventory_inv":
        # 鍊?鎴垮湴浜ф寚鏁扮瓥鐣?
        chg = raw_data.get("lme_cu_chg_rate")
        if chg is not None:
            return -chg
        v = raw_data.get("lme_cu_inventory")
        if v is None:
            return None
        return -(v / 100000.0)

    elif proxy == "ag_au_ag_ratio":
        # 浠?妯?娴?浠峰?艰?浠ユ?濓紝鍚﹀垯璁′负0
        v = raw_data.get("ag_au_ag_ratio")
        return v'''

new_cu_proxy = '''    elif proxy == "lme_cu_inventory_inv":
        # 鍊?鎴垮湴浜ф寚鏁扮瓥鐣?浠峰兼槸涓嬮檷
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
        # 浠ユ?哄?浠峰?艰?浠ユ?濓紝鍚﹀垯璁′负0
        v = raw_data.get("ag_au_real_ratio")
        return v'''

if old_cu_proxy in file_content:
    file_content = file_content.replace(old_cu_proxy, new_cu_proxy)
    print("Step 4: Updated proxy handlers - OK")
else:
    print("ERROR: Could not find proxy handler block")
    idx = file_content.find('elif proxy == "lme_cu_inventory_inv"')
    print(f"Found lme_cu_inventory_inv at index {idx}")
    if idx >= 0:
        print(repr(file_content[idx:idx+400]))
    raise SystemExit(1)

# Write back
with open(SCRIPT, 'w', encoding='utf-8') as f:
    f.write(file_content)

print(f"Written {len(file_content)} chars back to script")
print("All patches applied!")
