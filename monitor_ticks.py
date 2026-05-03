from config.paths import DATA_DIR
from config.paths import PROJECT_ROOT
import sys
import time
from pathlib import Path

project_dir = PROJECT_ROOT
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

macro_dir = project_dir / 'macro_engine'
if str(macro_dir) not in sys.path:
    sys.path.insert(0, str(macro_dir))

print('[TEST] Starting VNPY with strategy...')
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from vnpy_ctastrategy import CtaStrategyApp
from vnpy.trader.object import SubscribeRequest
from vnpy.trader.constant import Exchange

# Create engines
event_engine = EventEngine()
main_engine = MainEngine(event_engine)

# Add CTP gateway
main_engine.add_gateway(CtpGateway)

# Add CTA strategy app
cta_app = main_engine.add_app(CtaStrategyApp)

# Initialize engines
main_engine.init_engines()

# Load CTP config
import json
config_path = project_dir / 'config' / 'gateway_config.json'
with open(config_path, 'r', encoding='utf-8') as f:
    gateway_config = json.load(f)

ctp_config = gateway_config.get('CTP', {})

print('[TEST] Connecting to CTP...')
main_engine.connect(ctp_config, 'CTP')

# Wait for connection
print('[TEST] Waiting for CTP connection...')
for i in range(30):
    time.sleep(1)
    gateway = main_engine.get_gateway('CTP')
    if gateway and hasattr(gateway, 'td_api') and gateway.td_api:
        if getattr(gateway.td_api, 'login_status', False):
            print(f'[TEST] CTP connected after {i+1}s')
            break
    if i % 5 == 0:
        print(f'[TEST] Waiting... {i}s')

# Get CTA engine
cta_engine = main_engine.get_engine('CtaStrategy')

print('[TEST] CTA engine:', cta_engine)
print('[TEST] Loading strategies...')

# Load strategy class
from strategies.macro_demo_strategy import MacroDemoStrategy

# Add strategy
print('[TEST] Adding MacroDemoStrategy...')
cta_engine.add_strategy(
    class_name='MacroDemoStrategy',
    strategy_name='macro_ru',
    vt_symbol='RU2505.SHFE',
    setting={
        'signal_file': str(DATA_DIR / "signals/macro_signals.csv"),
        'bar_window': 5,
    }
)

print('[TEST] Strategy added.')
print('[TEST] Initiating strategies...')
cta_engine.init_all_strategies()

# Wait for init
print('[TEST] Waiting for strategy init...')
time.sleep(2)

print('[TEST] Starting all strategies...')
cta_engine.start_all_strategies()

print('[TEST] Strategy started!')
print('[TEST] Subscribing to symbols...')

# Subscribe to symbols (including precious metals for night session)
symbols = [
    ('AU2506', Exchange.SHFE),  # 黄金
    ('AG2506', Exchange.SHFE),  # 白银
    ('RU2505', Exchange.SHFE),
    ('ZN2505', Exchange.SHFE),
    ('RB2510', Exchange.SHFE),
    ('NI2505', Exchange.SHFE),
]

for symbol, exchange in symbols:
    req = SubscribeRequest(symbol=symbol, exchange=exchange)
    main_engine.subscribe(req, 'CTP')
    print(f'[TEST] Subscribed: {symbol}.{exchange.value}')

print('[TEST] Setup complete. Monitoring ticks...')
print('[TEST] Press Ctrl+C to stop')

# Monitor ticks
tick_count = 0
last_tick_time = time.time()

def on_tick(event):
    global tick_count, last_tick_time
    tick = event.data
    tick_count += 1
    last_tick_time = time.time()
    if tick_count % 100 == 0:
        print(f'[TICK] Received {tick_count} ticks. Last: {tick.vt_symbol} @ {tick.last_price}')

# Register tick event
event_engine.register('eTick', on_tick)

# Keep running and print status
try:
    while True:
        time.sleep(10)
        elapsed = time.time() - last_tick_time
        print(f'[STATUS] Total ticks: {tick_count}, Last tick: {elapsed:.1f}s ago')
        
        # Check if we're still receiving data
        if elapsed > 60:
            print('[WARNING] No tick data for 60s, market may be closed')
            
except KeyboardInterrupt:
    print('[TEST] Stopping...')
    cta_engine.stop_all_strategies()
    main_engine.close()
    print('[TEST] Done.')
