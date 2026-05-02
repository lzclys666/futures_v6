# adapters/test_adapters.py
# 适配器层测试脚本

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adapters import (
    AdapterManager,
    get_adapter_manager,
    AKShareAdapter,
    TushareAdapter,
    ExchangeAdapter,
    AdapterResult,
)


def test_akshare_health():
    """测试AKShare适配器健康状态"""
    print("\n=== AKShare健康检查 ===")
    adapter = AKShareAdapter()
    health = adapter.check_health()
    print(f"AKShare可用: {health}")
    return health


def test_adapter_manager():
    """测试适配器管理器"""
    print("\n=== 适配器管理器测试 ===")
    
    manager = get_adapter_manager()
    
    # 列出所有适配器
    print("\n--- 注册的适配器 ---")
    adapters = manager.list_adapters()
    for a in adapters:
        print(f"  {a['name']}: 优先级={a['priority']}, 可用={a['available']}")
    
    # 检查所有健康状态
    print("\n--- 健康状态 ---")
    health = manager.check_all_health()
    for name, status in health.items():
        print(f"  {name}: {'OK' if status else 'FAIL'}")


def test_precious_metals():
    """测试贵金属数据获取"""
    print("\n=== 贵金属测试 ===")
    
    manager = get_adapter_manager()
    
    # 测试黄金现货
    print("\n--- 黄金现货 (AU) ---")
    result = manager.get_precious_metal("AU")
    print(f"成功: {result.succeeded}")
    print(f"源: {result.source_name}")
    if result.data is not None:
        print(f"数据形状: {result.data.shape}")
        print(f"列名: {list(result.data.columns)[:5]}")
    else:
        print(f"错误: {result.error}")


def test_bond_yield():
    """测试国债收益率"""
    print("\n=== 国债收益率测试 ===")
    
    manager = get_adapter_manager()
    
    result = manager.get_bond_yield("US10Y")
    print(f"成功: {result.succeeded}")
    print(f"源: {result.source_name}")
    if result.data is not None:
        print(f"数据形状: {result.data.shape}")
        print(f"列名: {list(result.data.columns)}")
        print(f"最新数据:\n{result.data.head(2)}")
    else:
        print(f"错误: {result.error}")


def test_futures_oi():
    """测试期货持仓"""
    print("\n=== 期货持仓测试 ===")
    
    manager = get_adapter_manager()
    
    # 测试AU持仓
    result = manager.get_open_interest("AU0")
    print(f"成功: {result.succeeded}")
    print(f"源: {result.source_name}")
    if result.data is not None:
        print(f"数据形状: {result.data.shape}")
    else:
        print(f"错误: {result.error}")


def main():
    """主测试函数"""
    print("=" * 60)
    print("适配器层测试")
    print("=" * 60)
    
    test_akshare_health()
    test_adapter_manager()
    test_precious_metals()
    test_bond_yield()
    test_futures_oi()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
