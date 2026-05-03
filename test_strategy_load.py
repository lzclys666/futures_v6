# -*- coding: utf-8 -*-
from config.paths import MACRO_ENGINE
"""
测试脚本：验证 CtaEngine 是否能成功加载并实例化 macro_demo_strategy
"""
import sys
import os
from pathlib import Path

# 设置路径
project_dir = r"D:\futures_v6"
os.chdir(project_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.join(project_dir, "strategies"))
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "strategies"))

# 设置 Qt 无头模式
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctastrategy import CtaStrategyApp

print("=" * 50)
print("Phase 1.1: VNpy 策略加载验证")
print("=" * 50)

# 创建引擎
event_engine = EventEngine()
main_engine = MainEngine(event_engine)

# 添加 CTA 策略应用
main_engine.add_app(CtaStrategyApp)
main_engine.init_engines()

# 获取 CtaEngine
cta_engine = main_engine.get_engine("CtaStrategy")

if not cta_engine:
    print("[错误] CtaEngine 未找到")
    sys.exit(1)

print(f"[成功] CtaEngine 已获取: {type(cta_engine)}")

# 加载策略 - 使用 Path 对象
strategy_dir = Path(project_dir) / "macro_engine" / "strategies"
if strategy_dir.exists():
    cta_engine.load_strategy_class_from_folder(strategy_dir, module_name="macro_engine.strategies")
    class_names = cta_engine.get_all_strategy_class_names()
    print(f"[策略] 已加载 {len(class_names)} 个策略类: {class_names}")
else:
    print(f"[策略] 策略目录不存在: {strategy_dir}")

# 也尝试从用户目录加载
user_strategy_dir = Path(os.path.expanduser("~")) / "strategies"
if user_strategy_dir.exists():
    cta_engine.load_strategy_class_from_folder(user_strategy_dir, module_name="strategies")
    class_names = cta_engine.get_all_strategy_class_names()
    print(f"[策略] 从用户目录加载后，共 {len(class_names)} 个策略类: {class_names}")

# 检查 macro_demo_strategy 是否已加载
if "MacroDemoStrategy" in class_names:
    print("[成功] MacroDemoStrategy 已注册到 CtaEngine")
    
    # 尝试获取策略类（通过 classes 字典）
    try:
        strategy_class = cta_engine.classes.get("MacroDemoStrategy")
        if strategy_class:
            print(f"[成功] 策略类获取成功: {strategy_class}")
            print(f"[成功] 策略参数: {strategy_class.parameters}")
            print(f"[成功] 策略变量: {strategy_class.variables}")
            
            # 尝试创建策略实例（模拟）
            setting = {
                "fast_window": 10,
                "slow_window": 20,
                "use_macro": True,
                "csv_path_str": "str(MACRO_ENGINE)/output/{symbol}_macro_daily_{date}.csv"
            }
            
            # 模拟创建策略实例
            try:
                strategy = strategy_class(cta_engine, "MacroDemo_RU", "RU.SHF", setting)
                print(f"[成功] 策略实例化成功: {strategy}")
                print(f"[成功] 策略参数值:")
                print(f"  - fast_window: {strategy.fast_window}")
                print(f"  - slow_window: {strategy.slow_window}")
                print(f"  - use_macro: {strategy.use_macro}")
                print(f"  - csv_path_str: {strategy.csv_path_str}")
                
                # 测试 on_init 方法
                strategy.on_init()
                print(f"[成功] 策略初始化成功")
                
            except Exception as e:
                print(f"[错误] 策略实例化失败: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("[错误] 策略类未找到")
    except Exception as e:
        print(f"[错误] 策略实例化失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print("[错误] MacroDemoStrategy 未找到")

print("=" * 50)
print("验证完成")
print("=" * 50)

# 清理
main_engine.close()
event_engine.stop()
