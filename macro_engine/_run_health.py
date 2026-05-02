import subprocess, sys, os
os.chdir(r'D:\futures_v6\macro_engine')
result = subprocess.run(
    [sys.executable, 'crawlers/common/check_health.py'],
    capture_output=True, timeout=60
)
print('STDOUT:')
print(result.stdout.decode('utf-8', errors='replace')[-3000:])
if result.stderr:
    print('STDERR:')
    print(result.stderr.decode('utf-8', errors='replace')[-500:])
