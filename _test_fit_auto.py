# -*- coding: utf-8 -*-
import sys, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, r'D:\futures_v6\macro_engine\research')
import numpy as np, pandas as pd
from phase2_statistical_modules import HMMRegimeDetector

# Test with random data
np.random.seed(42)
dates = pd.date_range('2020-01-01', periods=500, freq='B')
rets = pd.Series(np.cumsum(np.random.randn(500) * 0.02), index=dates)

detector = HMMRegimeDetector(n_regimes=3)
print(f"Initial n_regimes: {detector.n_regimes}")
detector.fit_auto(rets, n_seeds=5, n_range=(2, 4))
print(f"After fit_auto n_regimes: {detector.n_regimes}")
print(f"Fitted: {detector.fitted}")
result = detector.predict_regime(rets.tail(30))
print(f"Current regime: {result['regime'].iloc[-1]}")
print("fit_auto OK")
