import sys
from pathlib import Path

project_dir = Path('D:/futures_v6')
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

macro_dir = project_dir / 'macro_engine'
if str(macro_dir) not in sys.path:
    sys.path.insert(0, str(macro_dir))

print('[TEST] Creating EventEngine...')
from vnpy.event import EventEngine
event_engine = EventEngine()

print('[TEST] Creating MainEngine...')
from vnpy.trader.engine import MainEngine
main_engine = MainEngine(event_engine)

print('[TEST] Adding CtaStrategyApp...')
from vnpy_ctastrategy import CtaStrategyApp
main_engine.add_app(CtaStrategyApp)

print('[TEST] Adding CtpGateway...')
from vnpy_ctp import CtpGateway
main_engine.add_gateway(CtpGateway)

print('[TEST] init_engines...')
main_engine.init_engines()

print('[TEST] Loading gateway config...')
import json
config_path = project_dir / 'config' / 'gateway_config.json'
with open(config_path, 'r', encoding='utf-8') as f:
    gateway_config = json.load(f)

ctp_config = gateway_config.get('CTP', {})
print('[TEST] CTP config loaded, keys:', list(ctp_config.keys()))
print('[TEST] Servers:', ctp_config.get('交易服务器'), ctp_config.get('行情服务器'))

# Try with different auth codes
auth_codes = [
    '0000000000000000',
    '',
    '1234567890123456',
]

for auth_code in auth_codes:
    print(f'\n[TEST] Trying auth_code: {repr(auth_code)}')
    ctp_config['授权编码'] = auth_code
    
    print('[TEST] Connecting to CTP...')
    main_engine.connect(ctp_config, 'CTP')
    
    print('[TEST] Waiting for connection (30s)...')
    import time
    
    for i in range(30):
        time.sleep(1)
        gateway = main_engine.get_gateway('CTP')
        if gateway and hasattr(gateway, 'td_api') and gateway.td_api:
            if hasattr(gateway.td_api, 'login_status') and gateway.td_api.login_status:
                print(f'[TEST] TD login succeeded after {i+1}s')
                break
            if i % 10 == 0:
                print(f'[TEST] Waiting... {i}s elapsed, login_status: {getattr(gateway.td_api, "login_status", "unknown")}')
    
    # Disconnect and try next
    print('[TEST] Disconnecting...')
    main_engine.close()
    time.sleep(2)
    
    # Recreate engines
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_app(CtaStrategyApp)
    main_engine.add_gateway(CtpGateway)
    main_engine.init_engines()

print('[TEST] All attempts done.')
