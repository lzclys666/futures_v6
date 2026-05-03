from config.paths import PROJECT_ROOT
import sys
from pathlib import Path

project_dir = PROJECT_ROOT
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

print('[TEST] Connecting to CTP...')
main_engine.connect(ctp_config, 'CTP')

print('[TEST] Waiting for connection (60s)...')
import time

# Wait up to 60 seconds for login
login_success = False
for i in range(60):
    time.sleep(1)
    gateway = main_engine.get_gateway('CTP')
    if gateway and hasattr(gateway, 'td_api') and gateway.td_api:
        if hasattr(gateway.td_api, 'login_status') and gateway.td_api.login_status:
            print(f'[TEST] TD login succeeded after {i+1}s')
            login_success = True
            break
        if i % 10 == 0:
            print(f'[TEST] Waiting... {i}s elapsed, login_status: {getattr(gateway.td_api, "login_status", "unknown")}')

print('[TEST] Checking gateway status...')
gateway = main_engine.get_gateway('CTP')
if gateway:
    print('[TEST] Gateway found:', type(gateway).__name__)
    for attr in ['connected', '_active', 'td_api', 'md_api']:
        if hasattr(gateway, attr):
            val = getattr(gateway, attr)
            print(f'[TEST] Gateway.{attr}:', type(val).__name__ if val else 'None')
    
    # Check TD API status
    if hasattr(gateway, 'td_api') and gateway.td_api:
        td = gateway.td_api
        for attr in ['login_status', 'reqid', 'frontid', 'sessionid']:
            if hasattr(td, attr):
                print(f'[TEST] TD API.{attr}:', getattr(td, attr))
    
    # Check account data
    accounts = main_engine.get_all_accounts()
    print('[TEST] Accounts:', len(accounts))
    for acc in accounts:
        print(f'[TEST] Account: {acc.accountid}, Balance: {acc.balance}, Available: {acc.available}')
    
    # Check positions
    positions = main_engine.get_all_positions()
    print('[TEST] Positions:', len(positions))
    for pos in positions:
        print(f'[TEST] Position: {pos.vt_symbol}, Dir: {pos.direction}, Vol: {pos.volume}')
else:
    print('[TEST] Gateway not found!')

print('[TEST] Done.')
