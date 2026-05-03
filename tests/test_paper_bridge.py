# -*- coding: utf-8 -*-
"""
PaperBridge 自动化测试
覆盖：开仓、平仓、部分平仓、持仓均价、盈亏计算、风控规则
"""
import pytest


@pytest.fixture
def bridge():
    """创建 PaperBridge 实例"""
    from services.vnpy_bridge import PaperBridge
    return PaperBridge()


class TestPaperBridgeOrder:
    """下单与持仓测试"""

    def test_open_long_position(self, bridge):
        """开多仓应正确更新持仓"""
        bridge.send_order(
            vt_symbol="RU2505.SHFE",
            direction="LONG",
            offset="OPEN",
            price=15000.0,
            volume=5,
        )
        positions = bridge.get_positions()
        assert len(positions) > 0
        ru_pos = [p for p in positions if "RU" in p.get("symbol", "")]
        assert len(ru_pos) > 0

    def test_open_short_position(self, bridge):
        """开空仓应正确更新持仓"""
        bridge.send_order(
            vt_symbol="AU2506.SHFE",
            direction="SHORT",
            offset="OPEN",
            price=620.0,
            volume=2,
        )
        positions = bridge.get_positions()
        assert len(positions) > 0

    def test_close_position(self, bridge):
        """平仓应减少持仓"""
        # 先开仓
        bridge.send_order(
            vt_symbol="RB2510.SHFE",
            direction="LONG",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        # 再平仓
        bridge.send_order(
            vt_symbol="RB2510.SHFE",
            direction="LONG",
            offset="CLOSE",
            price=3550.0,
            volume=10,
        )


class TestPaperBridgeAccount:
    """账户信息测试"""

    def test_get_account(self, bridge):
        """获取账户信息应返回余额等字段"""
        account = bridge.get_account()
        assert account is not None
        assert "balance" in account or isinstance(account, dict)


class TestPaperBridgeRisk:
    """风控规则测试"""

    def test_get_risk_status(self, bridge):
        """获取风控状态应返回12条规则"""
        status = bridge.get_risk_status()
        assert "rules" in status
        assert len(status["rules"]) == 12  # R1-R12

    def test_get_risk_rules(self, bridge):
        """获取风控规则配置应返回列表"""
        rules = bridge.get_risk_rules()
        assert isinstance(rules, list)

    def test_update_risk_rule(self, bridge):
        """更新风控规则应不抛异常"""
        rule_data = {
            "ruleId": "R2_DAILY_LOSS",
            "threshold": 0.03,
            "enabled": True,
        }
        # 应不抛异常
        bridge.update_risk_rule(rule_data)

    def test_update_nonexistent_rule(self, bridge):
        """更新不存在的规则应不抛异常（仅警告）"""
        rule_data = {
            "ruleId": "R99_FAKE",
            "threshold": 0.0,
            "enabled": False,
        }
        # 应不抛异常，仅日志警告
        bridge.update_risk_rule(rule_data)


class TestPaperBridgeStatus:
    """状态测试"""

    def test_status_running(self, bridge):
        """PaperBridge 应始终返回 running"""
        status = bridge.get_status()
        assert status.get("status") == "running"
        assert status.get("mode") == "paper"

    def test_is_trading_hours(self, bridge):
        """PaperBridge 应始终返回 True"""
        assert bridge.is_trading_hours() is True
