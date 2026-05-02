#!/usr/bin/env python3
"""
简单环境检查脚本
===============
避免 Unicode 编码问题
"""

import sys
import os
import importlib
import platform


def check_python():
    print("=" * 60)
    print("Python 环境检查")
    print("=" * 60)
    
    print(f"版本: Python {platform.python_version()}")
    print(f"架构: {platform.architecture()[0]}")
    print(f"可执行文件: {sys.executable}")
    
    if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
        print("[PASS] Python 版本满足要求")
        return True
    else:
        print("[FAIL] Python 版本过低，需要 >= 3.8")
        return False


def check_packages():
    print("\n" + "=" * 60)
    print("包依赖检查")
    print("=" * 60)
    
    basic_packages = [
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("requests", "requests"),
        ("beautifulsoup4", "bs4"),
        ("lxml", "lxml"),
    ]
    
    data_source_packages = [
        ("AKShare", "akshare"),
        ("Tushare", "tushare"),
        ("聚宽", "jqdatasdk"),
        ("优矿", "uqer"),
        ("WindPy", "WindPy"),
    ]
    
    print("基本包:")
    basic_ok = True
    for name, module in basic_packages:
        try:
            importlib.import_module(module)
            print(f"  [OK] {name}")
        except ImportError:
            print(f"  [MISSING] {name}")
            basic_ok = False
    
    print("\n数据源包:")
    data_ok = {}
    for name, module in data_source_packages:
        try:
            importlib.import_module(module)
            print(f"  [OK] {name}")
            data_ok[name] = True
        except ImportError:
            print(f"  [MISSING] {name}")
            data_ok[name] = False
    
    return basic_ok, data_ok


def check_env_vars():
    print("\n" + "=" * 60)
    print("环境变量检查")
    print("=" * 60)
    
    env_vars = [
        ("TUSHARE_TOKEN", "Tushare API Token", False),
        ("JQ_USER", "聚宽用户名", False),
        ("JQ_PASS", "聚宽密码", False),
        ("UQER_TOKEN", "优矿 Token", False),
    ]
    
    for var, desc, required in env_vars:
        value = os.getenv(var)
        if value:
            if var in ["JQ_PASS", "UQER_TOKEN", "TUSHARE_TOKEN"]:
                masked = value[:4] + "***" + value[-4:] if len(value) > 8 else "***"
                print(f"  [SET] {var}: {masked}")
            else:
                print(f"  [SET] {var}: {value}")
        else:
            if required:
                print(f"  [MISSING] {var}: 未设置（必需）")
            else:
                print(f"  [UNSET] {var}: 未设置（可选）")


def check_directory():
    print("\n" + "=" * 60)
    print("目录结构检查")
    print("=" * 60)
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    root_path = os.path.dirname(base_path)
    
    dirs = [
        ("脚本目录", base_path),
        ("采集器目录", os.path.join(base_path, "collectors")),
        ("模板目录", os.path.join(root_path, "templates")),
        ("数据目录", os.path.join(root_path, "data")),
    ]
    
    for name, path in dirs:
        if os.path.exists(path):
            print(f"  [EXISTS] {name}: {path}")
        else:
            print(f"  [MISSING] {name}: {path}")


def main():
    print("因子数据采集系统 - 环境检查")
    print("=" * 60)
    
    # 检查 Python
    py_ok = check_python()
    
    # 检查包
    basic_ok, data_ok = check_packages()
    
    # 检查环境变量
    check_env_vars()
    
    # 检查目录
    check_directory()
    
    # 总结
    print("\n" + "=" * 60)
    print("检查总结")
    print("=" * 60)
    
    akshare_ok = data_ok.get("AKShare", False)
    
    if py_ok and basic_ok and akshare_ok:
        print("[SUCCESS] 基本环境就绪，可运行快速演示")
        print("\n建议:")
        print("  1. 运行: python demo_quick_test.py")
        print("  2. 或运行: run_demo.bat")
    else:
        print("[WARNING] 环境不完整")
        print("\n需要:")
        if not py_ok:
            print("  - 安装 Python 3.8+")
        if not basic_ok:
            print("  - 安装基本包: pip install pandas numpy requests beautifulsoup4 lxml")
        if not akshare_ok:
            print("  - 安装 AKShare: pip install akshare")


if __name__ == "__main__":
    main()