# -*- coding: utf-8 -*-
"""
Risk Fix Verification Script
Verify core calculation logic after fixes
"""

import sys
sys.path.insert(0, 'D:/futures_v6')

from services.macro_risk_app import get_symbol_config, get_contract_size, get_margin_ratio, get_trading_hours, is_in_trading_hours
from datetime import time as dt_time


def test_symbol_config():
    """Test symbol configuration"""
    print("=" * 60)
    print("Test Symbol Configuration")
    print("=" * 60)
    
    test_cases = [
        ('AU', 1000, 0.10),  # Gold
        ('AG', 15, 0.13),    # Silver
        ('RU', 10, 0.12),    # Rubber
        ('CU', 5, 0.12),     # Copper
    ]
    
    for symbol, expected_size, expected_margin in test_cases:
        config = get_symbol_config(symbol)
        size = config['size']
        margin = config['margin_ratio']
        
        status = "PASS" if size == expected_size and margin == expected_margin else "FAIL"
        print(f"{status} {symbol}: size={size} (expect{expected_size}), margin={margin:.0%} (expect{expected_margin:.0%})")
    
    print()


def test_pnl_calculation():
    """Test PnL calculation"""
    print("=" * 60)
    print("Test PnL Calculation (with contract size)")
    print("=" * 60)
    
    test_cases = [
        {
            'name': 'AU Long Profit',
            'symbol': 'AU',
            'entry_price': 550.0,
            'exit_price': 555.0,
            'volume': 1,
            'direction': 'LONG',
            'expected_pnl': 5000.0,  # (555-550) * 1 * 1000 = 5000
        },
        {
            'name': 'AU Long Loss',
            'symbol': 'AU',
            'entry_price': 550.0,
            'exit_price': 545.0,
            'volume': 1,
            'direction': 'LONG',
            'expected_pnl': -5000.0,  # (545-550) * 1 * 1000 = -5000
        },
        {
            'name': 'RU Long Profit',
            'symbol': 'RU',
            'entry_price': 15000.0,
            'exit_price': 15100.0,
            'volume': 1,
            'direction': 'LONG',
            'expected_pnl': 1000.0,  # (15100-15000) * 1 * 10 = 1000
        },
        {
            'name': 'AG Short Profit',
            'symbol': 'AG',
            'entry_price': 7000.0,
            'exit_price': 6900.0,
            'volume': 1,
            'direction': 'SHORT',
            'expected_pnl': 1500.0,  # (7000-6900) * 1 * 15 = 1500
        },
    ]
    
    for case in test_cases:
        size = get_contract_size(case['symbol'])
        
        if case['direction'] == 'LONG':
            pnl = (case['exit_price'] - case['entry_price']) * case['volume'] * size
        else:
            pnl = (case['entry_price'] - case['exit_price']) * case['volume'] * size
        
        status = "PASS" if abs(pnl - case['expected_pnl']) < 0.01 else "FAIL"
        print(f"{status} {case['name']}: PnL={pnl:.2f} (expect{case['expected_pnl']:.2f})")
    
    print()


def test_position_limit():
    """Test position limit calculation"""
    print("=" * 60)
    print("Test Position Limit (by capital ratio)")
    print("=" * 60)
    
    # Simulate account balance 1M
    balance = 1000000
    max_position_value = balance * 0.30  # 30% capital
    
    test_cases = [
        {'symbol': 'AU', 'price': 550.0, 'expected_max_lots': 5},  # 300K/(550*1000*0.10) = 5.45 -> 5
        {'symbol': 'RU', 'price': 15000.0, 'expected_max_lots': 16},  # 300K/(15000*10*0.12) = 16.67 -> 16
        {'symbol': 'AG', 'price': 7000.0, 'expected_max_lots': 21},  # 300K/(7000*15*0.13) = 21.98 -> 21
    ]
    
    for case in test_cases:
        config = get_symbol_config(case['symbol'])
        size = config['size']
        margin_ratio = config['margin_ratio']
        
        max_lots = int(max_position_value / (case['price'] * size * margin_ratio))
        max_lots = max(1, max_lots)
        
        status = "PASS" if max_lots == case['expected_max_lots'] else "FAIL"
        print(f"{status} {case['symbol']} @ {case['price']}: max{max_lots} lots (expect{case['expected_max_lots']} lots)")
    
    print()


def test_trading_hours():
    """Test trading hours"""
    print("=" * 60)
    print("Test Trading Hours Configuration")
    print("=" * 60)
    
    test_cases = [
        {'symbol': 'AU', 'time': dt_time(22, 0), 'expected': True},   # Night session
        {'symbol': 'AU', 'time': dt_time(3, 0), 'expected': False},   # After night session
        {'symbol': 'CU', 'time': dt_time(22, 0), 'expected': True},   # Night session
        {'symbol': 'CU', 'time': dt_time(2, 0), 'expected': False},   # After night session (CU ends 01:00)
        {'symbol': 'RB', 'time': dt_time(22, 0), 'expected': True},   # Night session
        {'symbol': 'RB', 'time': dt_time(23, 30), 'expected': False}, # After night session (RB ends 23:00)
    ]
    
    for case in test_cases:
        trading_hours = get_trading_hours(case['symbol'])
        
        in_trading = is_in_trading_hours(trading_hours, case['time'])
        
        status = "PASS" if in_trading == case['expected'] else "FAIL"
        time_status = "trading" if in_trading else "non-trading"
        print(f"{status} {case['symbol']} @ {case['time']}: {time_status} (expect{'trading' if case['expected'] else 'non-trading'})")
    
    print()


def test_stop_loss_parameters():
    """Test stop loss parameters"""
    print("=" * 60)
    print("Test Stop Loss Parameters (amount-based)")
    print("=" * 60)
    
    # New parameters
    stop_loss = 5000      # 5000 CNY per lot
    take_profit = 10000   # 10000 CNY per lot
    trailing_stop = 3000  # 3000 CNY pullback
    
    print(f"Fixed Stop Loss: {stop_loss} CNY/lot")
    print(f"Fixed Take Profit: {take_profit} CNY/lot")
    print(f"Trailing Stop: {trailing_stop} CNY pullback")
    print()
    
    # Verify price changes for different symbols
    test_cases = [
        {'symbol': 'AU', 'price_change': 5.0, 'expected_loss': 5000.0},   # 5 CNY/g * 1000g = 5000 CNY
        {'symbol': 'RU', 'price_change': 500.0, 'expected_loss': 5000.0}, # 500 CNY/ton * 10ton = 5000 CNY
        {'symbol': 'AG', 'price_change': 333.33, 'expected_loss': 5000.0}, # 333.33 CNY/kg * 15kg = 5000 CNY
    ]
    
    for case in test_cases:
        size = get_contract_size(case['symbol'])
        actual_loss = case['price_change'] * size
        
        status = "PASS" if abs(actual_loss - case['expected_loss']) < 1 else "FAIL"
        print(f"{status} {case['symbol']}: price_change{case['price_change']} x size{size} = loss{actual_loss:.2f} CNY (expect{case['expected_loss']:.2f})")
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Risk Fix Verification")
    print("=" * 60 + "\n")
    
    test_symbol_config()
    test_pnl_calculation()
    test_position_limit()
    test_trading_hours()
    test_stop_loss_parameters()
    
    print("=" * 60)
    print("Verification Complete")
    print("=" * 60)
