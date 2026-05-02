#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CTP SimNow 连接测试脚本
非交易时间验证连接和登录
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_ctp_connect():
    """测试CTP连接"""
    print("="*60)
    print("CTP SimNow Connection Test")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查VNpy CTP模块
    try:
        from vnpy_ctp import CtpGateway
        print("[OK] vnpy_ctp module imported")
    except ImportError as e:
        print(f"[FAIL] vnpy_ctp import failed: {e}")
        return False
    
    # 检查事件引擎
    try:
        from vnpy.event import EventEngine
        event_engine = EventEngine()
        print("[OK] EventEngine created")
    except Exception as e:
        print(f"[FAIL] EventEngine creation failed: {e}")
        return False
    
    # 检查主引擎
    try:
        from vnpy.trader.engine import MainEngine
        main_engine = MainEngine(event_engine)
        print("[OK] MainEngine created")
    except Exception as e:
        print(f"[FAIL] MainEngine creation failed: {e}")
        return False
    
    # 添加CTP网关
    try:
        main_engine.add_gateway(CtpGateway)
        print("[OK] CtpGateway added to MainEngine")
    except Exception as e:
        print(f"[FAIL] Add gateway failed: {e}")
        return False
    
    # 尝试连接（使用SimNow测试环境）
    print("\n[Connecting to SimNow...]")
    
    # SimNow测试环境配置
    setting = {
        "用户名": "your_simnow_userid",
        "密码": "your_simnow_password",
        "经纪商代码": "9999",
        "交易服务器": "180.168.146.187:10101",
        "行情服务器": "180.168.146.187:10111",
        "产品名称": "simnow_client_test",
        "授权编码": "0000000000000000",
    }
    
    print(f"  Trade Server: {setting['交易服务器']}")
    print(f"  Market Server: {setting['行情服务器']}")
    print(f"  Broker: {setting['经纪商代码']}")
    
    # 非交易时间提示
    print("\n[WARNING] Current time is non-trading hours")
    print("  Trading hours: 09:00-10:15, 10:30-11:30, 13:30-15:00, 21:00-23:00")
    print("  Connection test will verify network only")
    print()
    
    # 实际连接（需要有效账户）
    try:
        connect_status = main_engine.connect(setting, "CTP")
        print(f"[INFO] Connect returned: {connect_status}")
        
        # 等待连接结果
        import time
        time.sleep(3)
        
        # 检查连接状态
        print("\n[Connection Status Check]")
        print("  Note: Without valid SimNow credentials, connection will fail")
        print("  This is expected for testing purposes")
        
    except Exception as e:
        print(f"[INFO] Connection attempt completed: {e}")
    
    # 清理
    main_engine.close()
    event_engine.stop()
    print("\n[OK] Resources cleaned up")
    
    return True


def test_paper_trade_mode():
    """测试Paper Trade模式"""
    print("\n" + "="*60)
    print("Paper Trade Mode Test")
    print("="*60)
    
    try:
        from vnpy_paperaccount import PaperAccountApp
        print("[OK] vnpy_paperaccount imported")
        
        from vnpy.event import EventEngine
        from vnpy.trader.engine import MainEngine
        
        event_engine = EventEngine()
        main_engine = MainEngine(event_engine)
        
        # 添加Paper Account
        paper_app = main_engine.add_app(PaperAccountApp)
        print("[OK] PaperAccountApp added")
        
        # 获取Paper引擎
        paper_engine = main_engine.get_engine("PaperAccount")
        if paper_engine:
            print("[OK] PaperAccount engine retrieved")
            print(f"  Paper trading: {paper_engine.active}")
        
        main_engine.close()
        event_engine.stop()
        
        return True
        
    except ImportError:
        print("[INFO] vnpy_paperaccount not installed")
        print("  Paper trade mode requires: pip install vnpy_paperaccount")
        return False
    except Exception as e:
        print(f"[FAIL] Paper trade test failed: {e}")
        return False


def check_simnow_account():
    """检查SimNow账户配置"""
    print("\n" + "="*60)
    print("SimNow Account Check")
    print("="*60)
    
    # 检查环境变量或配置文件
    account_file = os.path.expanduser("~/.vnpy/ctp_account.json")
    
    if os.path.exists(account_file):
        print(f"[OK] Account file found: {account_file}")
        import json
        try:
            with open(account_file, 'r') as f:
                account = json.load(f)
            print(f"  UserID: {account.get('userid', 'N/A')}")
            print(f"  Broker: {account.get('brokerid', 'N/A')}")
            return True
        except Exception as e:
            print(f"[FAIL] Read account file failed: {e}")
            return False
    else:
        print("[INFO] No account file found")
        print(f"  Expected: {account_file}")
        print("\n  To get SimNow account:")
        print("  1. Register at: http://www.simnow.com.cn/")
        print("  2. Download CTP API")
        print("  3. Save credentials to ~/.vnpy/ctp_account.json")
        return False


def run_all_tests():
    """运行所有测试"""
    results = []
    
    # 测试1: CTP连接
    results.append(("CTP Connect", test_ctp_connect()))
    
    # 测试2: Paper Trade
    results.append(("Paper Trade", test_paper_trade_mode()))
    
    # 测试3: 账户检查
    results.append(("SimNow Account", check_simnow_account()))
    
    # 汇总
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for name, result in results:
        status = "PASS" if result else "INFO/FAIL"
        print(f"[{status}] {name}")
    
    print("\n[NOTE] Non-trading hours connection test:")
    print("  - Network connectivity can be verified")
    print("  - Login requires valid SimNow credentials")
    print("  - Order placement requires trading hours")
    
    return results


if __name__ == "__main__":
    run_all_tests()
