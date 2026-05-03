content = open(r'D:\futures_v6\macro_engine\scripts\check_fetch_unpack.py', encoding='utf-8').read()
# Fix: replace the remaining call_node.id in findings append
content = content.replace(
    'self.findings.append((node.lineno, status, f"{call_node.id}() -> {data_var}, {err_var}"))',
    'self.findings.append((node.lineno, status, f"fetch_() -> {data_var}, {err_var}"))'
)
open(r'D:\futures_v6\macro_engine\scripts\check_fetch_unpack.py', 'w', encoding='utf-8').write(content)
print('done')