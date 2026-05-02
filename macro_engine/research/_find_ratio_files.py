"""找 CU/AL ratio 和 AU/AG ratio 的实际路径"""
import os, glob

# 搜索 D:\futures_macro_engine
root = r'D:\futures_macro_engine'
found = []
for dirpath, dirnames, filenames in os.walk(root):
    for f in filenames:
        if any(k in f.lower() for k in ['cu_al', 'al_cu', 'ratio', 'au_ag', 'ag_au']):
            full = os.path.join(dirpath, f)
            size = os.path.getsize(full)
            found.append((full, size))

print(f'找到 {len(found)} 个相关文件:')
for path, size in sorted(found):
    print(f'  {size:8d}  {path}')

# 尝试其他可能的根目录
alt_roots = [
    r'D:\futures_v6',
    r'D:\futures',
    r'C:\Users\Administrator\Desktop',
]
for r in alt_roots:
    if os.path.exists(r):
        print(f'\n{r} 目录内容:')
        try:
            items = os.listdir(r)
            for item in items[:20]:
                print(f'  {item}')
        except:
            print('  无法读取')
