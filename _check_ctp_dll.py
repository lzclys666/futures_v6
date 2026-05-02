import sys, os
sys.path.insert(0, r'C:\Python311\Lib\site-packages')

results = []

# Check DLLs
import ctypes
dll_path_md = r'C:\Python311\Lib\site-packages\vnpy_ctp\api\thostmduserapi_se.dll'
dll_path_td = r'C:\Python311\Lib\site-packages\vnpy_ctp\api\thosttraderapi_se.dll'

try:
    dll_md = ctypes.CDLL(dll_path_md)
    results.append(f'[OK] Market data DLL: {os.path.getsize(dll_path_md):,} bytes')
except Exception as e:
    results.append(f'[FAIL] Market data DLL: {e}')

try:
    dll_td = ctypes.CDLL(dll_path_td)
    results.append(f'[OK] Trader DLL: {os.path.getsize(dll_path_td):,} bytes')
except Exception as e:
    results.append(f'[FAIL] Trader DLL: {e}')

# Check vnpy_ctp API
try:
    from vnpy_ctp.api import MdApi, TdApi
    results.append(f'[OK] MdApi class: {MdApi}')
    results.append(f'[OK] TdApi class: {TdApi}')
except Exception as e:
    results.append(f'[FAIL] vnpy_ctp API import: {e}')

# Check CtpGateway
try:
    from vnpy_ctp import CtpGateway
    results.append(f'[OK] CtpGateway: {CtpGateway}')
except Exception as e:
    results.append(f'[FAIL] CtpGateway import: {e}')

# Try creating gateway without event engine
try:
    from vnpy_ctp.gateway.ctp_gateway import CtpGateway as CG
    results.append(f'[OK] CtpGateway from gateway module')
except Exception as e:
    results.append(f'[FAIL] CtpGateway: {e}')

# Check that DLLs are in PATH
env_path = os.environ.get('PATH', '')
vnpy_ctp_path = r'C:\Python311\Lib\site-packages\vnpy_ctp\api'
if vnpy_ctp_path in env_path:
    results.append(f'[OK] vnpy_ctp api path is in PATH')
else:
    results.append(f'[WARN] vnpy_ctp api path NOT in PATH (may still work if loaded by pyd)')

for r in results:
    print(r)
