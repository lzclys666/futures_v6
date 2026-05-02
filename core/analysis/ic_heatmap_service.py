# core/analysis/ic_heatmap_service.py
"""
IC 热力图计算服务（Stub）
TODO: 实现真实 IC 计算
"""
from typing import List, Optional, Dict, Any
from datetime import date
import random


class IcHeatmapService:
    """IC 热力图服务 Stub - 返回 Mock 数据供前端开发"""
    
    # Mock 因子列表
    MOCK_FACTORS = [
        "RU_CFTC_NC",
        "RU_INV_WEEKLY",
        "RU_SPREAD_CRB",
        "RU_FX_USDCNY",
        "RU_macro_sentiment",
    ]
    
    def get_heatmap_data(
        self,
        symbols: List[str],
        as_of_date: date,
        lookback_days: int = 252
    ) -> Dict[str, Any]:
        """返回 Mock IC 热力图数据"""
        factors = self.MOCK_FACTORS
        
        # 生成 Mock IC 矩阵（-0.3 到 0.3 之间）
        matrix = []
        ir_matrix = []
        significance = []
        
        for factor in factors:
            row_ic = []
            row_ir = []
            row_sig = []
            for symbol in symbols:
                ic = random.uniform(-0.3, 0.3)
                ir = ic * random.uniform(2, 5)  # IR ≈ IC * sqrt(N)
                sig = 0.05 if abs(ic) > 0.1 else 0.1 if abs(ic) > 0.05 else 0.5
                
                row_ic.append(round(ic, 3))
                row_ir.append(round(ir, 3))
                row_sig.append(round(sig, 3))
            
            matrix.append(row_ic)
            ir_matrix.append(row_ir)
            significance.append(row_sig)
        
        return {
            "factors": factors,
            "symbols": symbols,
            "matrix": matrix,
            "ir_matrix": ir_matrix,
            "significance": significance,
            "calc_date": as_of_date.isoformat(),
            "lookback_days": lookback_days,
            "forward_period": 5,
        }
    
    def get_ic_history(
        self,
        factor_code: str,
        symbol: str,
        start_date: date,
        end_date: date,
        rolling_window: int = 20
    ) -> Dict[str, Any]:
        """返回 Mock IC 历史数据"""
        from datetime import timedelta
        
        # 生成日期序列
        days = (end_date - start_date).days
        dates = []
        ic_values = []
        ic_ma = []
        
        current = start_date
        ic_buffer = []
        
        while current <= end_date:
            dates.append(current.isoformat())
            ic = random.uniform(-0.2, 0.2)
            ic_values.append(round(ic, 3))
            
            # 滚动平均
            ic_buffer.append(ic)
            if len(ic_buffer) > rolling_window:
                ic_buffer.pop(0)
            ic_ma.append(round(sum(ic_buffer) / len(ic_buffer), 3))
            
            current += timedelta(days=1)
        
        return {
            "dates": dates,
            "ic_values": ic_values,
            "ic_ma": ic_ma,
            "ir_values": [round(ic * 3, 3) for ic in ic_values],
            "factor_code": factor_code,
            "symbol": symbol,
            "rolling_window": rolling_window,
        }
    
    def get_factors(self) -> List[Dict[str, Any]]:
        """返回可用因子列表"""
        return [
            {"factor_code": f, "factor_name": f.replace("RU_", "").replace("_", " "), "category": "macro"}
            for f in self.MOCK_FACTORS
        ]
    
    def get_symbols(self) -> List[str]:
        """返回可用品种列表"""
        return ["RU", "ZN", "RB", "NI", "CU", "AL", "AU", "AG"]