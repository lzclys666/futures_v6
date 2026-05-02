"""
Stage 2: PIT 端到端验证 - 从 PIT 读 CU_AL_ratio，算 IC
"""
import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')

# 1. 从 PIT 读 CU_AL_ratio
ratio_pit = pd.read_sql(
    "SELECT obs_date, raw_value FROM pit_factor_observations "
    "WHERE factor_code='CU_AL_ratio' ORDER BY obs_date",
    conn
)
ratio_pit['date'] = pd.to_datetime(ratio_pit['obs_date'])
ratio_pit = ratio_pit.drop_duplicates(subset='date', keep='first')  # Bug 3 fix
ratio_pit.set_index('date', inplace=True)
ratio_pit = ratio_pit['raw_value']
print("CU_AL_ratio PIT: {} rows ({} ~ {})".format(
    len(ratio_pit), ratio_pit.index[0].date(), ratio_pit.index[-1].date()))

# 2. 从 PIT 读 CU 收盘价 (去重)
cu_close = pd.read_sql(
    "SELECT obs_date, raw_value FROM pit_factor_observations "
    "WHERE symbol='CU' AND factor_code NOT LIKE '%ratio%' ORDER BY obs_date",
    conn
)
cu_close['date'] = pd.to_datetime(cu_close['obs_date'])
cu_close = cu_close.drop_duplicates(subset='date', keep='first')  # Bug 3 fix
cu_close.set_index('date', inplace=True)
cu_close = cu_close['raw_value']
print("CU close PIT: {} rows ({} ~ {})".format(
    len(cu_close), cu_close.index[0].date(), cu_close.index[-1].date()))

conn.close()

# 3. 合并 (inner join 只保留共同日期)
print("\n=== Rolling IC (PIT 数据) ===")
df = pd.DataFrame({'ratio': ratio_pit, 'cu_close': cu_close})
df = df[~df.index.duplicated(keep='first')]  # 再去一次
print("合并后: {} rows".format(len(df)))

# 对齐：只保留两者都有数据的日期
df_aligned = df.dropna()
print("去NA后: {} rows".format(len(df_aligned)))

for hold in [10, 20]:
    fwd = df_aligned['cu_close'].pct_change(hold).shift(-hold)
    aligned = pd.DataFrame({'f': df_aligned['ratio'], 'r': fwd}).dropna()
    WINDOW = 60
    ic_list = []
    for i in range(WINDOW, len(aligned)):
        fw = aligned['f'].iloc[i-WINDOW:i].values
        rw = aligned['r'].iloc[i-WINDOW:i].values
        if len(fw) < 30:
            continue
        ic, _ = spearmanr(fw, rw)
        if not np.isnan(ic):
            ic_list.append(ic)
    s = pd.Series(ic_list)
    m = s.mean()
    std = s.std()
    t = m / (std / np.sqrt(len(s))) if std > 0 else 0
    win = (s > 0).mean()
    q = "GOOD" if m > 0.2 else ("OK" if m > 0.1 else "WEAK")
    print("  {}d IC={:+.4f}  IR={:+.4f}  t={:+.2f}  win={:.1%}  [{}]".format(
        hold, m, m/std if std > 0 else 0, t, win, q))

print("\nStage 2 端到端验证完成")
