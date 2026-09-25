import pandas as pd
import importlib.util

spec = importlib.util.spec_from_file_location(
    'mainmod',
    'c:/Users/arthu/OneDrive/Documentos/Folders/Programming/Python/macroframework/main.py'
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

base = pd.Timestamp('2024-01-01')
series_a = pd.Series([1, 2, 3, 4], index=pd.date_range(base, periods=4, freq='MS'))
series_b = pd.Series([10, 20, 30, 40], index=pd.date_range(base, periods=4, freq='W'))
series_c = pd.Series([100, 200], index=pd.date_range(base, periods=2, freq='D'))
job = pd.Series([50, 60, 70, 80], index=pd.date_range(base, periods=4, freq='MS'))
unemp = pd.Series([5, 6, 7, 8], index=pd.date_range(base, periods=4, freq='MS'))

def fake(code):
    lookup = {
        'A': series_a,
        'B': series_b,
        'C': series_c,
        'JTSJOL': job,
        'UNEMPLOY': unemp,
    }
    return lookup[code]

mod.SERIES_MAP = {
    'A': ('A', 'monthly', 'A', 'level'),
    'B': ('B', 'weekly', 'B', 'level'),
    'C': ('C', 'daily', 'C', 'level'),
}
mod.get_fred_series_with_retry = fake
result = mod.build_last_12_months_dataframe()
print(result.head().to_string())
print('COLUMNS:', result.columns.tolist())
print('MIN_DATE:', result.index.min())
print('MAX_DATE:', result.index.max())
print('SHAPE:', result.shape)
