#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FastAPI主应用 - 集成VNpyBridge

提供:
- REST API (持仓/账户/订单/策略/风控)
- WebSocket实时推送
- 健康检查
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 添加 macro_engine 路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'macro_engine'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routes import vnpy as vnpy_routes
from api.routes import trading as trading_routes
from api.routes import ic_heatmap as ic_routes
from api.routes import signal as signal_routes
from api.routes.circuit_breaker import router as circuit_breaker_router
from api.websocket.vnpy_ws import init_websocket
from services.vnpy_bridge import bridge


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时自动启动VNpy
    print("Starting VNpy engine...")
    bridge.start()
    
    yield
    
    # 关闭时停止VNpy
    print("Stopping VNpy engine...")
    bridge.stop()


# 创建FastAPI应用
app = FastAPI(
    title="期货智能交易系统 API",
    description="宏观基本面打分引擎 + VNpy交易执行",
    version="6.1.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(vnpy_routes.router)
app.include_router(trading_routes.router)
app.include_router(ic_routes.router)
app.include_router(signal_routes.router)
app.include_router(circuit_breaker_router)

# 初始化WebSocket
init_websocket(bridge, app)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "期货智能交易系统 API",
        "version": "6.1.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "vnpy_status": bridge.status.value,
        "is_running": bridge.status.value == "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
