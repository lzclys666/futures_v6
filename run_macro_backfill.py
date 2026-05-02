import subprocess
import sys

result = subprocess.run(
    [sys.executable, r'D:\futures_v6\api\macro_history_backfill.py', '--symbol', 'CU', '--start', '20260101', '--end', '20260422'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print(result.stdout[-3000:] if result.stdout else "(no stdout)")
print(result.stderr[-1000:] if result.stderr else "(no stderr)")
