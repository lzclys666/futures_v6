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

print('[TEST] init_engines...')
main_engine.init_engines()

print('[TEST] Getting CtaEngine...')
cta_engine = main_engine.get_engine('CtaStrategy')
print('[TEST] CtaEngine type:', type(cta_engine).__name__)

print('[TEST] Loading strategies from macro_engine/strategies...')
strategy_dir = project_dir / 'macro_engine' / 'strategies'
cta_engine.load_strategy_class_from_folder(strategy_dir, module_name='macro_engine.strategies')

class_names = cta_engine.get_all_strategy_class_names()
print('[TEST] Loaded strategies:', class_names)

if 'MacroDemoStrategy' in class_names:
    print('[TEST] SUCCESS: MacroDemoStrategy loaded!')
else:
    print('[TEST] FAIL: MacroDemoStrategy not found!')
