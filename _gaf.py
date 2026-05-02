import re
with open(r'D:\futures_v6\macro_engine\core\data\pit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()
match = re.search(r'def get_active_factors.*?(?=\n    def |\Z)', content, re.DOTALL)
if match:
    print(match.group())
