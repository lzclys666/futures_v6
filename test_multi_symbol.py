#!/usr/bin/env python
# -*- coding: utf-8 -*-
from config.paths import PROJECT_ROOT
"""
多品种支持测试
"""

import sys
from pathlib import Path

# Add project path
project_dir = PROJECT_ROOT
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from strategies.macro_demo_strategy import MacroDemoStrategy, SYMBOL_CONFIG


def test_symbol_extraction():
    """测试品种代码提取"""
    print("=== 测试品种代码提取 ===")
    
    test_cases = [
        ('RU2505.SHFE', 'RU'),
        ('ZN2506.SHFE', 'ZN'),
        ('RB2510.SHFE', 'RB'),
        ('I2505.DCE', 'I'),
        ('JM2505.DCE', 'JM'),
        ('TA2505.CZCE', 'TA'),
        ('MA2505.CZCE', 'MA'),
        ('SC2505.INE', 'SC'),
        ('IF2505.CFFEX', 'IF'),
    ]
    
    strategy = MacroDemoStrategy(None, "test", "RU2505.SHFE", {})
    
    for vt_symbol, expected in test_cases:
        result = strategy.extract_symbol(vt_symbol)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {vt_symbol} -> {result} (expected: {expected}) [{status}]")


def test_symbol_config():
    """测试品种配置获取"""
    print("\n=== 测试品种配置获取 ===")
    
    strategy = MacroDemoStrategy(None, "test", "RU2505.SHFE", {})
    
    for symbol in ['RU', 'ZN', 'RB', 'I', 'TA', 'SC', 'IF', 'UNKNOWN']:
        config = strategy.get_symbol_config(symbol)
        print(f"  {symbol}: {config}")


def test_supported_symbols():
    """测试支持的品种列表"""
    print("\n=== 支持的品种列表 ===")
    
    print(f"总计: {len(SYMBOL_CONFIG)} 个品种")
    print("\n上海期货交易所 (SHFE):")
    for symbol, config in SYMBOL_CONFIG.items():
        if config['exchange'] == 'SHFE':
            print(f"  {symbol}: {config['name']} (size={config['size']}, pricetick={config['pricetick']})")
    
    print("\n大连商品交易所 (DCE):")
    for symbol, config in SYMBOL_CONFIG.items():
        if config['exchange'] == 'DCE':
            print(f"  {symbol}: {config['name']} (size={config['size']}, pricetick={config['pricetick']})")
    
    print("\n郑州商品交易所 (CZCE):")
    for symbol, config in SYMBOL_CONFIG.items():
        if config['exchange'] == 'CZCE':
            print(f"  {symbol}: {config['name']} (size={config['size']}, pricetick={config['pricetick']})")
    
    print("\n上海国际能源交易中心 (INE):")
    for symbol, config in SYMBOL_CONFIG.items():
        if config['exchange'] == 'INE':
            print(f"  {symbol}: {config['name']} (size={config['size']}, pricetick={config['pricetick']})")
    
    print("\n中国金融期货交易所 (CFFEX):")
    for symbol, config in SYMBOL_CONFIG.items():
        if config['exchange'] == 'CFFEX':
            print(f"  {symbol}: {config['name']} (size={config['size']}, pricetick={config['pricetick']})")


if __name__ == "__main__":
    test_symbol_extraction()
    test_symbol_config()
    test_supported_symbols()
    print("\n测试完成！")
