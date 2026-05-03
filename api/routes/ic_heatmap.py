# api/routes/ic_heatmap.py
"""
IC 热力图 API 路由
提供因子-品种 IC 相关系数数据
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import date, datetime, timedelta

from macro_engine.core.analysis.ic_heatmap_service import IcHeatmapService

router = APIRouter(prefix="/api/ic-heatmap", tags=["ic-heatmap"])


def _wrap(data=None, message: str = "success", code: int = 0):
    """统一 API 响应格式：{code, message, data}"""
    return {"code": code, "message": message, "data": data}


# 初始化服务
ic_service = IcHeatmapService()


@router.get("/")
async def get_ic_heatmap(
    symbols: Optional[List[str]] = Query(None, description="品种代码列表（如 RU,ZN,RB,NI）"),
    as_of_date: Optional[date] = Query(None, description="截止日期（默认今天）"),
    lookback_days: int = Query(252, description="回溯期（默认252个交易日≈1年）")
):
    """
    获取 IC 热力图数据
    
    返回因子-品种的 Spearman IC 相关系数矩阵
    
    示例:
    ```
    GET /api/ic-heatmap/?symbols=RU&symbols=ZN&symbols=RB&lookback_days=252
    ```
    
    响应:
    ```json
    {
        "factors": ["factor1", "factor2", ...],
        "symbols": ["RU", "ZN", "RB"],
        "matrix": [[0.1, 0.2, ...], [-0.1, 0.3, ...], ...],
        "ir_matrix": [[0.5, 0.6, ...], ...],
        "significance": [[0.01, 0.05, ...], ...],
        "calc_date": "2026-04-27",
        "lookback_days": 252,
        "forward_period": 5
    }
    ```
    """
    try:
        # 默认品种
        if not symbols:
            symbols = ["RU", "ZN", "RB", "NI", "CU", "AL", "AU", "AG"]
            
        # 默认日期
        if as_of_date is None:
            as_of_date = date.today()
            
        # 获取热力图数据
        result = ic_service.get_heatmap_data(
            symbols=symbols,
            as_of_date=as_of_date,
            lookback_days=lookback_days
        )
        
        return _wrap(result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IC 计算错误: {str(e)}")


@router.get("/history/{factor_code}/{symbol}")
async def get_ic_history(
    factor_code: str,
    symbol: str,
    start_date: Optional[date] = Query(None, description="起始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    rolling_window: int = Query(20, description="滚动窗口（默认20日）")
):
    """
    获取单因子-单品种的 IC 历史走势
    
    示例:
    ```
    GET /api/ic-heatmap/history/factor1/RU?start_date=2026-01-01&end_date=2026-04-27
    ```
    
    响应:
    ```json
    {
        "status": "success",
        "data": {
            "dates": ["2026-01-01", ...],
            "ic_values": [0.1, 0.2, ...],
            "ic_ma": [0.15, 0.18, ...],
            "ir_values": [0.5, 0.6, ...],
            "factor_code": "factor1",
            "symbol": "RU",
            "rolling_window": 20
        }
    }
    ```
    """
    try:
        # 默认日期范围
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=90)
            
        # 获取历史数据
        result = ic_service.get_ic_history(
            factor_code=factor_code,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            rolling_window=rolling_window
        )
        
        return _wrap(result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IC 历史数据错误: {str(e)}")


@router.get("/factors")
async def get_available_factors(symbol: Optional[str] = Query(None, description="品种代码（如 RU）")):
    """获取可用的因子列表"""
    try:
        symbol_code = symbol  # 使用 query 参数
        factors = ic_service.get_factors(symbol=symbol_code)
        return _wrap({"factors": factors, "count": len(factors)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取因子列表错误: {str(e)}")


@router.get("/symbols")
async def get_available_symbols():
    """获取可用的品种列表"""
    # 预定义品种列表
    symbols = [
        {"code": "RU", "name": "天然橡胶", "exchange": "SHFE"},
        {"code": "ZN", "name": "沪锌", "exchange": "SHFE"},
        {"code": "RB", "name": "螺纹钢", "exchange": "SHFE"},
        {"code": "NI", "name": "沪镍", "exchange": "SHFE"},
        {"code": "CU", "name": "沪铜", "exchange": "SHFE"},
        {"code": "AL", "name": "沪铝", "exchange": "SHFE"},
        {"code": "AU", "name": "黄金", "exchange": "SHFE"},
        {"code": "AG", "name": "白银", "exchange": "SHFE"},
        {"code": "FU", "name": "燃料油", "exchange": "SHFE"},
        {"code": "BU", "name": "沥青", "exchange": "SHFE"}
    ]
    
    return _wrap({"symbols": symbols, "count": len(symbols)})
