import sys
sys.path.append(r'D:\futures_v6\macro_engine\api')

from ic_heatmap.calculator import ICHeatmapCalculator
from signal_system.scoring import SignalScoringSystem

print("=" * 80)
print("Testing with Real Data")
print("=" * 80)

# Test 1: IC Heatmap
print("\n[1] Testing IC Heatmap...")
calculator = ICHeatmapCalculator()

result = calculator.compute_ic_matrix(
    symbols=['AG', 'CU'],
    factors=['momentum', 'usd_index', 'basis'],
    lookback=60,
    hold_period=5
)

print(f"\nFactors: {result['factors']}")
print(f"Symbols: {result['symbols']}")
print(f"Lookback: {result['lookbackPeriod']} days")
print(f"Hold Period: {result['holdPeriod']} days")

print("\nIC Matrix:")
header = "Factor\\Symbol".ljust(15)
for symbol in result['symbols']:
    header += symbol.ljust(12)
print(header)
print("-" * 80)

for i, factor in enumerate(result['factors']):
    row = factor.ljust(15)
    for j, symbol in enumerate(result['symbols']):
        ic_value = result['icMatrix'][i][j]
        row += f"{ic_value:+.4f}    "
    print(row)

# Test 2: Signal Scoring
print("\n" + "=" * 80)
print("[2] Testing Signal Scoring...")
scoring = SignalScoringSystem()

for symbol in ['AG', 'CU', 'RB']:
    print(f"\n--- {symbol} ---")
    signal = scoring.compute_signal_score(symbol)
    
    print(f"Composite Score: {signal['compositeScore']}")
    print(f"Signal Strength: {signal['signalStrength']}")
    print(f"Confidence: {signal['confidence']}%")
    print(f"Regime: {signal['regime']}")
    
    if signal['factorBreakdown']:
        print("Factor Breakdown:")
        for factor in signal['factorBreakdown']:
            print(f"  {factor['factorName']}: weight={factor['weight']:.2%}, "
                  f"IC={factor['ic']:+.4f}, contribution={factor['contribution']:.2f}")

print("\n" + "=" * 80)
print("Test completed!")
print("=" * 80)
