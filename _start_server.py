"""API服务器启动脚本 - 解决__file__路径问题"""
import sys, os, logging, asyncio
from pathlib import Path

# 显式路径设置
BASE = Path(r"D:\futures_v6")
sys.path.insert(0, str(BASE / "macro_engine"))
sys.path.insert(0, str(BASE / "api"))
sys.path.insert(0, str(BASE))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", encoding="utf-8")
logger = logging.getLogger("macro_api")

try:
    from api.macro_api_server import app
    logger.info("App imported successfully.")

    # 启动 uvicorn
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", access_log=False)
except Exception as e:
    logger.error(f"Failed to start: {e}", exc_info=True)
    input("Press Enter to exit...")