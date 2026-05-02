import glob
files = glob.glob(r'D:\futures_v6\**\macro_api_server.py', recursive=True)
for f in files:
    print(f)
