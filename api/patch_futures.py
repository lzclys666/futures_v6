"""
Patch macro_history_backfill.py to add futures cache loading and real gold/silver/copper prices.
"""
import re

SCRIPT = r'C:\Users\Administrator\.qclaw\workspace-agent-63961edb\scripts\macro_history_backfill.py'

with open(SCRIPT, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# Step 1: Add _load_futures_cache() call to _load_all_caches
# ============================================================
old_caches = 'def _load_all_caches() -> None:\n    """\u4e00\u6b21\u6027\u52a0\u8f7d\u6240\u6709 CU/AU/AG \u7f13\u5b58"""\n    _load_lme_cu_cache()\n    _load_pmi_cache()\n    _load_bond_cache()\n    _load_cb_gold_cache()\n    _load_ip_cache()\n    _load_property_cache()'

new_caches = 'def _load_all_caches() -> None:\n    """\u4e00\u6b21\u6027\u52a0\u8f7d\u6240\u6709 CU/AU/AG \u7f13\u5b58"""\n    _load_lme_cu_cache()\n    _load_pmi_cache()\n    _load_bond_cache()\n    _load_cb_gold_cache()\n    _load_ip_cache()\n    _load_property_cache()\n    _load_futures_cache()'

if old_caches in content:
    content = content.replace(old_caches, new_caches)
    print('Step 1: Updated _load_all_caches - OK')
else:
    print('ERROR: Could not find _load_all_caches text')
    # Try alternate encoding
    alt = 'def _load_all_caches() -> None:\n    """'
    idx = content.find('def _load_all_caches')
    print(f'Found _load_all_caches at index {idx}')
    print('Bytes around it:', repr(content[idx:idx+200])[:300])
    raise SystemExit(1)

# ============================================================
# Step 2: Add _load_futures_cache() function before _load_all_caches
# ============================================================
new_func = '''def _load_futures_cache() -> None:
    """\u52a0\u8f7d\u4e0a\u6d77\u671f\u8d27\u65e5\u7ebf\u6570\u636e\uff1a\u9ec4\u91d1(au0)\u3001\u767d\u94f6(ag0)\u3001\u94dc(cu0)"""
    global _GOLD_FUTURES_CACHE, _SILVER_FUTURES_CACHE, _CU_FUTURES_CACHE, _FUTURES_LOADED
    if _FUTURES_LOADED:
        return
    _FUTURES_LOADED = True

    # \u9ec4\u91d1\u671f\u8d27 au0\uff08CNY/g\uff09
    try:
        df_gold = ak.futures_zh_daily_sina(symbol='au0')
        df_gold = df_gold.copy()
        df_gold['date'] = pd.to_datetime(df_gold['date']).dt.strftime('%Y-%m-%d')
        df_gold = df_gold.dropna(subset=['close'])
        _GOLD_FUTURES_CACHE = dict(zip(df_gold['date'], df_gold['close'].astype(float)))
        print(f"  [OK] \u9ec4\u91d1\u671f\u8d27(au0)\u7f13\u5b58\u5df2\u52a0\u8f7d: {len(_GOLD_FUTURES_CACHE)} \u6761\uff0c\u6700\u65b0: {sorted(_GOLD_FUTURES_CACHE.keys())[-1]}")
    except Exception as e:
        print(f"  [WARN] \u9ec4\u91d1\u671f\u8d27\u63a5\u53e3\u5931\u8d25: {e}")

    # \u767d\u94f6\u671f\u8d27 ag0\uff08CNY/kg\uff09
    try:
        df_silver = ak.futures_zh_daily_sina(symbol='ag0')
        df_silver = df_silver.copy()
        df_silver['date'] = pd.to_datetime(df_silver['date']).dt.strftime('%Y-%m-%d')
        df_silver = df_silver.dropna(subset=['close'])
        _SILVER_FUTURES_CACHE = dict(zip(df_silver['date'], df_silver['close'].astype(float)))
        print(f"  [OK] \u767d\u94f6\u671f\u8d27(ag0)\u7f13\u5b58\u5df2\u52a0\u8f7d: {len(_SILVER_FUTURES_CACHE)} \u6761\uff0c\u6700\u65b0: {sorted(_SILVER_FUTURES_CACHE.keys())[-1]}")
    except Exception as e:
        print(f"  [WARN] \u767d\u94f6\u671f\u8d27\u63a5\u53e3\u5931\u8d25: {e}")

    # \u94dc\u671f\u8d27 cu0\uff08CNY/ton\uff09
    try:
        df_cu = ak.futures_zh_daily_sina(symbol='cu0')
        df_cu = df_cu.copy()
        df_cu['date'] = pd.to_datetime(df_cu['date']).dt.strftime('%Y-%m-%d')
        df_cu = df_cu.dropna(subset=['close'])
        _CU_FUTURES_CACHE = dict(zip(df_cu['date'], df_cu['close'].astype(float)))
        print(f"  [OK] \u94dc\u671f\u8d27(cu0)\u7f13\u5b58\u5df2\u52a0\u8f7d: {len(_CU_FUTURES_CACHE)} \u6761\uff0c\u6700\u65b0: {sorted(_CU_FUTURES_CACHE.keys())[-1]}")
    except Exception as e:
        print(f"  [WARN] \u94dc\u671f\u8d27\u63a5\u53e3\u5931\u8d25: {e}")


'''

# Insert before _load_all_caches
idx = content.find('def _load_all_caches')
if idx == -1:
    print('ERROR: Could not find _load_all_caches to insert before')
    raise SystemExit(1)
content = content[:idx] + new_func + content[idx:]
print('Step 2: Added _load_futures_cache() function - OK')

# ============================================================
# Step 3: Update AG data fetch to use real futures prices
# ============================================================
# Find the AG section return statement and update it
# We need to add gold/silver/copper futures close prices to the returned dict
old_ag_return = '''        return {
            "lme_cu_inventory":   cu_inv,
            "lme_cu_chg_rate":   cu_inv_chg_rate,  # \u94dc\u5e93\u5b58\u65e5\u73af\u6bd4\uff08AG_CU_PRICE \u7528\uff09
            "china_pmi":          pmi_val,
            "usdcny":             fx,
            "industrial_ip":     ip_val,
            "cb_gold_chg":       cb_gold,
            "ag_au_ag_ratio":    ag_au_ag_ratio,    # \u91d1\u94f6\u6bd4\u56fa\u7d20\uff08\u65e5\u73af\u6bd4\uff09
        }'''

new_ag_return = '''        # \u9ec4\u91d1/\u767d\u94f6/\u94dc\u671f\u8d27\u6536\u76d8\u4ef7\uff08\u524d\u5411\u586b\u5145\uff09
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

        # \u91d1\u94f6\u6bd4 = \u767d\u94f6\u6536\u76d8/\u9ec4\u91d1\u6536\u76d8
        # ag0: CNY/kg, au0: CNY/g * 31.1035 = CNY/kg
        ag_au_real_ratio = None
        if gold_close is not None and silver_close is not None and gold_close > 0:
            gold_kg = gold_close * 31.1035  # CNY/g → CNY/kg
            ag_au_real_ratio = silver_close / gold_kg

        return {
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
        }'''

if old_ag_return in content:
    content = content.replace(old_ag_return, new_ag_return)
    print('Step 3: Updated AG data fetch with real futures prices - OK')
else:
    print('ERROR: Could not find old AG return statement')
    # Find it
    idx = content.find('lme_cu_chg_rate')
    print(f'Found lme_cu_chg_rate at index {idx}')
    print(repr(content[idx-50:idx+400]))
    raise SystemExit(1)

# ============================================================
# Step 4: Update proxy handlers for AG_CU_PRICE and AG_AU_AG_RATIO
# ============================================================
# Change AG_CU_PRICE to use cu_futures_close instead of lme_cu_inventory_inv
old_cu_proxy = '''    elif proxy == "lme_cu_inventory_inv":
        # \u94dc\u5e93\u5b58\u65e5\u73af\u6bd4\u53d8\u5316\u53d6\u53cd\uff08\u5e93\u5b58\u4e0b\u964d\u2192\u94dc\u4ef7\u4e0a\u6da8\u2192\u94f6\u4ef7\u53d7\u76ca\uff09
        chg = raw_data.get("lme_cu_chg_rate")
        if chg is not None:
            return -chg
        v = raw_data.get("lme_cu_inventory")
        if v is None:
            return None
        return -(v / 100000.0)'''

new_cu_proxy = '''    elif proxy == "lme_cu_inventory_inv":
        # \u94dc\u671f\u8d27\u6536\u76d8\u4ef7\uff08CNY/ton\uff09\u76f4\u63a5\u4f7f\u7528\u3002
        # \u91cd\u94c1\u884c\u60c5\u4e0b\uff0c\u94dc\u4ef7\u4e0a\u6da8 \u2192 \u94dc\u5e94\u7528\u7b56\u7565\u91cd\u94c1\u89c2\u5ff5\u3002
        cu_price = raw_data.get("cu_futures_close")
        if cu_price is not None:
            return cu_price
        # \u964d\u7ea7\uff1a\u7528LME\u94dc\u5e93\u5b58\u65e5\u73af\u6bd4\u53d8\u5316\u53d6\u53cd
        chg = raw_data.get("lme_cu_chg_rate")
        if chg is not None:
            return -chg
        v = raw_data.get("lme_cu_inventory")
        if v is None:
            return None
        return -(v / 100000.0)'''

if old_cu_proxy in content:
    content = content.replace(old_cu_proxy, new_cu_proxy)
    print('Step 4a: Updated AG_CU_PRICE proxy (lme_cu_inventory_inv) - OK')
else:
    print('ERROR: Could not find lme_cu_inventory_inv proxy')
    idx = content.find('elif proxy == \"lme_cu_inventory_inv\"')
    print(f'Found at index {idx}')
    print(repr(content[idx:idx+300]))
    raise SystemExit(1)

# Update AG_AU_AG_RATIO proxy to use real ratio
old_ratio_proxy = '''    elif proxy == "ag_au_ag_ratio":
        # \u91d1\u94f6\u6bd4\u56fa\u7d20\uff1a\u65e5\u73af\u6bd4\u53d8\u7387
        v = raw_data.get("ag_au_ag_ratio")
        return v'''

new_ratio_proxy = '''    elif proxy == "ag_au_ag_ratio":
        # \u91d1\u94f6\u6bd4\uff1a\u771f\u5b9e\u91d1\u94f6\u6bd4\u503c\uff08\u767d\u94f6\u6536\u76d8/\u9ec4\u91d1\u6536\u76d8\uff09
        v = raw_data.get("ag_au_real_ratio")
        return v'''

if old_ratio_proxy in content:
    content = content.replace(old_ratio_proxy, new_ratio_proxy)
    print('Step 4b: Updated AG_AU_AG_RATIO proxy (ag_au_ag_ratio) - OK')
else:
    print('ERROR: Could not find ag_au_ag_ratio proxy')
    idx = content.find('elif proxy == \"ag_au_ag_ratio\"')
    print(f'Found at index {idx}')
    print(repr(content[idx:idx+200]))
    raise SystemExit(1)

# ============================================================
# Write back
# ============================================================
with open(SCRIPT, 'w', encoding='utf-8') as f:
    f.write(content)

print()
print('All patches applied successfully!')
print('Total file size:', len(content), 'chars')
