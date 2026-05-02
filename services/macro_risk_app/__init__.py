# -*- coding: utf-8 -*-
"""
MacroRiskApp - VNpy App 插件
  
基于 core/risk/risk_engine.py 前 5 条核心规则封装为 VNpy App 形式

核心规则:
  R10 - 宏观熔断
  R5  - 波动率异常过滤
  R6  - 流动性检查
  R8  - 交易时间检查
  R3  - 涨跌停限制

使用方式:
    from services.macro_risk_app import MacroRiskApp
    main_engine.add_app(MacroRiskApp)
"""

from pathlib import Path
from vnpy.trader.app import BaseApp
from .engine import RiskEngine


class MacroRiskApp(BaseApp):
    """宏观风控系统 VNpy App"""

    app_name = "MacroRiskApp"
    app_module = __name__
    app_path = Path(__file__).parent.name
    display_name = "宏观风控系统"
    engine_class = RiskEngine
    widget_name = "RiskManagerWidget"
    icon_name = "macro_risk.ico"
