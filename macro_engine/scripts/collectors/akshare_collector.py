import akshare as ak
from typing import Dict, Any
import pandas as pd
import logging

# 配置日志（若外部已配置，此处可省略）
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def collect_factor(factor_code: str, api_params: Dict[str, Any]) -> Dict[str, Any]:
    if factor_code == "RU_MAIN":
        return collect_futures_main(api_params)
    elif factor_code == "CU_MAIN":
        return collect_futures_main(api_params)
    elif factor_code == "GDP":
        return collect_macro_china_gdp()
    else:
        raise ValueError(f"Unsupported factor code: {factor_code}")

def collect_futures_main(api_params: Dict[str, Any]) -> Dict[str, Any]:
    symbol = api_params.get("symbol")
    # exchange 参数已移除，akshare 新版不再需要
    try:
        data = ak.futures_main_sina(symbol=symbol)
        if data.empty:
            raise ValueError(f"No data found for symbol: {symbol}")
        logging.info(f"Successfully collected futures data for {symbol}")
        return data.to_dict(orient="records")
    except Exception as e:
        logging.error(f"Failed to collect futures data for {symbol}: {e}")
        raise RuntimeError(f"Failed to collect futures data for {symbol}: {e}")

def collect_macro_china_gdp() -> Dict[str, Any]:
    try:
        data = ak.macro_china_gdp()
        if data.empty:
            raise ValueError("No GDP data found")
        logging.info("Successfully collected GDP data")
        return data.to_dict(orient="records")
    except Exception as e:
        logging.error(f"Failed to collect GDP data: {e}")
        raise RuntimeError(f"Failed to collect GDP data: {e}")