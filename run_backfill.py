import sys
sys.path.insert(0, r'D:\futures_v6\macro_engine')
from backfill_2y import main
sys.argv = ['backfill_2y.py', '--symbols', 'CU,AG']
main()
