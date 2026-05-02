import sys
from pathlib import Path
from datetime import datetime

project_dir = Path('D:/futures_v6')
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

print('[BACKTEST] Starting backtest...')

from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from strategies.macro_demo_strategy import MacroDemoStrategy

# Create backtesting engine
engine = BacktestingEngine()

# Set parameters
engine.set_parameters(
    vt_symbol="RU2505.SHFE",
    interval=Interval.MINUTE,
    start=datetime(2025, 1, 1),
    end=datetime(2025, 4, 24),
    rate=0.0001,
    slippage=2,
    size=10,
    pricetick=1,
    capital=1_000_000,
    mode=BacktestingMode.BAR  # 使用正确的枚举值
)

# Add strategy
engine.add_strategy(
    MacroDemoStrategy,
    {
        "fast_window": 10,
        "slow_window": 20,
        "use_macro": True,
        "csv_path_str": str(project_dir / "macro_engine/output/{symbol}_macro_daily_{date}.csv")
    }
)

# Load data
print('[BACKTEST] Loading historical data...')
data_path = project_dir / "data" / "historical" / "RU2505_1min.csv"
if data_path.exists():
    import pandas as pd
    df = pd.read_csv(data_path)
    print(f'[BACKTEST] Loaded {len(df)} rows from {data_path}')
    
    # Convert to BarData objects (backtesting engine expects bars in BAR_MODE)
    bars = []
    for _, row in df.iterrows():
        bar = BarData(
            symbol="RU2505",
            exchange=Exchange.SHFE,
            datetime=pd.to_datetime(row['datetime']),
            open_price=row['open'],
            high_price=row['high'],
            low_price=row['low'],
            close_price=row['close'],
            volume=row['volume'],
            open_interest=row['open_interest'],
            gateway_name="BACKTESTING"
        )
        bars.append(bar)
    
    engine.history_data = bars
    print(f'[BACKTEST] Data loaded: {len(engine.history_data)} bars')
else:
    print(f'[BACKTEST] Warning: Data file not found: {data_path}')
    sys.exit(1)

# Run backtest
print('[BACKTEST] Running backtest...')
engine.run_backtesting()

# Calculate result
print('[BACKTEST] Calculating results...')
engine.calculate_result()

# Calculate statistics
print('[BACKTEST] Calculating statistics...')
statistics = engine.calculate_statistics()

# Print results
print('\n' + '='*50)
print('BACKTEST RESULTS')
print('='*50)
for key, value in statistics.items():
    print(f'{key}: {value}')

# Show chart
print('[BACKTEST] Showing chart...')
engine.show_chart()

print('[BACKTEST] Done!')
