# -*- coding: utf-8 -*-
"""
API 路由自动化测试
覆盖：/api/risk/status, /api/risk/simulate, /api/trading/order, /api/signal/all/latest
"""
import sys
from pathlib import Path

# 确保 macro_api_server 所在目录(api/)在 sys.path 中
_api_dir = str(Path(__file__).resolve().parent.parent / "api")
_project_dir = str(Path(__file__).resolve().parent.parent)
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """创建测试客户端（懒加载 macro_api_server）"""
    from macro_api_server import app
    return TestClient(app)


# ==================== 风控路由测试 ====================

class TestRiskRoutes:
    """风控 API 路由测试"""

    def test_risk_status_returns_200(self, client):
        """GET /api/risk/status 应返回 200 且格式正确"""
        resp = client.get("/api/risk/status")
        assert resp.status_code == 200
        data = resp.json()
        # 统一响应格式：{code, message, data}
        assert "code" in data or "data" in data

    def test_risk_rules_returns_200(self, client):
        """GET /api/risk/rules 应返回 200"""
        resp = client.get("/api/risk/rules")
        assert resp.status_code == 200

    def test_risk_simulate_returns_200(self, client):
        """POST /api/risk/simulate 应返回 200"""
        payload = {
            "symbol": "RU",
            "direction": "LONG",
            "price": 15000.0,
            "volume": 1,
        }
        resp = client.post("/api/risk/simulate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "pass" in data["data"]

    def test_risk_kelly_returns_200(self, client):
        """POST /api/risk/kelly 应返回 200"""
        payload = {
            "symbol": "RU",
            "winRate": 0.55,
            "avgWin": 2000,
            "avgLoss": 1000,
            "capital": 500000,
        }
        resp = client.post("/api/risk/kelly", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data


# ==================== 交易路由测试 ====================

class TestTradingRoutes:
    """交易 API 路由测试"""

    def test_trading_positions_returns_200(self, client):
        """GET /api/trading/positions 应返回 200"""
        resp = client.get("/api/trading/positions")
        assert resp.status_code == 200

    def test_trading_account_returns_200(self, client):
        """GET /api/trading/account 应返回 200"""
        resp = client.get("/api/trading/account")
        assert resp.status_code == 200

    def test_trading_portfolio_returns_200(self, client):
        """GET /api/trading/portfolio 应返回 200"""
        resp = client.get("/api/trading/portfolio")
        assert resp.status_code == 200

    def test_trading_orders_returns_200(self, client):
        """GET /api/trading/orders 应返回 200"""
        resp = client.get("/api/trading/orders")
        assert resp.status_code == 200


# ==================== 信号路由测试 ====================

class TestSignalRoutes:
    """信号 API 路由测试"""

    def test_signal_all_latest_returns_200(self, client):
        """GET /api/signal/all/latest 应返回 200"""
        resp = client.get("/api/signal/all/latest")
        assert resp.status_code == 200

    def test_signal_all_summary_returns_200(self, client):
        """GET /api/signal/all/summary 应返回 200"""
        resp = client.get("/api/signal/all/summary")
        assert resp.status_code == 200
