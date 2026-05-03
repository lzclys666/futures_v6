"""Analyze 12 complex requests.get() calls with headers= in crawlers"""
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
            for i, line in enumerate(lines):
                if 'requests.get' in line and 'headers=' in line:
                    # Get surrounding context (5 lines after)
                    context_lines = lines[i:i+6]
                    full_context = '\n'.join(context_lines)
                    
                    # Extract headers variable name
                    hdrs_var = None
                    m = re.search(r'headers\s*=\s*(\w+)', line)
                    if m:
                        hdrs_var = m.group(1)
                    
                    # Find headers definition
                    hdrs_def = ''
                    for cl in content.split('\n'):
                        if hdrs_var and cl.strip().startswith(hdrs_var + '='):
                            hdrs_def = cl.strip()[:150]
                            break
                        if not hdrs_var and 'headers=' in cl and cl.strip().startswith('headers='):
                            hdrs_def = cl.strip()[:150]
                            break
                    
                    results.append({
                        'file': fp.replace(root + '\\', ''),
                        'line': i+1,
                        'context': full_context[:200],
                        'hdrs_var': hdrs_var or 'inline',
                        'hdrs_def': hdrs_def
                    })
        except Exception as e:
            pass

print(f'Total complex calls with headers=: {len(results)}')
print('='*80)
for i, r in enumerate(results, 1):
    print(f'\n[{i}] {r["file"]}:{r["line"]}')
    print(f'    Headers: {r["hdrs_var"]}')
    print(f'    Definition: {r["hdrs_def"]}')
    print(f'    Context: {r["context"][:120]}...')
    print('-'*60)
