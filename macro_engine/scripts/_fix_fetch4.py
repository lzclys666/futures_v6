content = open(r'D:\futures_v6\macro_engine\scripts\check_fetch_unpack.py', encoding='utf-8').read()
# Only one occurrence left - replace the remaining call_node.id with a safe string
content = content.replace(
    'self.findings.append((node.lineno, status, f"{call_node.id}() -> {data_var}, {err_var}"))',
    'fn = call_node.func.id if isinstance(call_node.func, ast.Name) else "?"; self.findings.append((node.lineno, status, f"{fn}() -> {data_var}, {err_var}"))'
)
open(r'D:\futures_v6\macro_engine\scripts\check_fetch_unpack.py', 'w', encoding='utf-8').write(content)
print('done')