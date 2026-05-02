#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VNpy Paper Trade 启动脚本
集成 MacroRiskStrategy + RiskEngine
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy_ctp import CtpGateway
from vnpy_ctastrategy import CtaStrategyApp
from vnpy_ctabacktester import CtaBacktesterApp


def run_paper_trade():
    """运行 Paper Trade 模式"""
    print("="*60)
    print("VNpy Paper Trade - MacroRiskStrategy")
    print("="*60)
    
    # 创建事件引擎
    event_engine = EventEngine()
    
    # 创建主引擎
    main_engine = MainEngine(event_engine)
    
    # 添加网关
    main_engine.add_gateway(CtpGateway)
    
    # 添加应用
    main_engine.add_app(CtaStrategyApp)
    main_engine.add_app(CtaBacktesterApp)
    
    # 连接模拟盘
    print("\nConnecting to CTP SimNow...")
    
    # 从环境变量或配置文件读取账户信息
    setting = {
        "用户名": os.getenv("CTP_USERID", ""),
        "密码": os.getenv("CTP_PASSWORD", ""),
        "经纪商代码": os.getenv("CTP_BROKERID", "9999"),
        "交易服务器": os.getenv("CTP_TRADE_SERVER", "180.168.146.187:10101"),
        "行情服务器": os.getenv("CTP_MD_SERVER", "180.168.146.187:10111"),
        "产品名称": os.getenv("CTP_PRODUCT", "simnow_client_test"),
        "授权编码": os.getenv("CTP_AUTH_CODE", ""),
    }
    
    # 检查配置
    if not setting["用户名"]:
        print("[WARNING] CTP credentials not found in environment variables")
        print("Please set: CTP_USERID, CTP_PASSWORD, CTP_AUTH_CODE")
        print("\nStarting in UI mode (manual connection required)...")
    
    # 创建Qt应用
    qapp = create_qapp()
    
    # 创建主窗口
    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()
    
    print("\n[READY] VNpy Paper Trade started")
    print("[INFO] Please load MacroRiskStrategy in CTA Strategy module")
    print("[INFO] Strategy file: strategies/macro_risk_strategy.py")
    
    # 运行Qt应用
    qapp.exec()


def run_backtest():
    """运行回测模式"""
    print("="*60)
    print("VNpy Backtest - MacroRiskStrategy")
    print("="*60)
    
    from vnpy_ctastrategy.backtesting import BacktestingEngine
    from strategies.macro_risk_strategy import MacroRiskStrategy
    from datetime import datetime
    
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 设置参数
    engine.set_parameters(
        vt_symbol="RU2505.SHFE",
        interval="1m",
        start=datetime(2025, 1, 1),
        end=datetime(2025, 3, 31),
        rate=0.0001,
        slippage=2,
        size=10,
        pricetick=5,
        capital=100000,
    )
    
    # 添加策略
    engine.add_strategy(
        MacroRiskStrategy,
        {
            "fast_window": 10,
            "slow_window": 20,
            "use_macro": True,
            "risk_profile": "moderate",
            "enable_risk_engine": True,
        }
    )
    
    # 加载数据
    print("\nLoading historical data...")
    engine.load_data()
    
    # 运行回测
    print("Running backtest...")
    engine.run_backtesting()
    
    # 计算结果
    df = engine.calculate_result()
    statistics = engine.calculate_statistics()
    
    # 显示结果
    print("\n" + "="*60)
    print("Backtest Results")
    print("="*60)
    for key, value in statistics.items():
        print(f"{key}: {value}")
    
    # 显示图表
    engine.show_chart()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="VNpy MacroRiskStrategy Launcher")
    parser.add_argument("--mode", choices=["paper", "backtest"], default="paper",
                        help="Run mode: paper trade or backtest")
    
    args = parser.parse_args()
    
    if args.mode == "paper":
        run_paper_trade()
    else:
        run_backtest()
