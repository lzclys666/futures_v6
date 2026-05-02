"""检查 ratio 文件到底是 CU/AL 还是 AL/CU"""
import pandas as pd

cu = pd.read_csv(r'D:\futures_v6\macro_engine\data\crawlers\CU\daily\CU_fut_close.csv', parse_dates=['date'])
al = pd.read_csv(r'D:\futures_v6\macro_engine\data\crawlers\AL\daily\AL_fut_close.csv', parse_dates=['date'])
ratio = pd.read_csv(r'D:\futures_v6\macro_engine\data\crawlers\shared\daily\CU_AL_ratio.csv', parse_dates=['date'])

cu = cu.set_index('date')['close']
al = al.set_index('date')['close']
ratio = ratio.set_index('date')['ratio']

# 找共同日期
common = ratio.index.intersection(cu.index).intersection(al.index)
print('共同日期数:', len(common))

# 对齐
r = ratio.loc[common]
c = cu.loc[common]
a = al.loc[common]

# 两种比价
cu_al = c / a
al_cu = a / c

corr_direct = r.corr(cu_al)
corr_inv = r.corr(al_cu)
print('ratio vs CU/AL:', corr_direct)
print('ratio vs AL/CU:', corr_inv)

print('\nLatest values:')
print('  ratio file:', r.iloc[-1])
print('  CU/AL:', cu_al.iloc[-1])
print('  AL/CU:', al_cu.iloc[-1])
print('  CU price:', c.iloc[-1])
print('  AL price:', a.iloc[-1])

# 判断
if abs(corr_direct) > abs(corr_inv):
    print('\n结论: ratio = CU/AL (直接比价)')
else:
    print('\n结论: ratio = AL/CU (反向比价)')
