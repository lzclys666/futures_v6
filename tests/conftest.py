#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pytest配置 - 解决 strategy fixture not found
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest


@pytest.fixture
def strategy():
    """
    提供 MacroRiskStrategy 实例用于测试
    """
    from strategies.macro_risk_strategy import MacroRiskStrategy
    
    # 使用 MockCtaEngine (用 None 代替，测试环境下足够)
    class MockCtaEngine:
        def write_log(self, msg, strategy=None):
            pass
    
    engine = MockCtaEngine()
    s = MacroRiskStrategy(engine, "test_strategy", "RU2505.SHFE", {})
    s.on_init()
    return s


@pytest.fixture
def risk_engine():
    """
    提供 RiskEngine 实例用于测试
    """
    from core.risk.risk_engine import RiskEngine
    
    return RiskEngine(profile='moderate')


@pytest.fixture
def mock_context():
    """
    提供标准测试用风控上下文
    """
    from core.risk.risk_engine import RiskContext
    
    return RiskContext(
        account={
            'equity': 100000,
            'available': 80000,
            'used_margin': 15000,
            'frozen': 5000,
            'pre_frozen': 0,
        },
        positions={
            'RU2505.SHFE': 1,
        },
        market_data={
            'macro_score': 50,
            'RU2505_atr_14': 300,
            'RU2505_price': 15000,
            'RU2505_avg_volume_20d': 100000,
            'RU2505_limit_up': 16000,
            'RU2505_limit_down': 14000,
            'RU2505_volatility_20d': 0.18,
        }
    )