# api/routes/strategy.py
"""
策略管理 API 路由

端点：
- GET /api/strategy/list        — 策略列表（含元数据）
- GET /api/strategy/bindings    — 品种→策略绑定
- GET /api/strategy/validate    — 校验绑定配置
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


def _get_registry():
    """延迟导入注册中心（避免循环依赖）"""
    from core.strategy_registry import get_registry
    return get_registry()


@router.get("/list")
async def list_strategies():
    """返回所有已发现的策略类"""
    registry = _get_registry()
    if registry is None:
        return {"error": "StrategyRegistry 未初始化", "strategies": []}
    strategies = registry.list_strategies()
    return {
        "count": len(strategies),
        "strategies": strategies,
    }


@router.get("/bindings")
async def list_bindings():
    """返回品种→策略绑定"""
    registry = _get_registry()
    if registry is None:
        return {"error": "StrategyRegistry 未初始化", "bindings": {}}
    bindings = registry.get_bindings()
    enabled = registry.get_enabled_bindings()
    return {
        "total": len(bindings),
        "enabled": len(enabled),
        "bindings": bindings,
    }


@router.get("/validate")
async def validate_bindings():
    """校验绑定配置（策略类是否都存在）"""
    registry = _get_registry()
    if registry is None:
        return {"error": "StrategyRegistry 未初始化", "valid": False}
    errors = registry.validate_bindings()
    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }
