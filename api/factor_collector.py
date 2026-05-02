"""
因子数据采集主脚本
==================
读取 factor_requirements.json，按优先级顺序批量采集因子数据

用法：
    python factor_collector.py factor_requirements.json

输出：
    - 数据文件：data/raw_factors/{品种代码}/{因子代码}.csv
    - 摘要文件：data/collection_summary_{task_id}.json
    - 错误日志：logs/collection_errors_{task_id}.log
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import traceback
import pandas as pd

# 添加采集器模块路径
sys.path.append(str(Path(__file__).parent / "collectors"))

from akshare_collector import collect_akshare
from tushare_collector import collect_tushare
from custom_collector import collect_custom
from wind_collector import collect_wind
from joinquant_collector import collect_joinquant
from uqer_collector import collect_uqer
from exchange_crawler import collect_exchange


class FactorCollector:
    """因子数据采集器"""
    
    # 数据源到采集函数的映射
    COLLECTOR_MAP = {
        "akshare": collect_akshare,
        "tushare": collect_tushare,
        "custom": collect_custom,
        "wind": collect_wind,
        "joinquant": collect_joinquant,
        "uqer": collect_uqer,
        "exchange": collect_exchange,
    }
    
    def __init__(self, requirements_path: str):
        """初始化采集器
        
        Args:
            requirements_path: factor_requirements.json 文件路径
        """
        self.requirements_path = Path(requirements_path)
        self.requirements = self._load_requirements()
        self.task_id = self.requirements["task_info"]["task_id"]
        self.results = {
            "success": [],
            "failed": [],
            "skipped": []
        }
        self.start_time = datetime.now()
        
        # 创建必要的目录
        self._ensure_directories()
    
    def _load_requirements(self) -> Dict[str, Any]:
        """加载需求文件"""
        # 如果路径为空或不存在，返回默认结构
        path_str = str(self.requirements_path)
        if not path_str or path_str == "." or not self.requirements_path.exists():
            return {
                "task_info": {"task_id": f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"},
                "factors": [],
                "execution_order": [],
                "global_config": {}
            }
        with open(self.requirements_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _ensure_directories(self):
        """确保输出目录存在"""
        Path("data/raw_factors").mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(parents=True, exist_ok=True)
    
    def run(self) -> Dict[str, Any]:
        """执行采集任务
        
        Returns:
            采集结果摘要
        """
        execution_order = self.requirements.get("execution_order", [])
        factors_dict = {f["factor_code"]: f for f in self.requirements["factors"]}
        global_config = self.requirements.get("global_config", {})
        
        print(f"[启动] 任务 {self.task_id}，共 {len(execution_order)} 个因子")
        
        # 按顺序采集
        for i, factor_code in enumerate(execution_order, 1):
            factor = factors_dict.get(factor_code)
            if not factor:
                self._log_error(f"因子 {factor_code} 未在 factors 中定义")
                self.results["skipped"].append({
                    "factor_code": factor_code,
                    "reason": "未定义"
                })
                continue
            
            print(f"[{i}/{len(execution_order)}] 采集 {factor_code}...")
            
            # 执行采集
            success = self._collect_factor(factor, global_config)
            
            if success:
                self.results["success"].append(factor_code)
            else:
                self.results["failed"].append(factor_code)
                # 如果配置了遇错停止
                if global_config.get("stop_on_error", False):
                    print(f"[停止] 因子 {factor_code} 失败，停止后续采集")
                    break
        
        # 生成摘要
        summary = self._generate_summary()
        self._save_summary(summary)
        
        return summary
    
    def collect_single(self, factor: Dict[str, Any], global_config: Dict[str, Any] = None) -> pd.DataFrame:
        """采集单个因子（用于演示和测试）
        
        Args:
            factor: 因子配置
            global_config: 全局配置（可选）
            
        Returns:
            采集到的数据 DataFrame，失败返回 None
        """
        if global_config is None:
            global_config = {}
        
        factor_code = factor.get("factor_code", "UNKNOWN")
        data_source = factor.get("data_source")
        
        if not data_source:
            raise ValueError("因子配置缺少 data_source 字段")
        
        # 获取采集函数
        collector_func = self.COLLECTOR_MAP.get(data_source)
        if not collector_func:
            raise ValueError(f"不支持的数据源: {data_source}")
        
        # 直接调用采集函数
        return collector_func(factor)
    
    def collect_batch(self, factors: List[Dict[str, Any]], global_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """批量采集多个因子（用于演示和测试）
        
        Args:
            factors: 因子配置列表
            global_config: 全局配置（可选）
            
        Returns:
            采集结果摘要 {"success": [...], "failed": [...], "data": {...}}
        """
        if global_config is None:
            global_config = {}
        
        results = {
            "success": [],
            "failed": [],
            "data": {}
        }
        
        print(f"开始批量采集，共 {len(factors)} 个因子")
        
        for i, factor in enumerate(factors):
            factor_code = factor.get("factor_code", f"factor_{i}")
            print(f"\n[{i+1}/{len(factors)}] 采集 {factor_code}...")
            
            try:
                df = self.collect_single(factor, global_config)
                if df is not None and not df.empty:
                    results["success"].append(factor_code)
                    results["data"][factor_code] = {
                        "shape": df.shape,
                        "columns": list(df.columns)
                    }
                    print(f"  [OK] 成功，数据形状: {df.shape}")
                else:
                    results["failed"].append(factor_code)
                    print(f"  [FAIL] 返回空数据")
            except Exception as e:
                results["failed"].append(factor_code)
                print(f"  [FAIL] 失败: {str(e)}")
        
        print(f"\n批量采集完成: 成功 {len(results['success'])}, 失败 {len(results['failed'])}")
        return results
    
    def _collect_factor(self, factor: Dict[str, Any], global_config: Dict[str, Any]) -> bool:
        """采集单个因子
        
        Args:
            factor: 因子配置
            global_config: 全局配置
            
        Returns:
            是否成功
        """
        factor_code = factor["factor_code"]
        data_source = factor["data_source"]
        retry_config = factor.get("retry_config", {})
        
        # 获取采集函数
        collector_func = self.COLLECTOR_MAP.get(data_source)
        if not collector_func:
            self._log_error(f"因子 {factor_code}：不支持的数据源 {data_source}")
            return False
        
        # 重试逻辑
        max_retries = retry_config.get("max_retries", 3)
        retry_interval = retry_config.get("retry_interval_sec", 60)
        
        for attempt in range(max_retries):
            try:
                # 调用采集函数
                data = collector_func(factor)
                
                # 保存数据
                output_path = self._save_data(data, factor)
                
                print(f"  ✓ 成功 -> {output_path}")
                return True
                
            except Exception as e:
                error_msg = f"因子 {factor_code} 第 {attempt + 1} 次尝试失败: {str(e)}"
                self._log_error(error_msg)
                
                if attempt < max_retries - 1:
                    print(f"  ⚠ 失败，{retry_interval}秒后重试...")
                    import time
                    time.sleep(retry_interval)
                else:
                    # 达到最大重试次数
                    fallback = retry_config.get("fallback_strategy", "skip_and_log")
                    print(f"  ✗ 失败（策略：{fallback}）")
                    return False
        
        return False
    
    def _save_data(self, data: Any, factor: Dict[str, Any]) -> str:
        """保存采集的数据
        
        Args:
            data: 采集到的数据
            factor: 因子配置
            
        Returns:
            输出文件路径
        """
        import pandas as pd
        
        output_config = factor.get("output_config", {})
        output_dir = output_config.get("output_path", f"data/raw_factors/{factor['commodity']}/")
        filename = f"{factor['factor_code']}.csv"
        output_path = Path(output_dir) / filename
        
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为 DataFrame 并保存
        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame([data])
        
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        
        return str(output_path)
    
    def _log_error(self, message: str):
        """记录错误日志"""
        log_path = Path(f"logs/collection_errors_{self.task_id}.log")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """生成采集摘要"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        summary = {
            "task_id": self.task_id,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_sec": round(duration, 2),
            "total_factors": len(self.requirements.get("execution_order", [])),
            "success_count": len(self.results["success"]),
            "failed_count": len(self.results["failed"]),
            "skipped_count": len(self.results["skipped"]),
            "success_factors": self.results["success"],
            "failed_factors": self.results["failed"],
            "skipped_factors": self.results["skipped"],
            "status": "success" if len(self.results["failed"]) == 0 else "partial_failure"
        }
        
        return summary
    
    def _save_summary(self, summary: Dict[str, Any]):
        """保存摘要文件"""
        output_config = self.requirements.get("global_config", {})
        summary_path = output_config.get(
            "output_summary_to",
            f"data/collection_summary_{self.task_id}.json"
        )
        
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n[完成] 摘要已保存: {summary_path}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python factor_collector.py <requirements.json>")
        sys.exit(1)
    
    requirements_path = sys.argv[1]
    
    if not Path(requirements_path).exists():
        print(f"错误: 文件不存在 {requirements_path}")
        sys.exit(1)
    
    collector = FactorCollector(requirements_path)
    summary = collector.run()
    
    # 输出极简摘要（用于 token 节省）
    print("\n" + "="*50)
    print(f"✅ 采集完成")
    print(f"  - 成功: {summary['success_count']} 因子")
    print(f"  - 失败: {summary['failed_count']} 因子")
    print(f"  - 耗时: {summary['duration_sec']} 秒")
    print("="*50)


if __name__ == "__main__":
    main()
