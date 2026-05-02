"""Patch _load_fx_cache_with_retry to add Frankfurter API for historical FX data."""
import re

SCRIPT = r'C:\Users\Administrator\.qclaw\workspace-agent-63961edb\scripts\macro_history_backfill.py'

with open(SCRIPT, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the end of the current function - the line after "return" in the fx_spot_quote block
# The fx_spot_quote block ends with "return" after successfully loading spot rate
# We need to find that "return" and insert Frankfurter logic BEFORE it

# Pattern: after the fx_spot_quote block's "return", we have:
#     except Exception as e2:
#         print(f"  [WARN] 汇率现货接口也失败: {e2}")
#
# And then the function ends with:
#     print(f"  [WARN] 所有汇率接口均失败，将使用备用汇率...")
#     _FX_LOADED = False

# The new code to insert: Frankfurter API call between the fx_spot_quote failure
# and the final fallback warning

old_section = '''    except Exception as e2:
        print(f"  [WARN] 汇率现货接口也失败: {e2}")

    print(f"  [WARN] 所有汇率接口均失败，将使用备用汇率 {_FX_FALLBACK}")
    _FX_LOADED = False'''

new_section = '''    except Exception as e2:
        print(f"  [WARN] 汇率现货接口也失败: {e2}")

    # Frankfurter API - 免费开源汇率历史数据（https://api.frankfurter.app）
    try:
        import requests as _req
        _url = "https://api.frankfurter.app/2026-01-01.." + datetime.now().strftime("%Y-%m-%d")
        _r = _req.get(_url, params={"from": "USD", "to": "CNY"}, timeout=15)
        if _r.status_code == 200:
            _data = _r.json()
            _rates = _data.get("rates", {})
            _count = 0
            for _d, _v in _rates.items():
                if isinstance(_v, dict) and "CNY" in _v:
                    _FX_CACHE[_d] = float(_v["CNY"])
                    _count += 1
                elif isinstance(_v, (int, float)):
                    _FX_CACHE[_d] = float(_v)
                    _count += 1
            if _count > 0:
                _FX_LOADED = True
                print(f"  [OK] Frankfurter汇率已加载: {_count} 条 (USD/CNY)")
                # 如果今天还不在缓存里，用最后一天的值
                _today = datetime.now().strftime("%Y-%m-%d")
                if _today not in _FX_CACHE and _rates:
                    _last_date = max(_rates.keys())
                    _last_val = list(_rates[_last_date].values())[0] if isinstance(_rates[_last_date], dict) else _rates[_last_date]
                    _FX_CACHE[_today] = float(_last_val)
                return
    except Exception as e3:
        print(f"  [WARN] Frankfurter接口也失败: {e3}")

    print(f"  [WARN] 所有汇率接口均失败，将使用备用汇率 {_FX_FALLBACK}")
    _FX_LOADED = False'''

if old_section in content:
    content = content.replace(old_section, new_section)
    print("Patch applied - OK")
else:
    print("ERROR: Could not find old section")
    # Try to find the fx_spot_quote block
    idx = content.find("汇率现货接口也失败")
    if idx >= 0:
        print(f"Found at index {idx}")
        print(repr(content[idx-50:idx+300]))
    raise SystemExit(1)

with open(SCRIPT, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify syntax
import ast
try:
    ast.parse(content)
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    raise SystemExit(1)

print("DONE!")
