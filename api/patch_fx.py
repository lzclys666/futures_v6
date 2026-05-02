"""Patch _load_fx_cache_with_retry to use fx_spot_quote as fallback."""
SCRIPT = r'C:\Users\Administrator\.qclaw\workspace-agent-63961edb\scripts\macro_history_backfill.py'

with open(SCRIPT, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the function by structure: "def _load_fx_cache_with_retry" followed by "ak.forex_hist_em"
func_start = content.find('def _load_fx_cache_with_retry')
if func_start < 0:
    print("ERROR: Could not find _load_fx_cache_with_retry")
    raise SystemExit(1)

# Find where the function ends (next function def or end of file)
next_func = content.find('\ndef ', func_start + 10)
if next_func < 0:
    next_func = len(content)

# The function body is from func_start to next_func
old_body = content[func_start:next_func]
print(f"Found function body at {func_start}, length {len(old_body)}")
print("First 200 chars:", repr(old_body[:200]))

# Find where the function ends (look for the final else clause with _FX_LOADED = False)
# The old function ends with: "print(f\"  [WARN] ...\"); _FX_LOADED = False"
# We want to add the fx_spot_quote fallback BEFORE that final else clause

# Look for the pattern: "else:\n                print(f\"  [WARN] 汇率接口彻底失败"
# The function ends with _FX_LOADED = False at the final else clause

# Let's find the last "else:" block in the function
last_else = old_body.rfind('else:')
print(f"Last else at offset {last_else} in function body")
print("Context around last else:")
print(repr(old_body[last_else-50:last_else+200]))

# Find the return statement after the for loop ends
# The function structure is:
# for attempt in range(max_retries):
#     try: ... except: ... (repeated)
# else:  <-- this is the for-else, NOT the if-else!
# So the real end is the last _FX_LOADED = False followed by the next function

# Actually, the issue is that Python's for-else has "else:" which is NOT an if-else
# The real function end is at "        _FX_LOADED = False" followed by "\n\n\ndef "

# Find "        _FX_LOADED = False" near the end
fx_loaded_false = old_body.rfind('        _FX_LOADED = False')
print(f"_FX_LOADED = False at offset {fx_loaded_false}")
print("Context:")
print(repr(old_body[fx_loaded_false-100:fx_loaded_false+100]))

# The new code to insert after the final _FX_LOADED = False
# We need to add: try fx_spot_quote, then set _FX_LOADED = True if successful

new_fallback_code = '''

    # 历史接口全部失败，尝试 fx_spot_quote 现货接口
    try:
        df_spot = ak.fx_spot_quote()
        # 找 USD/CNY 现货中间价
        usd_row = df_spot[df_spot.iloc[:, 0].str.contains("USD/CNY", na=False)]
        if not usd_row.empty:
            bid = float(usd_row.iloc[0, 1])
            ask = float(usd_row.iloc[0, 2])
            spot_rate = (bid + ask) / 2.0
            today_str = datetime.now().strftime("%Y-%m-%d")
            _FX_CACHE[today_str] = spot_rate
            _FX_LOADED = True
            print(f"  [OK] 汇率现货已加载 (USD/CNY={spot_rate:.4f})")
            return
    except Exception as e2:
        print(f"  [WARN] 汇率现货接口也失败: {e2}")

    print(f"  [WARN] 所有汇率接口均失败，将使用备用汇率 {_FX_FALLBACK}")
    _FX_LOADED = False'''

# Insert after the last "        _FX_LOADED = False" in the function
# Find the position right after the last _FX_LOADED = False
insert_pos = func_start + fx_loaded_false + len('        _FX_LOADED = False')
print(f"Will insert new code at position {insert_pos}")

new_content = content[:insert_pos] + new_fallback_code + content[insert_pos:]

with open(SCRIPT, 'w', encoding='utf-8') as f:
    f.write(new_content)

# Verify syntax
import ast
try:
    ast.parse(new_content)
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    lines = new_content.split('\n')
    for i in range(max(0, e.lineno-3), min(len(lines), e.lineno+5)):
        print(f"  {i+1}: {repr(lines[i][:100])}")
    raise SystemExit(1)

print("DONE!")
