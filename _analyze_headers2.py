"""Extract actual headers content for 14 complex requests.get calls"""
import os, re

root = r'D:\futures_v6\macro_engine\crawlers'
results = []

for dirpath, dirs, filenames in os.walk(root):
    for f in filenames:
        if not f.endswith('.py') or f in ('__init__.py',) or '_run_all' in f:
            continue
        fp = os.path.join(dirpath, f)
        try:
            content = open(fp, 'rb').read().decode('utf-8', errors='ignore')
            if 'requests.get' not in content or 'headers=' not in content:
                continue
            lines = content.split('\n')
            in_complex_call = False
            for i, line in enumerate(lines):
                if 'requests.get' in line and 'headers=' in line:
                    # Find the function this belongs to
                    func_start = i
                    while func_start > 0 and not lines[func_start].strip().startswith('def '):
                        func_start -= 1
                    
                    # Search for headers definition in this function
                    headers_content = ''
                    for j in range(func_start, min(len(lines), func_start + 50)):
                        if 'headers' in lines[j] and '=' in lines[j] and not 'requests.get' in lines[j]:
                            # Found headers definition
                            headers_content = lines[j].strip()
                            # If multi-line dict, capture more
                            if lines[j].strip().endswith('{'):
                                k = j + 1
                                while k < len(lines) and not lines[k].strip().endswith('}'):
                                    headers_content += ' ' + lines[k].strip()
                                    k += 1
                                if k < len(lines):
                                    headers_content += ' ' + lines[k].strip()
                            break
                    
                    # Also check if params= is used
                    has_params = 'params=' in line
                    has_json = 'r.json()' in content or 'resp.json()' in content
                    encoding_line = ''
                    for j in range(i, min(len(lines), i+3)):
                        if 'encoding' in lines[j]:
                            encoding_line = lines[j].strip()
                            break
                    
                    results.append({
                        'file': fp.replace(root + '\\', ''),
                        'line': i+1,
                        'headers_content': headers_content[:200],
                        'has_params': has_params,
                        'has_json': has_json,
                        'encoding': encoding_line
                    })
        except: pass

print(f'Total complex calls: {len(results)}')
print('='*80)
for i, r in enumerate(results, 1):
    print(f'\n[{i}] {r["file"]}:{r["line"]}')
    print(f'    Headers: {r["headers_content"] or "(not found)"}')
    print(f'    Params: {r["has_params"]}, JSON: {r["has_json"]}')
    print(f'    Encoding: {r["encoding"] or "N/A"}')
    print('-'*60)
