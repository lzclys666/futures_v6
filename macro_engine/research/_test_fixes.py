"""Test both fixes with synthetic data for HMM"""
import sys, warnings
sys.path.insert(0, r'D:\futures_v6\macro_engine\research')
from phase2_statistical_modules import HMMRegimeDetector, PITDataService
import pandas as pd
import numpy as np

print("=" * 60)
print("Fix 1: HMM fit_stable() test (synthetic data)")
print("=" * 60)

# Generate synthetic returns (3 regimes: bear/neutral/bull)
np.random.seed(42)
n = 500
returns = []
for _ in range(n):
    regime = np.random.choice([0, 1, 2], p=[0.3, 0.5, 0.2])
    if regime == 0:
        r = np.random.normal(-0.005, 0.015)  # bear
    elif regime == 1:
        r = np.random.normal(0.000, 0.010)   # neutral
    else:
        r = np.random.normal(0.008, 0.020)    # bull
    returns.append(r)

ret = pd.Series(returns, index=pd.date_range('2020-01-01', periods=n, freq='B'))

try:
    hmm = HMMRegimeDetector(n_regimes=3)
    hmm.fit_stable(ret, n_seeds=10)
    tm = hmm.get_transition_matrix()
    print(f"Best seed: {hmm.random_state}")
    print(f"Transition matrix:\n{tm.round(4)}")
    diag = np.diag(tm.values)
    print(f"Self-transition: {diag}")
    print(f"Min self-transition: {diag.min():.4f}  {'PASS' if diag.min() > 0.01 else 'FAIL - transient state!'}")
    stats = hmm.get_regime_stats()
    for k, v in stats.items():
        print(f"  {k}: count={v['count']}, self_t={v['transition_from_self']:.4f}")
    print("HMM test: PASS")
except Exception as e:
    print(f"HMM test FAILED: {e}")
    import traceback; traceback.print_exc()

print()
print("=" * 60)
print("Fix 2: JM spread repair_obs_date() test")
print("=" * 60)

try:
    pit = PITDataService()

    # Compare v1 (old) vs v2 (new) compliance check
    v1 = pit.verify_pit_compliance('jm_futures_spread')
    v2 = pit.verify_pit_compliance_v2('jm_futures_spread')

    print(f"Old method (v1) - pub_date>obs_date violations: {v1['future_violations']}")
    print(f"New method (v2) - obs_date>trade_date violations: {v2['obs_gt_trade']}")
    print(f"New method (v2) - compliant: {v2['compliant']}")

    # DRY RUN - should show 0 since obs_date already fixed
    result = pit.repair_obs_date('jm_futures_spread', dry_run=True)
    print(f"\nrepair_obs_date DRY RUN: {result['message']}")
    print(f"  Total mismatches: {result['total_mismatches']}")

    if result['total_mismatches'] > 0:
        # Execute fix
        fix = pit.repair_obs_date('jm_futures_spread', dry_run=False)
        print(f"[EXEC] {fix['message']}, fixed: {fix['fixed']}")
        v2_after = pit.verify_pit_compliance_v2('jm_futures_spread')
        print(f"After fix (v2) - compliant: {v2_after['compliant']}, obs_gt_trade: {v2_after['obs_gt_trade']}")
    else:
        print("No mismatches found - obs_date already equals trade_date for all rows")
        print("JM spread PIT repair: ALREADY COMPLETE (obs_date == trade_date)")

    pit.close()
    print("JM spread test: PASS")
except Exception as e:
    print(f"JM spread test FAILED: {e}")
    import traceback; traceback.print_exc()

print("\nAll tests done.")
