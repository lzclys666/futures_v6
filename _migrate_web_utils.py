"""
B3-6.2 conservative migration: only replace simple single-line requests.get(url) patterns.
Complex patterns (headers=, multi-line) are reported but not modified.
"""
import os, re

ROOT = r'D:\futures_v6\macro_engine\crawlers'
updated = []
skipped_complex = []
skipped_no_change = []
errors = []

for dirpath, dirs, filenames in os.walk(ROOT):
    for f in filenames:
        if not f.endswith('.py') or f == '__init__.py' or f.endswith('_run_all.py'):
            continue
        fp = os.path.join(dirpath, f)
        try:
            content = open(fp, 'rb').read().decode('utf-8', errors='ignore')
        except:
            errors.append((fp, 'read_error'))
            continue
        
        if 'requests.get' not in content:
            skipped_no_change.append(fp)
            continue
        
        original = content
        
        # Find all requests.get lines and categorize
        lines = content.split('\n')
        new_lines = []
        i = 0
        file_updated = False
        
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            indent = line[:len(line)-len(stripped)]
            
            if 'requests.get' in line and line.strip().startswith(('r = requests.get', 'resp = requests.get', 'response = requests.get')):
                # Check if it's a simple single-line call
                if 'headers=' not in line and '#' not in line.split('requests.get')[0]:
                    # Simple pattern: r = requests.get(url) or r = requests.get(url, timeout=X)
                    m = re.match(r'(\s*)(\w+)\s*=\s*requests\.get\(\s*([^)]+)\s*(?:,\s*timeout=(\d+))?\s*\)', line)
                    if m:
                        var_name = m.group(2)
                        url_var = m.group(3).strip()
                        timeout = m.group(4) or '15'
                        # Check next line for resp.text usage
                        if i+1 < len(lines) and f'{var_name}.text' in lines[i+1]:
                            # Replace both lines
                            new_lines.append(f'{indent}{var_name}_html, {var_name}_err = fetch_url({url_var}, timeout={timeout})')
                            i += 1
                            # Replace .text reference
                            next_line = lines[i]
                            next_line = next_line.replace(f'{var_name}.text', f'{var_name}_html')
                            # Also handle .status_code check if present
                            if f'{var_name}.status_code' in next_line:
                                next_line = re.sub(
                                    rf'if\s+{re.escape(var_name)}\.status_code\s*==\s*200',
                                    f'if not {var_name}_err',
                                    next_line
                                )
                                next_line = re.sub(
                                    rf'{re.escape(var_name)}\.status_code\s*!=\s*200',
                                    f'if {var_name}_err',
                                    next_line
                                )
                            new_lines.append(next_line)
                            file_updated = True
                            i += 1
                            continue
                        else:
                            # Just replace the assignment, add error var
                            new_lines.append(f'{indent}{var_name}_html, {var_name}_err = fetch_url({url_var}, timeout={timeout})')
                            file_updated = True
                            i += 1
                            continue
                    else:
                        # Complex pattern, keep as-is with comment
                        new_lines.append(f'# TODO B3-6.2: {line}')
                        skipped_complex.append((fp, line.strip()))
                        new_lines.append(line)
                        file_updated = True
                        i += 1
                        continue
                else:
                    # Has headers= or other complexity
                    new_lines.append(f'# TODO B3-6.2 complex: {line}')
                    skipped_complex.append((fp, line.strip()))
                    new_lines.append(line)
                    file_updated = True
                    i += 1
                    continue
            else:
                new_lines.append(line)
                i += 1
        
        if file_updated:
            new_content = '\n'.join(new_lines)
            # Add import if not present
            if 'from common.web_utils import' not in new_content:
                # Find where to insert import (after other imports)
                import_line = 'from common.web_utils import fetch_url\n'
                lines = new_content.split('\n')
                inserted = False
                new_lines2 = []
                for j, l in enumerate(lines):
                    new_lines2.append(l)
                    if not inserted and (l.startswith('import ') or l.startswith('from ')):
                        if j+1 < len(lines) and not lines[j+1].startswith('import') and not lines[j+1].startswith('from '):
                            new_lines2.append(import_line)
                            inserted = True
                new_content = '\n'.join(new_lines2)
            
            try:
                open(fp, 'w', encoding='utf-8').write(new_content)
                updated.append(fp)
            except Exception as e:
                errors.append((fp, str(e)))

print(f"Updated: {len(updated)}")
for fp in updated:
    print(f"  + {os.path.relpath(fp, ROOT)}")
print(f"\nSkipped complex: {len(skipped_complex)}")
for fp, line in skipped_complex[:5]:
    print(f"  ! {os.path.relpath(fp, ROOT)}: {line[:60]}")
print(f"\nNo requests.get: {len(skipped_no_change)}")
print(f"Errors: {len(errors)}")
for fp, err in errors:
    print(f"  X {os.path.relpath(fp, ROOT)}: {err}")
