import sys, os, time
sys.path.insert(0, r'D:\futures_v6')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

results = []

try:
    from vnpy.event import EventEngine
    from vnpy_ctp import CtpGateway

    ee = EventEngine()
    gw = CtpGateway(ee, 'CTP')
    results.append(f'Gateway created: {gw.gateway_name}')

    # Try connecting with Chinese keys
    conn_params = {
        '用户名': '260345',
        '密码': 'luzc19891222@',
        '经纪商代码': '9999',
        '交易服务器': '182.254.243.31:30001',
        '行情服务器': '182.254.243.31:30011',
        '产品名称': 'simnow_client_test',
        '授权编码': '0000000000000000',
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
