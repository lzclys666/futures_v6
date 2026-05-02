"""Add _load_futures_cache function and call to macro_history_backfill.py"""
SCRIPT = r'C:\Users\Administrator\.qclaw\workspace-agent-63961edb\scripts\macro_history_backfill.py'

with open(SCRIPT, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# 1. Add def _load_futures_cache() before def _load_all_caches()
# ============================================================
func_def = '''def _load_futures_cache() -> None:
    """加载上海期货日线数据：黄金(au0)、白银(ag0)、铜(cu0)"""
    global _GOLD_FUTURES_CACHE, _SILVER_FUTURES_CACHE, _CU_FUTURES_CACHE, _FUTURES_LOADED
    if _FUTURES_LOADED:
        return
    _FUTURES_LOADED = True

    try:
        df_gold = ak.futures_zh_daily_sina(symbol='au0')
        df_gold = df_gold.copy()
        df_gold['date'] = pd.to_datetime(df_gold['date']).dt.strftime('%Y-%m-%d')
        df_gold = df_gold.dropna(subset=['close'])
        _GOLD_FUTURES_CACHE = dict(zip(df_gold['date'], df_gold['close'].astype(float)))
        print(f"  [OK] 黄金期货(au0)缓存: {len(_GOLD_FUTURES_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 黄金期货接口失败: {e}")

    try:
        df_silver = ak.futures_zh_daily_sina(symbol='ag0')
        df_silver = df_silver.copy()
        df_silver['date'] = pd.to_datetime(df_silver['date']).dt.strftime('%Y-%m-%d')
        df_silver = df_silver.dropna(subset=['close'])
        _SILVER_FUTURES_CACHE = dict(zip(df_silver['date'], df_silver['close'].astype(float)))
        print(f"  [OK] 白银期货(ag0)缓存: {len(_SILVER_FUTURES_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 白银期货接口失败: {e}")

    try:
        df_cu = ak.futures_zh_daily_sina(symbol='cu0')
        df_cu = df_cu.copy()
        df_cu['date'] = pd.to_datetime(df_cu['date']).dt.strftime('%Y-%m-%d')
        df_cu = df_cu.dropna(subset=['close'])
        _CU_FUTURES_CACHE = dict(zip(df_cu['date'], df_cu['close'].astype(float)))
        print(f"  [OK] 铜期货(cu0)缓存: {len(_CU_FUTURES_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 铜期货接口失败: {e}")


'''

# Insert before _load_all_caches
old_text = 'def _load_all_caches() -> None:'
new_text = func_def + 'def _load_all_caches() -> None:'

if old_text in content:
    content = content.replace(old_text, new_text, 1)  # Replace only first occurrence
    print("Step 1: Added _load_futures_cache() definition - OK")
else:
    print("ERROR: Could not find 'def _load_all_caches() -> None:'")
    raise SystemExit(1)

# ============================================================
# 2. Add _load_futures_cache() call inside _load_all_caches()
# ============================================================
old_all_caches_call = '''    _load_lme_cu_cache()
    _load_pmi_cache()
    _load_bond_cache()
    _load_cb_gold_cache()
    _load_ip_cache()
    _load_property_cache()'''

new_all_caches_call = '''    _load_lme_cu_cache()
    _load_pmi_cache()
    _load_bond_cache()
    _load_cb_gold_cache()
    _load_ip_cache()
    _load_property_cache()
    _load_futures_cache()'''

if old_all_caches_call in content:
    content = content.replace(old_all_caches_call, new_all_caches_call, 1)
    print("Step 2: Added _load_futures_cache() call - OK")
else:
    print("ERROR: Could not find cache loading calls")
    raise SystemExit(1)

# ============================================================
# 3. Verify proxy handlers are updated
# ============================================================
# The proxy handlers should use cu_futures_close and ag_au_real_ratio
# Let's check
has_cu_futures = 'cu_futures_close' in content
has_ag_real = 'ag_au_real_ratio' in content
print(f"Step 3: Proxy verification - cu_futures_close={has_cu_futures}, ag_au_real_ratio={has_ag_real}")

# ============================================================
# Write back
# ============================================================
with open(SCRIPT, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Written {len(content)} chars")

# Verify syntax
import ast
try:
    ast.parse(content)
    print("SYNTAX OK!")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    lines = content.split('\n')
    for i in range(max(0, e.lineno-3), min(len(lines), e.lineno+5)):
        print(f"  {i+1}: {repr(lines[i][:100])}")
    raise SystemExit(1)

print("DONE!")
