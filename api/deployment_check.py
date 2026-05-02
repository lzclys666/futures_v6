#!/usr/bin/env python3
"""
部署检查脚本
===========
检查因子数据采集系统的所有依赖和配置

运行：
    python deployment_check.py
"""

import sys
import os
import importlib
from pathlib import Path


def check_python_version():
    """检查 Python 版本"""
    import platform
    
    print("=" * 60)
    print("检查 Python 版本...")
    
    version_info = sys.version_info
    version_str = platform.python_version()
    
    print(f"   当前版本: Python {version_str}")
    print(f"   架构: {platform.architecture()[0]}")
    
    if version_info.major >= 3 and version_info.minor >= 8:
        print("   ✓ Python 版本满足要求")
        return True
    else:
        print(f"   ✗ Python 版本过低，需要 >= 3.8")
        return False


def check_required_packages():
    """检查必需包"""
    print("\n" + "=" * 60)
    print("检查必需包...")
    
    required = [
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("requests", "requests"),
        ("beautifulsoup4", "bs4"),
        ("lxml", "lxml"),
        ("pytz", "pytz"),
        ("python-dateutil", "dateutil"),
    ]
    
    all_ok = True
    
    for pip_name, import_name in required:
        try:
            importlib.import_module(import_name)
            print(f"   ✅ {pip_name}")
        except ImportError:
            print(f"   ❌ {pip_name} 未安装")
            all_ok = False
    
    return all_ok


def check_data_source_packages():
    """检查数据源专用包"""
    print("\n" + "=" * 60)
    print("检查数据源专用包...")
    
    sources = [
        ("AKShare", "akshare"),
        ("Tushare", "tushare"),
        ("WindPy", "WindPy"),
        ("聚宽", "jqdatasdk"),
        ("优矿", "uqer"),
    ]
    
    status = {}
    
    for source_name, module_name in sources:
        try:
            importlib.import_module(module_name)
            status[source_name] = True
            print(f"   ✅ {source_name} - 已安装")
        except ImportError:
            status[source_name] = False
            print(f"   ⚠️  {source_name} - 未安装")
    
    return status


def check_environment_variables():
    """检查环境变量"""
    print("\n" + "=" * 60)
    print("检查环境变量...")
    
    env_vars = [
        ("TUSHARE_TOKEN", "Tushare API Token", False),
        ("JQ_USER", "聚宽用户名", False),
        ("JQ_PASS", "聚宽密码", False),
        ("UQER_TOKEN", "优矿 Token", False),
    ]
    
    all_ok = True
    
    for var_name, description, required in env_vars:
        value = os.getenv(var_name)
        if value:
            # 隐藏敏感信息，只显示部分
            if var_name in ["JQ_PASS", "UQER_TOKEN", "TUSHARE_TOKEN"]:
                masked = value[:4] + "***" + value[-4:] if len(value) > 8 else "***"
                print(f"   ✅ {var_name}: {masked}")
            else:
                print(f"   ✅ {var_name}: {value}")
        else:
            if required:
                print(f"   ❌ {var_name}: 未设置（必需）")
                all_ok = False
            else:
                print(f"   ⚠️  {var_name}: 未设置（可选）")
    
    return all_ok


def check_directory_structure():
    """检查目录结构"""
    print("\n" + "=" * 60)
    print("检查目录结构...")
    
    base_path = Path(__file__).parent
    required_dirs = [
        base_path,
        base_path / "collectors",
        base_path.parent / "templates",
        base_path.parent / "data",
        base_path.parent / "logs",
        base_path.parent / "collected_data",
    ]
    
    all_ok = True
    
    for dir_path in required_dirs:
        if dir_path.exists():
            print(f"   ✅ {dir_path.relative_to(base_path.parent)}")
        else:
            print(f"   ❌ {dir_path.relative_to(base_path.parent)} - 目录不存在")
            all_ok = False
    
    return all_ok


def check_script_files():
    """检查脚本文件"""
    print("\n" + "=" * 60)
    print("检查脚本文件...")
    
    base_path = Path(__file__).parent
    required_files = [
        base_path / "factor_collector.py",
        base_path / "trigger_collection.py",
        base_path / "collectors" / "__init__.py",
        base_path / "collectors" / "akshare_collector.py",
        base_path / "collectors" / "tushare_collector.py",
        base_path / "collectors" / "custom_collector.py",
        base_path / "collectors" / "wind_collector.py",
        base_path / "collectors" / "joinquant_collector.py",
        base_path / "collectors" / "uqer_collector.py",
        base_path / "collectors" / "exchange_crawler.py",
    ]
    
    all_ok = True
    
    for file_path in required_files:
        if file_path.exists():
            print(f"   ✅ {file_path.relative_to(base_path.parent)}")
        else:
            print(f"   ❌ {file_path.relative_to(base_path.parent)} - 文件不存在")
            all_ok = False
    
    return all_ok


def check_template_files():
    """检查模板文件"""
    print("\n" + "=" * 60)
    print("检查模板文件...")
    
    base_path = Path(__file__).parent.parent
    required_templates = [
        base_path / "templates" / "factor_requirements_template.json",
        base_path / "templates" / "factor_requirements_minimal_template.json",
        base_path / "templates" / "factor_requirements_field_guide.md",
        base_path / "templates" / "factor_requirements_extended_example.json",
    ]
    
    all_ok = True
    
    for file_path in required_templates:
        if file_path.exists():
            print(f"   ✅ {file_path.relative_to(base_path)}")
        else:
            print(f"   ❌ {file_path.relative_to(base_path)} - 文件不存在")
            all_ok = False
    
    return all_ok


def check_skill_file():
    """检查 Skill 文件"""
    print("\n" + "=" * 60)
    print("检查 Skill 文件...")
    
    base_path = Path(__file__).parent.parent
    skill_dir = base_path / "skills" / "factor-collection-workflow"
    
    if not skill_dir.exists():
        print("   ⚠️  Skill 目录不存在")
        return False
    
    required_files = [
        skill_dir / "SKILL.md",
    ]
    
    all_ok = True
    
    for file_path in required_files:
        if file_path.exists():
            print(f"   ✅ {file_path.relative_to(base_path)}")
        else:
            print(f"   ❌ {file_path.relative_to(base_path)} - 文件不存在")
            all_ok = False
    
    return all_ok


def check_config_files():
    """检查配置文件"""
    print("\n" + "=" * 60)
    print("检查配置文件...")
    
    base_path = Path(__file__).parent.parent
    config_files = [
        base_path / "config" / "factor_collection_cron_example.json",
    ]
    
    all_ok = True
    
    for file_path in config_files:
        if file_path.exists():
            print(f"   ✅ {file_path.relative_to(base_path)}")
        else:
            print(f"   ⚠️  {file_path.relative_to(base_path)} - 文件不存在（可选）")
    
    return all_ok


def main():
    """主检查函数"""
    print("因子数据采集系统 - 部署检查")
    print("=" * 60)
    
    results = []
    
    results.append(("Python 版本", check_python_version()))
    results.append(("必需包", check_required_packages()))
    
    source_status = check_data_source_packages()
    results.append(("数据源包", any(source_status.values())))
    
    results.append(("环境变量", check_environment_variables()))
    results.append(("目录结构", check_directory_structure()))
    results.append(("脚本文件", check_script_files()))
    results.append(("模板文件", check_template_files()))
    results.append(("Skill 文件", check_skill_file()))
    results.append(("配置文件", check_config_files()))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("部署检查总结")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"通过: {passed}/{total}")
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")
    
    # 数据源包状态详情
    print("\n数据源包状态:")
    for source_name, installed in source_status.items():
        status = "✅ 已安装" if installed else "❌ 未安装"
        print(f"  {status} {source_name}")
    
    # 部署建议
    print("\n" + "=" * 60)
    print("部署建议:")
    print("-" * 60)
    
    # 必需包安装命令
    print("1. 安装必需包:")
    print("   pip install pandas numpy requests beautifulsoup4 lxml pytz python-dateutil")
    
    # 数据源包安装命令
    print("\n2. 安装数据源包:")
    print("   # AKShare（首选免费）")
    print("   pip install akshare")
    
    print("   # Tushare（宏观数据）")
    print("   pip install tushare")
    
    print("   # 聚宽 JoinQuant（免费量化平台）")
    print("   pip install jqdatasdk")
    
    print("   # 优矿 Uqer（通联数据）")
    print("   pip install uqer")
    
    print("   # Wind（商业数据源）")
    print("   需要安装 Wind 终端和 WindPy")
    
    # 环境变量设置
    print("\n3. 设置环境变量:")
    print("   Windows:")
    print("   set TUSHARE_TOKEN=your_token")
    print("   set JQ_USER=your_username")
    print("   set JQ_PASS=your_password")
    print("   set UQER_TOKEN=your_token")
    
    print("\n   Linux/macOS:")
    print("   export TUSHARE_TOKEN=your_token")
    print("   export JQ_USER=your_username")
    print("   export JQ_PASS=your_password")
    print("   export UQER_TOKEN=your_token")
    
    if passed == total:
        print("\n🎉 所有检查通过！系统已准备就绪。")
    else:
        print("\n⚠️  请修复以上问题，然后重新运行检查。")


if __name__ == "__main__":
    main()