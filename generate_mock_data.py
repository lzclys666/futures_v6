import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Generate mock historical data for RU2505
def generate_mock_data(symbol='RU2505', days=60):
    print(f'[DATA] Generating mock data for {symbol}...')
    
    # Generate dates (trading days only)
    start_date = datetime(2025, 2, 1)
    dates = []
    current = start_date
    while len(dates) < days:
        if current.weekday() < 5:  # Monday to Friday
            # Trading hours: 9:00-10:15, 10:30-11:30, 13:30-15:00, 21:00-23:00
            for hour in [9, 10, 13, 14, 21, 22]:
                for minute in range(0, 60, 1):
                    if (hour == 9 and minute >= 0) or \
                       (hour == 10 and minute < 15) or \
                       (hour == 10 and minute >= 30) or \
                       (hour == 13 and minute >= 30) or \
                       (hour == 14) or \
                       (hour == 21) or \
                       (hour == 22):
                        dates.append(current + timedelta(hours=hour, minutes=minute))
        current += timedelta(days=1)
    
    # Generate price data
    np.random.seed(42)
    base_price = 15000
    prices = [base_price]
    
    for i in range(1, len(dates)):
        change = np.random.normal(0, 0.001)  # Small random walk
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    # Create DataFrame
    df = pd.DataFrame({
        'datetime': dates,
        'open': [p * (1 + np.random.normal(0, 0.0005)) for p in prices],
        'high': [p * (1 + abs(np.random.normal(0, 0.001))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.001))) for p in prices],
        'close': prices,
        'volume': np.random.randint(100, 10000, len(dates)),
        'open_interest': np.random.randint(10000, 100000, len(dates)),
    })
    
    # Ensure high >= open, close, low and low <= open, close, high
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df

# Generate data for multiple symbols
symbols = ['RU2505', 'ZN2505', 'RB2510', 'NI2505']
output_dir = Path('D:/futures_v6/data/historical')

for symbol in symbols:
    df = generate_mock_data(symbol)
    output_path = output_dir / f'{symbol}_1min.csv'
    df.to_csv(output_path, index=False)
    print(f'[DATA] Saved: {output_path} ({len(df)} rows)')

print('[DATA] Mock data generation complete!')
