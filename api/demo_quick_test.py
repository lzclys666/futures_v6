#!/usr/bin/env python3
"""
快速演示测试脚本
=================
使用 AKShare 快速验证采集器功能

运行：
    python demo_quick_test.py
"""

import sys
from pathlib import Path
import json

# 添加采集器模块路径
sys.path.append(str(Path(__file__).parent))

from factor_collector import FactorCollector


def create_demo_factor():
    """创建演示用的因子配置"""
    factor = {
        "factor_code": "RU_DEMO",
        "factor_name": "橡胶期货演示数据",
        "description": "AKShare 橡胶合约日线数据演示",
        "data_source": "akshare",
        "api_params": {
            "function": "futures_zh_daily_sina",
            "symbol": "ru2505"
        },
        "pit_requirement": {
            "need_pit": False,
            "source_type": "spot"
        },
        "expected_columns": ["date", "open", "high", "low", "close", "volume"],
        "frequency": "daily"
    }
    
    return factor


def run_quick_test():
    """运行快速测试"""
    print("快速演示测试 - AKShare 数据源")
    print("=" * 60)
    
    # 创建收集器（传入空路径）
    collector = FactorCollector("")
    
    # 创建因子配置
    factor = create_demo_factor()
    
    print(f"测试因子: {factor['factor_name']} ({factor['factor_code']})")
    print(f"数据源: {factor['data_source']}")
    print(f"API 函数: {factor['api_params']['function']}")
    print()
    
    try:
        # 执行采集
        print("开始采集...")
        df = collector.collect_single(factor)
        
        if df is None or df.empty:
            print("[FAIL] 采集失败：返回空数据")
            return False
        
        print(f"[OK] 采集成功")
        print(f"   数据形状: {df.shape}")
        print(f"   列名: {list(df.columns)}")
        
        # 显示前几行数据
        print(f"   前 3 行数据:")
        print(df.head(3).to_string(index=False))
        
        # 显示基本统计
        print(f"   基本统计:")
        if "close" in df.columns:
            print(f"     收盘价范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
            print(f"     成交量范围: {df['volume'].min():,.0f} - {df['volume'].max():,.0f}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 采集失败: {str(e)}")
        return False


def test_batch_collection():
    """测试批量采集"""
    print("\n" + "=" * 60)
    print("测试批量采集...")
    print("=" * 60)
    
    # 创建包含多个因子的需求文件
    factor_requirements = {
        "project": {
            "name": "快速演示项目",
            "version": "1.0.0",
            "description": "批量采集演示",
            "date": "2026-04-16"
        },
        "factor_groups": [
            {
                "group_name": "期货演示组",
                "group_description": "期货主力合约数据",
                "data_dir": "demo_data",
                "factors": [
                    {
                        "factor_code": "RU_DEMO",
                        "factor_name": "橡胶合约",
                        "description": "橡胶期货合约数据",
                        "data_source": "akshare",
                        "api_params": {
                            "function": "futures_zh_daily_sina",
                            "symbol": "ru2505"
                        },
                        "pit_requirement": {"need_pit": False},
                        "expected_columns": ["date", "open", "high", "low", "close", "volume"],
                        "frequency": "daily"
                    },
                    {
                        "factor_code": "CU_DEMO",
                        "factor_name": "铜合约",
                        "description": "铜期货合约数据",
                        "data_source": "akshare",
                        "api_params": {
                            "function": "futures_zh_daily_sina",
                            "symbol": "cu2505"
                        },
                        "pit_requirement": {"need_pit": False},
                        "expected_columns": ["date", "open", "high", "low", "close", "volume"],
                        "frequency": "daily"
                    }
                ]
            }
        ],
        "collection_settings": {
            "max_retries": 2,
            "timeout": 60,
            "log_dir": "demo_logs",
            "error_handling": "continue",
            "concurrent": False
        }
    }
    
    # 从 factor_requirements 中提取因子列表
    factors = factor_requirements['factor_groups'][0]['factors']
    
    # 创建收集器（传入空路径）
    collector = FactorCollector("")
    
    # 设置保存目录
    output_dir = Path("demo_output")
    output_dir.mkdir(exist_ok=True)
    
    print(f"输出目录: {output_dir.absolute()}")
    print(f"因子数量: {len(factors)}")
    
    try:
        # 执行批量采集
        print("开始批量采集...")
        results = collector.collect_batch(factors)
        
        print(f"[OK] 批量采集完成")
        print(f"   成功: {len(results['success'])}")
        print(f"   失败: {len(results['failed'])}")
        
        # 显示结果详情
        if results['success']:
            print("\n   成功因子:")
            for factor_code in results['success']:
                data_info = results['data'].get(factor_code, {})
                print(f"     - {factor_code}: {data_info.get('shape', 'N/A')}")
        
        return len(results['failed']) == 0
        
    except Exception as e:
        print(f"[FAIL] 批量采集失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("因子数据采集系统 - 快速演示")
    print("=" * 60)
    
    print("1. 测试单因子采集...")
    quick_result = run_quick_test()
    
    print("\n2. 测试批量采集...")
    batch_result = test_batch_collection()
    
    print("\n" + "=" * 60)
    print("演示结果总结")
    print("=" * 60)
    
    if quick_result and batch_result:
        print("[SUCCESS] 所有测试通过！系统运行正常。")
        print("\n下一步:")
        print("  1. 查看 demo_output/ 目录中的采集结果")
        print("  2. 运行 deployment_check.py 检查完整部署")
        print("  3. 运行 test_extended_collectors.py 测试所有数据源")
    else:
        print("[WARN]  部分测试失败。")
        print("\n建议:")
        print("  1. 运行 deployment_check.py 检查依赖")
        print("  2. 确保网络连接正常")
        print("  3. 检查 AKShare 包是否安装正确")
    
    print("\n快速演示完成。")


if __name__ == "__main__":
    main()