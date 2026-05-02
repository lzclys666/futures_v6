import pandas as pd, numpy as np
from scipy.stats import spearmanr

f = r'D:\futures_v6\macro_engine\data\crawlers\AG\daily\AG_fut_close.csv'
df = pd.read_csv(f, encoding='utf-8-sig')
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date').sort_index()
df['ret5'] = df['close'].pct_change(5)
df_orig = df.copy()

aligned = pd.DataFrame({'factor': df['close'], 'ret5': df['ret5']}).dropna()
print(f'aligned len={len(aligned)}, df len={len(df)}, offset=5')

# === The bug in Phase2: rolling on aligned vs iloc on df ===
# Phase2: rolling on aligned['factor'] uses iloc positions in aligned
# Reference: uses iloc positions in df
# But aligned[pos] = df[pos+5] (because 5 rows were dropped from the front)
# So at df position 825, Phase2 rolling sees df positions 770-829
# But reference sees df positions 765-824
# They differ by 5 positions (systematic offset)

# === Verify the offset ===
print('\n=== Offset verification ===')
for pos in [5, 10, 60, 100, 825]:
    aligned_val = aligned['factor'].iloc[pos]
    df_val = df['factor' if 'factor' in df.columns else 'close'].iloc[pos + 5]
    print(f'pos={pos}: aligned[{pos}]={aligned_val:.2f}, df[{pos+5}]={df_val:.2f}, match={np.isclose(aligned_val, df_val)}')

# === Reference implementation (correct) ===
window, min_periods = 60, 30
ic_list = []
for i in range(window, len(df)):
    fac_win = df['close'].iloc[i-window:i]
    ret_win = df['ret5'].iloc[i-window:i]
    mask = fac_win.notna() & ret_win.notna()
    if mask.sum() < min_periods:
        ic_list.append(np.nan)
    else:
        ic, _ = spearmanr(fac_win[mask].values, ret_win[mask].values)
        ic_list.append(ic)
ref_ic = pd.Series(ic_list, index=df.index[window:])

# === Phase2 implementation (buggy) ===
def spearman_corr_phase2(x, aligned, min_periods):
    if len(x) < min_periods:
        return np.nan
    idx = x.index
    y = aligned.loc[idx, 'ret5']
    if isinstance(y, pd.DataFrame):
        return np.nan
    if len(y) < min_periods:
        return np.nan
    ic, _ = spearmanr(x.values, y.values)
    return ic

rolling_ic = aligned['factor'].rolling(window=window, min_periods=min_periods).apply(
    lambda x: spearman_corr_phase2(x, aligned, min_periods), raw=False
)

# === Compare at specific position ===
pos = 825
ref_val = ref_ic.iloc[pos - window]  # ref_ic is indexed by df.index, at position pos-window in ref_ic corresponds to df index position pos
# Actually ref_ic is aligned to df.index[window:]
print(f'\n=== At position {pos} ===')
print(f'Reference window df[{pos-window}:{pos}] dates: {list(df.index[pos-window:pos])}')
print(f'Phase2 window aligned[{pos-window}:{pos}] dates: {list(aligned.index[pos-window:pos])}')
print(f'Same dates? {list(df.index[pos-window:pos]) == list(aligned.index[pos-window:pos])}')

# The dates ARE the same (since aligned = df.dropna() preserves order)
# So why is Phase2 different?

# === Let me check: what if there's a duplicate index issue? ===
dupes = aligned.index[aligned.index.duplicated()]
print(f'\nDuplicate dates in aligned: {len(dupes)}')
if len(dupes) > 0:
    print(f'First few dupes: {list(dupes[:5])}')

# === Actually, let me manually compute Phase2 at position 825 ===
x = aligned['factor'].iloc[pos-window:pos]
y = aligned['ret5'].iloc[pos-window:pos]
print(f'\nx (factor) values[:5]: {x.values[:5]}')
print(f'y (ret5)   values[:5]: {y.values[:5]}')
ic_p2_manual, _ = spearmanr(x.values, y.values)
print(f'Manual Phase2 IC at pos {pos}: {ic_p2_manual:.6f}')

# === Reference at the corresponding position ===
# Reference iterates df by position i
# At i=pos=825, reference uses df[825-60:825] = df[765:825]
# These are df positions 765..824
# But aligned[765:825] = df[770:830] (because 5 rows were dropped from aligned)
# So Phase2 at aligned[765:825] = df[770:830]
# Reference at df[765:825]

# Let me verify by checking df positions
print(f'\ndf[765:825] factor[:5]: {df["close"].iloc[765:770].values}')
print(f'df[770:830] factor[:5]: {df["close"].iloc[770:775].values}')
print(f'aligned[765:825] factor[:5]: {aligned["factor"].iloc[765:770].values}')
print(f'aligned[765:825] corresponds to df[770:830]: {np.allclose(aligned["factor"].iloc[765:770].values, df["close"].iloc[770:775].values)}')
