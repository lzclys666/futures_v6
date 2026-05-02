# api/routes/signal.py
"""
信号系统 API 路由
提供宏观信号查询、历史信号、信号统计等接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from pathlib import Path
import logging

# PitDataService 暂未实现，移除导入
# from core.data.pit_service import PitDataService

router = APIRouter(prefix="/api/signal", tags=["signal"])

# 懒加载 SignalBridge（避免启动时依赖）
_signal_bridge = None

def get_signal_bridge():
    """获取 SignalBridge 实例（懒加载）"""
    global _signal_bridge
    if _signal_bridge is None:
        try:
            from services.signal_bridge import SignalBridge
            # 尝试从 macro_api_server 获取 vnpy_bridge
            import sys
            from pathlib import Path
            api_dir = Path(__file__).parent.parent
            if str(api_dir) not in sys.path:
                sys.path.insert(0, str(api_dir))
            
            # 导入 get_vnpy_bridge
            try:
                # 尝试从父模块获取
                import importlib
                parent_module = importlib.import_module("macro_api_server")
                if hasattr(parent_module, "get_vnpy_bridge"):
                    vnpy_bridge = parent_module.get_vnpy_bridge()
                else:
                    vnpy_bridge = None
            except ImportError:
                vnpy_bridge = None
            
            if vnpy_bridge and hasattr(vnpy_bridge, 'event_engine'):
                _signal_bridge = SignalBridge(vnpy_bridge.event_engine, "D:/futures_v6/macro_engine/output")
            else:
                # 无 event_engine 时使用 None（仅文件轮询）
                _signal_bridge = SignalBridge(None, "D:/futures_v6/macro_engine/output")
        except Exception as e:
            logging.getLogger("signal_api").warning(f"SignalBridge init failed: {e}")
    return _signal_bridge


def _parse_csv_signal(csv_path: Path) -> Optional[Dict[str, Any]]:
    """解析单个 CSV 文件，提取 SUMMARY 行和 FACTOR 行"""
    import csv
    if not csv_path.exists():
        return None

    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return None

        # Helper: get value from row supporting both camelCase and snake_case
        def _g(row: dict, camel: str, snake: str, default=""):
            return row.get(camel, row.get(snake, default))

        # Helper: get float value safely
        def _gf(row: dict, camel: str, snake: str, default=0.0):
            val = row.get(camel, row.get(snake, default))
            if val is None or val == "":
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        # 查找 SUMMARY 行
        summary_row = None
        factors = []
        for row in rows:
            row_type = _g(row, "rowType", "row_type", "")
            if row_type == "SUMMARY":
                summary_row = row
            elif row_type in ("DETAIL", "FACTOR"):
                factors.append({
                    "factorCode": _g(row, "factorCode", "factor_code", f"factor_{len(factors)+1}"),
                    "factorName": _g(row, "factorName", "factor_name", _g(row, "factorCode", "factor_code", f"Factor {len(factors)+1}")),
                    "rawValue": _gf(row, "rawValue", "raw_value"),
                    "normalizedScore": _gf(row, "normalizedScore", "normalized_score"),
                    "weight": _gf(row, "weight", "weight", 0.1) if _g(row, "weight", "weight") else 0.1,
                    "contribution": _gf(row, "contribution", "contribution"),
                    "contributionPolarity": _g(row, "contributionPolarity", "contribution_polarity", "neutral").lower(),
                    "icValue": _gf(row, "icValue", "ic_value", 0) if _g(row, "icValue", "ic_value") else None,
                })

        if summary_row:
            score = _gf(summary_row, "compositeScore", "composite_score")
            
            return {
                "symbol": _g(summary_row, "symbol", "symbol", ""),
                "date": csv_path.stem.split("_")[-1],  # 从文件名提取日期
                "direction": _g(summary_row, "direction", "direction", "NEUTRAL"),
                "score": score,
                "confidence": _g(summary_row, "confidence", "confidence", "MEDIUM"),
                "factorCount": int(_gf(summary_row, "factorCount", "factor_count")),
                "updatedAt": _g(summary_row, "updatedAt", "updated_at", ""),
                "engineVersion": _g(summary_row, "engineVersion", "engine_version", ""),
                "factors": factors,
                "source_file": str(csv_path),
                "updated_at": datetime.now().isoformat(),
            }
        return None
    except Exception as e:
        logging.getLogger("signal_api").error(f"Parse CSV error {csv_path}: {e}")
        return None


def _scan_all_signals() -> Dict[str, Any]:
    """Scan directory for all symbols latest signal"""
    output_dir = Path("D:/futures_v6/macro_engine/output")
    if not output_dir.exists():
        return {}
    
    # Find all symbols (skip composite ones with commas)
    symbols = set()
    for csv_file in output_dir.glob("*_macro_daily_*.csv"):
        name = csv_file.name
        symbol_part = name.replace("_macro_daily_", "_")  # XXX_YYYYMMDD.csv
        symbol = symbol_part.split("_")[0]  # XXX
        # Skip composite symbols like "AU,AG,CU,RU"
        if "," not in symbol:
            symbols.add(symbol)
    
    # 获取每个品种的最新信号
    all_signals = {}
    for symbol in symbols:
        csv_files = sorted(
            output_dir.glob(f"{symbol}_macro_daily_*.csv"),
            reverse=True
        )
        if csv_files:
            signal = _parse_csv_signal(csv_files[0])
            if signal:
                all_signals[symbol] = signal
    
    return all_signals


@router.get("/{symbol}")
async def get_signal(symbol: str):
    """
    获取指定品种的最新宏观信号
    
    示例:
    ```
    GET /api/signal/RU
    ```
    
    响应:
    ```json
    {
        "status": "success",
        "data": {
            "symbol": "RU",
            "date": "2026-04-27",
            "direction": "LONG",
            "score": 0.35,
            "confidence": "HIGH",
            "factors": [
                {
                    "factorCode": "RU_CFTC_NC",
                    "factorName": "CFTC非商业净持仓",
                    "rawValue": 12345.0,
                    "normalizedScore": 0.8,
                    "weight": 0.15,
                    "contribution": 0.12,
                    "contributionPolarity": "positive",
                    "icValue": 0.05
                }
            ],
            "source_file": "D:/futures_v6/macro_engine/output/RU_macro_daily_20260427.csv",
            "updated_at": "2026-04-27T00:00:00+08:00"
        }
    }
    ```
    """
    try:
        bridge = get_signal_bridge()
        signal = bridge.get_latest_signal(symbol.upper())
        
        if signal is None:
            # 尝试直接读取 CSV 文件
            csv_path = Path(f"D:/futures_v6/macro_engine/output/{symbol.upper()}_macro_daily_{date.today().strftime('%Y%m%d')}.csv")
            if csv_path.exists():
                signal = _parse_csv_signal(csv_path)
            else:
                # 查找最新的 CSV 文件
                output_dir = Path("D:/futures_v6/macro_engine/output")
                if output_dir.exists():
                    csv_files = sorted(output_dir.glob(f"{symbol.upper()}_macro_daily_*.csv"), reverse=True)
                    if csv_files:
                        signal = _parse_csv_signal(csv_files[0])
        
        if signal is None:
            raise HTTPException(status_code=404, detail=f"未找到品种 {symbol} 的信号数据")
            
        return {
            "status": "success",
            "data": signal
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取信号错误: {str(e)}")


@router.get("/{symbol}/direction")
async def get_signal_direction(symbol: str):
    """
    获取指定品种的宏观方向（简化接口）
    
    示例:
    ```
    GET /api/signal/RU/direction
    ```
    
    响应:
    ```json
    {
        "status": "success",
        "data": {
            "symbol": "RU",
            "direction": "LONG",
            "score": 0.35,
            "confidence": "HIGH",
            "timestamp": "2026-04-27T00:00:00"
        }
    }
    ```
    """
    try:
        bridge = get_signal_bridge()
        direction = bridge.get_latest_direction(symbol.upper())
        score = bridge.get_latest_score(symbol.upper())
        
        # 如果缓存为空，尝试直接读取 CSV
        if direction is None:
            csv_path = Path(f"D:/futures_v6/macro_engine/output/{symbol.upper()}_macro_daily_{date.today().strftime('%Y%m%d')}.csv")
            if not csv_path.exists():
                # 查找最新的 CSV 文件
                output_dir = Path("D:/futures_v6/macro_engine/output")
                if output_dir.exists():
                    csv_files = sorted(output_dir.glob(f"{symbol.upper()}_macro_daily_*.csv"), reverse=True)
                    if csv_files:
                        csv_path = csv_files[0]
            
            if csv_path.exists():
                signal = _parse_csv_signal(csv_path)
                if signal:
                    direction = signal.get("direction", "NEUTRAL")
                    score = signal.get("score", 0.0)
        
        if direction is None:
            raise HTTPException(status_code=404, detail=f"未找到品种 {symbol} 的方向数据")
            
        return {
            "status": "success",
            "data": {
                "symbol": symbol.upper(),
                "direction": direction,
                "score": score,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取方向错误: {str(e)}")


@router.get("/{symbol}/history")
async def get_signal_history(
    symbol: str,
    start_date: Optional[date] = Query(None, description="起始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(30, description="返回条数限制")
):
    """
    获取指定品种的历史信号
    
    示例:
    ```
    GET /api/signal/RU/history?start_date=2026-04-01&end_date=2026-04-27&limit=30
    ```
    
    响应:
    ```json
    {
        "status": "success",
        "data": {
            "symbol": "RU",
            "history": [
                {
                    "date": "2026-04-27",
                    "direction": "LONG",
                    "score": 0.35,
                    "confidence": "HIGH"
                },
                {
                    "date": "2026-04-26",
                    "direction": "NEUTRAL",
                    "score": 0.05,
                    "confidence": "LOW"
                }
            ],
            "count": 2
        }
    }
    ```
    """
    try:
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
            
        output_dir = Path("D:/futures_v6/macro_engine/output")
        history = []
        
        if output_dir.exists():
            # 查找日期范围内的 CSV 文件
            current_date = end_date
            while current_date >= start_date and len(history) < limit:
                csv_path = output_dir / f"{symbol.upper()}_macro_daily_{current_date.strftime('%Y%m%d')}.csv"
                if csv_path.exists():
                    signal = _parse_csv_signal(csv_path)
                    if signal:
                        history.append({
                            "date": signal.get("date", current_date.isoformat()),
                            "direction": signal.get("direction", "NEUTRAL"),
                            "score": signal.get("score", 0.0),
                            "confidence": signal.get("confidence", "MEDIUM")
                        })
                current_date -= timedelta(days=1)
                
        return {
            "status": "success",
            "data": {
                "symbol": symbol.upper(),
                "history": history,
                "count": len(history),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史信号错误: {str(e)}")


@router.get("/{symbol}/factors")
async def get_signal_factors(symbol: str):
    """
    获取指定品种的最新因子明细
    
    示例:
    ```
    GET /api/signal/RU/factors
    ```
    
    响应:
    ```json
    {
        "status": "success",
        "data": {
            "symbol": "RU",
            "date": "2026-04-27",
            "factors": [
                {
                    "factorCode": "RU_CFTC_NC",
                    "factorName": "CFTC非商业净持仓",
                    "rawValue": 12345.0,
                    "normalizedScore": 0.8,
                    "weight": 0.15,
                    "contribution": 0.12,
                    "contributionPolarity": "positive",
                    "icValue": 0.05
                }
            ],
            "factor_count": 1
        }
    }
    ```
    """
    try:
        bridge = get_signal_bridge()
        signal = bridge.get_latest_signal(symbol.upper())
        
        if signal is None:
            # 尝试直接读取 CSV
            csv_path = Path(f"D:/futures_v6/macro_engine/output/{symbol.upper()}_macro_daily_{date.today().strftime('%Y%m%d')}.csv")
            if not csv_path.exists():
                # 查找最新的 CSV 文件
                output_dir = Path("D:/futures_v6/macro_engine/output")
                if output_dir.exists():
                    csv_files = sorted(output_dir.glob(f"{symbol.upper()}_macro_daily_*.csv"), reverse=True)
                    if csv_files:
                        csv_path = csv_files[0]
            
            if csv_path.exists():
                signal = _parse_csv_signal(csv_path)
            
        if signal is None:
            raise HTTPException(status_code=404, detail=f"未找到品种 {symbol} 的因子数据")
            
        factors = signal.get("factors", [])
        
        return {
            "status": "success",
            "data": {
                "symbol": symbol.upper(),
                "date": signal.get("date", ""),
                "factors": factors,
                "factor_count": len(factors)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取因子明细错误: {str(e)}")


@router.get("/all/latest")
async def get_all_latest_signals():
    """
    获取所有品种的最新信号
    
    示例:
    ```
    GET /api/signal/all/latest
    ```
    
    响应:
    ```json
    {
        "status": "success",
        "data": {
            "signals": [
                {
                    "symbol": "RU",
                    "direction": "LONG",
                    "score": 0.35,
                    "confidence": "HIGH"
                },
                {
                    "symbol": "ZN",
                    "direction": "SHORT",
                    "score": -0.28,
                    "confidence": "MEDIUM"
                }
            ],
            "count": 2,
            "timestamp": "2026-04-27T00:00:00"
        }
    }
    ```
    """
    try:
        # 扫描目录获取所有品种最新信号
        all_signals = _scan_all_signals()
        
        # 如果目录无数据，尝试缓存
        if not all_signals:
            bridge = get_signal_bridge()
            all_signals = bridge.get_all_signals()
        
        # 转换为列表格式
        signals_list = []
        for symbol, signal in all_signals.items():
            signals_list.append({
                "symbol": symbol,
                "direction": signal.get("direction", "NEUTRAL"),
                "score": signal.get("score", 0.0),
                "confidence": signal.get("confidence", "MEDIUM"),
                "date": signal.get("date", ""),
                "factorCount": signal.get("factorCount", len(signal.get("factors", []))),
                "factors": signal.get("factors", []),
                "updatedAt": signal.get("updatedAt", ""),
            })
            
        # 按分数绝对值排序
        signals_list.sort(key=lambda x: abs(x["score"]), reverse=True)
        
        return {
            "status": "success",
            "data": {
                "signals": signals_list,
                "count": len(signals_list),
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取所有信号错误: {str(e)}")


@router.get("/all/summary")
async def get_signals_summary():
    """
    获取信号汇总统计
    
    示例:
    ```
    GET /api/signal/all/summary
    ```
    
    响应:
    ```json
    {
        "status": "success",
        "data": {
            "total_symbols": 10,
            "long_count": 3,
            "short_count": 2,
            "neutral_count": 5,
            "avg_score": 0.05,
            "max_score": 0.45,
            "min_score": -0.32,
            "timestamp": "2026-04-27T00:00:00"
        }
    }
    ```
    """
    try:
        # 扫描目录获取所有品种最新信号
        all_signals = _scan_all_signals()
        
        # 如果目录无数据，尝试缓存
        if not all_signals:
            bridge = get_signal_bridge()
            all_signals = bridge.get_all_signals()
        
        if not all_signals:
            return {
                "status": "success",
                "data": {
                    "total_symbols": 0,
                    "long_count": 0,
                    "short_count": 0,
                    "neutral_count": 0,
                    "avg_score": 0.0,
                    "max_score": 0.0,
                    "min_score": 0.0,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        scores = [s.get("score", 0.0) for s in all_signals.values()]
        directions = [s.get("direction", "NEUTRAL") for s in all_signals.values()]
        
        return {
            "status": "success",
            "data": {
                "total_symbols": len(all_signals),
                "long_count": directions.count("LONG"),
                "short_count": directions.count("SHORT"),
                "neutral_count": directions.count("NEUTRAL"),
                "avg_score": sum(scores) / len(scores) if scores else 0.0,
                "max_score": max(scores) if scores else 0.0,
                "min_score": min(scores) if scores else 0.0,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取信号汇总错误: {str(e)}")
