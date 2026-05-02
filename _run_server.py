import sys
sys.path.insert(0, r'D:\futures_v6\api')
sys.path.insert(0, r'D:\futures_v6\macro_engine')
sys.path.insert(0, r'D:\futures_v6')
try:
    import uvicorn
    from macro_api_server import app
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='info')
except Exception as e:
    import traceback
    traceback.print_exc()
    input('Press Enter to exit...')