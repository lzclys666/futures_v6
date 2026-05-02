#!/usr/bin/env python3
"""自测：z-score 阈值过滤逻辑"""
import numpy as np

ZSCORE_THRESHOLD = 0.5

def _apply_threshold(x):
    if abs(x) >= ZSCORE_THRESHOLD:
        return np.sign(x)
    return 0

# Test cases: (input, expected_output)
tests = [
    (1.2,  1),    # |1.2| >= 0.5 → Long
    (-1.2, -1),   # |1.2| >= 0.5 → Short
    (0.3,  0),    # |0.3| < 0.5  → no trade
    (-0.3, 0),    # |0.3| < 0.5  → no trade
    (0.5,  1),    # boundary: |0.5| >= 0.5 → Long
    (-0.5, -1),   # boundary: |0.5| >= 0.5 → Short
    (0.49, 0),    # just below threshold
    (0.0,  0),    # zero → no trade
]

all_passed = True
for raw, expected in tests:
    result = _apply_threshold(raw)
    status = 'PASS' if result == expected else 'FAIL'
    if status == 'FAIL':
        all_passed = False
    print(f'  [{status}] _apply_threshold({raw:+.2f}) = {result:+.0f}  (expected {expected:+.0f})')

print()
if all_passed:
    print('✅ All tests PASSED')
else:
    print('❌ Some tests FAILED')
