# 期货智能交易系统 V6 — 部署文档

## 环境要求

- Node.js 18+
- Python 3.10+
- VNpy 3.x

## 前端部署

```bash
cd futures_trading
npm install
npm run build
```

构建产物在 `dist/` 目录，可部署到任何静态服务器。

## 后端部署

```bash
cd D:\futures_v6
pip install -r requirements.txt
python main.py
```

后端运行在 http://localhost:8000

## 环境变量

复制 `.env.example` 为 `.env.local`：

```bash
VITE_USE_MOCK=true      # 开发环境用 Mock
VITE_USE_MOCK=false     # 生产环境连真实 API
VITE_API_BASE_URL=http://localhost:8000
```

## 端口配置

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 5173 | Vite dev server |
| 后端 | 8000 | FastAPI + VNpy |

## 生产构建

```bash
npm run build
# 或使用 Docker
docker build -t futures-v6 .
```

## 故障排查

- 前端无法连接后端：检查 CORS 配置和 `VITE_API_BASE_URL`
- VNpy 启动失败：检查 CTP 账户配置
- 构建失败：确保 Node.js >= 18
