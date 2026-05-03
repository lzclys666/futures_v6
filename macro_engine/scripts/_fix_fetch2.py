import re
content = open(r'D:\futures_v6\macro_engine\scripts\check_fetch_unpack.py', encoding='utf-8').read()
# Fix 1: call_node.id
content = content.replace(
    'if call_node and call_node.id in ("fetch_url", "fetch_json"):',
    'if call_node and isinstance(call_node.func, ast.Name) and call_node.func.id in ("fetch_url", "fetch_json"):'
)
# Fix 2: {call_node.id}() in findings
content = content.replace(
    'self.findings.append((node.lineno, status, f"{call_node.id}() -> {data_var}, {err_var}"))',
    'self.findings.append((node.lineno, status, f"fetch_{chr(85)}() -> {data_var}, {err_var}"))'
)
open(r'D:\futures_v6\macro_engine\scripts\check_fetch_unpack.py', 'w', encoding='utf-8').write(content)
print('done')