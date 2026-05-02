"""
Test HMMRegimeDetector new features:
1. select_n_regimes() - BIC/AIC automatic state selection
2. save() / load() - model persistence
"""
import sys
import os
import numpy as np
import pandas as pd
import tempfile

sys.path.insert(0, r'D:\futures_v6\macro_engine\research')
from phase2_statistical_modules import HMMRegimeDetector

# Synthetic test data (AG 1d return simulation, 1523 rows)
np.random.seed(42)
n = 1523
data = pd.DataFrame({
    'date': pd.date_range('2020-01-02', periods=n, freq='B'),
    'close': 5000 + np.cumsum(np.random.randn(n) * 30)
})
data['ret'] = data['close'].pct_change().fillna(0)
X = data[['ret']].values  # numpy array for select_n_regimes
X_series = data['ret']           # pandas Series for fit()
print(f"Test data: {X.shape}, mean={X.mean():.6f}, std={X.std():.6f}")

# ========== Test 1: select_n_regimes ==========
print("\n=== Test 1: select_n_regimes ===")
detector = HMMRegimeDetector(n_regimes=3)
optimal = detector.select_n_regimes(X, n_range=(2, 4), criterion='bic', verbose=True)
print(f"PASS select_n_regimes OK, n_regimes={optimal}")

# ========== Test 2: save / load ==========
print("\n=== Test 2: save / load ===")
# First fit a model
detector2 = HMMRegimeDetector(n_regimes=3)
detector2.fit(X_series)
print(f"After fit, transmat:\n{detector2.model.transmat_}")

with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f:
    tmp_path = f.name
try:
    # save
    detector2.save(tmp_path)
    size = os.path.getsize(tmp_path)
    print(f"PASS save OK, file={size/1024:.1f} KB")

    # load
    detector3 = HMMRegimeDetector.load(tmp_path)
    print(f"PASS load OK")
    print(f"transmat match: {np.allclose(detector2.model.transmat_, detector3.model.transmat_)}")
    print(f"n_regimes match: {detector2.n_regimes == detector3.n_regimes}")
    print(f"_X_mean match: {np.allclose(detector2._X_mean, detector3._X_mean)}")
    print(f"_X_std match: {np.allclose(detector2._X_std, detector3._X_std)}")
finally:
    os.unlink(tmp_path)
    print("Temp file cleaned")

print("\nALL TESTS PASSED")
