import sys, os, time
sys.path.insert(0, r'D:\futures_v6')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# 凭据从环境变量读取（永不硬编码）
VNPY_CTP_USER_ID     = os.getenv("VNPY_CTP_USER_ID",     "PLEASE_SET_ENV")
VNPY_CTP_PASSWORD    = os.getenv("VNPY_CTP_PASSWORD",    "PLEASE_SET_ENV")
VNPY_CTP_BROKER_ID   = os.getenv("VNPY_CTP_BROKER_ID",   "PLEASE_SET_ENV")
VNPY_CTP_TD_SERVER   = os.getenv("VNPY_CTP_TD_SERVER",   "PLEASE_SET_ENV")
VNPY_CTP_MD_SERVER   = os.getenv("VNPY_CTP_MD_SERVER",   "PLEASE_SET_ENV")
VNPY_CTP_APP_ID      = os.getenv("VNPY_CTP_APP_ID",      "PLEASE_SET_ENV")
VNPY_CTP_AUTH_CODE   = os.getenv("VNPY_CTP_AUTH_CODE",   "PLEASE_SET_ENV")

results = []

try:
    from vnpy.event import EventEngine
    from vnpy_ctp import CtpGateway

    ee = EventEngine()
    gw = CtpGateway(ee, 'CTP')
    results.append(f'Gateway created: {gw.gateway_name}')

    # Try connecting with Chinese keys
    conn_params = {
        '用户名': VNPY_CTP_USER_ID,
        '密码': VNPY_CTP_PASSWORD,
        '经纪商代码': VNPY_CTP_BROKER_ID,
        '交易服务器': VNPY_CTP_TD_SERVER,
        '行情服务器': VNPY_CTP_MD_SERVER,
        '产品名称': VNPY_CTP_APP_ID,
        '授权编码': VNPY_CTP_AUTH_CODE,
        '环境': '仿真',
    }
    gw.connect(conn_params)
    results.append(f'connect() called successfully')
    results.append(f'Params used: user={conn_params["用户名"]}, broker={conn_params["经纪商代码"]}')
    results.append(f'td_server={conn_params["交易服务器"]}, md_server={conn_params["行情服务器"]}')

    # Wait a bit for async connection
    time.sleep(5)

    # Check gateway status
    from vnpy.api.ctp import MdApi, TraderApi
    results.append(f'gateway td_api: {gw.td_api}')
    results.append(f'gateway md_api: {gw.md_api}')

    results.append('CTP connection test PASSED')

except Exception as e:
    import traceback
    results.append(f'ERROR: {e}')
    results.append(traceback.format_exc())

# Write results
with open(r'D:\futures_v6\_ctp_test_result.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print('Done, results written')
