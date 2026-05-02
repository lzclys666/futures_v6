import subprocess
import sys
import os

# 启动 YIYI 的 API 服务
os.chdir(r'D:\futures_v6\macro_engine\api')
subprocess.Popen([sys.executable, 'main.py'], 
                 stdout=subprocess.PIPE, 
                 stderr=subprocess.PIPE,
                 creationflags=subprocess.CREATE_NEW_CONSOLE)
print("YIYI API 服务已启动在端口 8001")
