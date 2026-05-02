from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import sys

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ic_heatmap.calculator import ICHeatmapCalculator
from signal_system.scoring import SignalScoringSystem

# 创建FastAPI应用
app = FastAPI(
    title="期货因子分析API",
    description="IC热力图与信号评分系统",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化计算器
ic_calculator = ICHeatmapCalculator()
signal_scoring = SignalScoringSystem()


# ============================================================
# 数据模型
# ============================================================

class ICHeatmapRequest(BaseModel):
    symbols: List[str] = ["JM", "RU", "RB", "ZN", "NI"]
    factors: Optional[List[str]] = None
    lookback: int = 60
    holdPeriod: int = 5


class ICHeatmapResponse(BaseModel):
    factors: List[str]
    symbols: List[str]
    icMatrix: List[List[float]]
    lookbackPeriod: int
    holdPeriod: int
    updatedAt: str


class SignalResponse(BaseModel):
    symbol: str
    compositeScore: float
    signalStrength: str
    confidence: float
    factorDetails: List[Dict[str, Any]]  # Lucy 要求：factorBreakdown → factorDetails
    regime: str
    timestamp: str


class BatchSignalResponse(BaseModel):
    signals: List[SignalResponse]
    count: int
    updatedAt: str


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


# ============================================================
# API端点
# ============================================================

@app.get("/", response_model=HealthResponse)
async def root():
    """健康检查"""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=datetime.now().isoformat() + "Z"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=datetime.now().isoformat() + "Z"
    )


# ============================================================
# IC热力图API
# ============================================================

@app.get("/api/ic/heatmap", response_model=ICHeatmapResponse)
async def get_ic_heatmap(
    symbols: str = Query("JM,RU,RB,ZN,NI", description="品种列表，逗号分隔"),
    lookback: int = Query(60, description="回看天数"),
    hold_period: int = Query(5, description="持有期天数")
):
    """
    获取IC热力图
    
    计算多品种多因子的IC矩阵，使用Spearman相关系数
    """
    try:
        # 解析品种列表
        symbol_list = [s.strip() for s in symbols.split(",")]
        
        # 计算IC矩阵
        result = ic_calculator.compute_ic_matrix(
            symbols=symbol_list,
            factors=ic_calculator.default_factors,
            lookback=lookback,
            hold_period=hold_period
        )
        
        return ICHeatmapResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ic/heatmap", response_model=ICHeatmapResponse)
async def post_ic_heatmap(request: ICHeatmapRequest):
    """
    获取IC热力图（POST方式）
    
    支持自定义因子列表
    """
    try:
        factors = request.factors if request.factors else ic_calculator.default_factors
        
        result = ic_calculator.compute_ic_matrix(
            symbols=request.symbols,
            factors=factors,
            lookback=request.lookback,
            hold_period=request.holdPeriod
        )
        
        return ICHeatmapResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ic/heatmap/optimal", response_model=ICHeatmapResponse)
async def get_ic_heatmap_optimal(
    symbols: str = Query("JM,RU,RB,ZN,NI", description="品种列表，逗号分隔")
):
    """
    使用最优参数获取IC热力图
    """
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        
        result = ic_calculator.compute_heatmap_with_optimal_params(
            symbols=symbol_list
        )
        
        return ICHeatmapResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 信号系统API
# ============================================================

@app.get("/api/signal/{symbol}", response_model=SignalResponse)
async def get_signal(symbol: str):
    """
    获取品种信号评分
    
    返回综合评分、信号强度、置信度等信息
    """
    try:
        result = signal_scoring.compute_signal_score(symbol.upper())
        return SignalResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/signal", response_model=BatchSignalResponse)
async def get_batch_signals(
    symbols: str = Query("JM,RU,RB,ZN,NI", description="品种列表，逗号分隔")
):
    """
    批量获取信号评分
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        
        signals = signal_scoring.batch_compute_signals(symbol_list)
        
        return BatchSignalResponse(
            signals=[SignalResponse(**s) for s in signals],
            count=len(signals),
            updatedAt=datetime.now().isoformat() + "Z"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 启动服务
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("期货因子分析API服务")
    print("=" * 80)
    print("\n端点列表:")
    print("  GET  /                    - 健康检查")
    print("  GET  /health              - 健康检查")
    print("  GET  /api/ic/heatmap      - IC热力图")
    print("  POST /api/ic/heatmap      - IC热力图(POST)")
    print("  GET  /api/ic/heatmap/optimal - 最优参数IC热力图")
    print("  GET  /api/signal/{symbol} - 信号评分")
    print("  GET  /api/signal          - 批量信号评分")
    print("\n" + "=" * 80)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)
