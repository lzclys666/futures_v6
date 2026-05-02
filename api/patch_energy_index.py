"""Patch to add China energy index cache for AG_INDUSTRIAL_IP."""
SCRIPT = r'C:\Users\Administrator\.qclaw\workspace-agent-63961edb\scripts\macro_history_backfill.py'
with open(SCRIPT, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line index where PMI_CACHE is defined
pmi_line_idx = None
for i, line in enumerate(lines):
    if '_PMI_CACHE: Dict' in line and 'global' not in line:
        pmi_line_idx = i
        break

if pmi_line_idx is None:
    print("ERROR: PMI_CACHE definition not found")
    raise SystemExit(1)

print(f"Found PMI_CACHE at line {pmi_line_idx}: {repr(lines[pmi_line_idx][:50])}")

# New code to insert
new_global = '''# ======== 中国能源指数缓存（日频）=======
_ENERGY_INDEX_CACHE: Dict[str, float] = {}
_ENERGY_INDEX_LOADED: bool = False

'''

# Insert before PMI_CACHE
lines.insert(pmi_line_idx, new_global)
print(f"Step 1: Inserted global cache before line {pmi_line_idx} - OK")

# Now find where to insert the load function - right before _load_pmi_cache
# Look for "def _load_pmi_cache"
load_func_idx = None
for i, line in enumerate(lines):
    if 'def _load_pmi_cache' in line:
        load_func_idx = i
        break

if load_func_idx is None:
    print("ERROR: _load_pmi_cache not found")
    raise SystemExit(1)

print(f"Found _load_pmi_cache at line {load_func_idx}")

new_load_func = '''def _load_energy_index_cache() -> None:
    """加载中国能源指数（日频），用于替代工业增加值常数"""
    global _ENERGY_INDEX_CACHE, _ENERGY_INDEX_LOADED
    try:
        df = ak.macro_china_energy_index()
        date_col = df.columns[0]
        idx_col = df.columns[1]
        for _, row in df.iterrows():
            d = str(row[date_col])[:10]
            try:
                val = float(row[idx_col])
                if 500 < val < 2000:
                    _ENERGY_INDEX_CACHE[d] = val
            except (ValueError, TypeError):
                pass
        _ENERGY_INDEX_LOADED = True
        print(f"  [OK] 中国能源指数已加载: {len(_ENERGY_INDEX_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 能源指数加载失败: {e}")
        _ENERGY_INDEX_LOADED = False


'''

lines.insert(load_func_idx, new_load_func)
print(f"Step 2: Inserted _load_energy_index_cache function - OK")

# Now find _load_all_caches and add the call
all_caches_idx = None
for i, line in enumerate(lines):
    if 'def _load_all_caches' in line:
        all_caches_idx = i
        break

if all_caches_idx is None:
    print("ERROR: _load_all_caches not found")
    raise SystemExit(1)

print(f"Found _load_all_caches at line {all_caches_idx}")

# Find where _load_lme_cu_cache() is called
lme_call_idx = None
for i, line in enumerate(lines):
    if '_load_lme_cu_cache()' in line:
        lme_call_idx = i
        break

if lme_call_idx is None:
    print("ERROR: _load_lme_cu_cache() call not found")
    raise SystemExit(1)

print(f"Found _load_lme_cu_cache() call at line {lme_call_idx}")

# Insert after _load_lme_cu_cache()
lines.insert(lme_call_idx + 1, '    _load_energy_index_cache()\n')
print("Step 3: Added _load_energy_index_cache call - OK")

# Now find the AG fetch section and add energy_index forward-fill
# Find where "industrial_ip" is set in the AG fetch
ag_ip_idx = None
for i, line in enumerate(lines):
    if 'ip_val = _get_monthly_filled(d_iso, _IP_CACHE)' in line and i > all_caches_idx:
        ag_ip_idx = i
        break

if ag_ip_idx is None:
    print("ERROR: AG industrial_ip line not found")
    raise SystemExit(1)

print(f"Found AG industrial_ip at line {ag_ip_idx}: {repr(lines[ag_ip_idx])}")

# Insert energy index forward-fill after ip_val
energy_code = '''        # 中国能源指数（日频前向填充）
        energy_val = _ENERGY_INDEX_CACHE.get(d_iso)
        if energy_val is None:
            d_dt = datetime.strptime(d_iso, "%Y-%m-%d")
            for delta in range(1, 15):
                check = (d_dt - timedelta(days=delta)).strftime("%Y-%m-%d")
                if check in _ENERGY_INDEX_CACHE:
                    energy_val = _ENERGY_INDEX_CACHE[check]
                    break

'''
lines.insert(ag_ip_idx + 1, energy_code)
print("Step 4: Added energy index forward-fill - OK")

# Now add energy_index to the return dict for AG
# Find the return dict line that contains "industrial_ip"
ag_return_idx = None
for i, line in enumerate(lines):
    if '"industrial_ip"' in line and i > ag_ip_idx:
        ag_return_idx = i
        break

if ag_return_idx is None:
    print("ERROR: AG return dict industrial_ip not found")
    raise SystemExit(1)

print(f"Found AG return dict at line {ag_return_idx}: {repr(lines[ag_return_idx])}")

# Replace industrial_ip line with industrial_ip + energy_index
old_line = lines[ag_return_idx]
lines[ag_return_idx] = old_line.rstrip()[:-1] + ',\n            "energy_index": energy_val,\n        }'

# Actually let me be more careful here
# The old line ends with "},\n" - we need to change the last }, to a comma and add energy_index
print(f"Old return line: {repr(lines[ag_return_idx])}")
raise SystemExit(1)  # Debug

with open(SCRIPT, 'w', encoding='utf-8') as f:
    f.writelines(lines)

# Verify syntax
import ast
with open(SCRIPT, 'r', encoding='utf-8') as f:
    content = f.read()
try:
    ast.parse(content)
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    raise SystemExit(1)

print("DONE!")
