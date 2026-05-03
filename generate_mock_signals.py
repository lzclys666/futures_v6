from config.paths import MACRO_ENGINE
import csv
from datetime import datetime, timedelta
from pathlib import Path

# Generate mock macro signals for backtesting
def generate_mock_macro_signals():
    output_dir = Path('str(MACRO_ENGINE)/output')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate signals for RU (橡胶) - alternating LONG/SHORT for testing
    symbols = ['RU', 'ZN', 'RB', 'NI']
    
    # Generate for multiple dates
    start_date = datetime(2025, 2, 1)
    
    for symbol in symbols:
        # Create signal file for each date
        for day_offset in range(60):
            date = start_date + timedelta(days=day_offset)
            if date.weekday() >= 5:  # Skip weekends
                continue
                
            date_str = date.strftime('%Y%m%d')
            file_path = output_dir / f'{symbol}_macro_daily_{date_str}.csv'
            
            # Alternate between LONG and SHORT every few days
            if (day_offset // 3) % 2 == 0:
                direction = 'LONG'
                score = 75.0
            else:
                direction = 'SHORT'
                score = 25.0
            
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['symbol', 'row_type', 'direction', 'composite_score', 'confidence'])
                # Write summary row
                writer.writerow([symbol, 'SUMMARY', direction, score, 'HIGH'])
                # Write some detail rows
                writer.writerow([symbol, 'DETAIL', direction, score * 0.9, 'HIGH'])
                writer.writerow([symbol, 'DETAIL', direction, score * 1.1, 'MEDIUM'])
            
            print(f'[SIGNAL] Created: {file_path} -> {direction} ({score})')

if __name__ == '__main__':
    generate_mock_macro_signals()
    print('[SIGNAL] Mock macro signals generated!')
