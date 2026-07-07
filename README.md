# AI Berkshire — 本地个人投资理财工作台

基于 [ai-berkshire](https://github.com/xbtlin/ai-berkshire) 价值投资研究框架构建的本地个人投资理财、股票复盘与资产配置工作台。

本项目当前按“个人本地使用”规划：前后端运行在你的电脑上，数据库保存在本机 SQLite，GitHub 用于托管代码和版本备份，不把个人财务数据提交到仓库。

## 项目结构

```
ai-berkshire-web/
├── backend/          # FastAPI 后端服务
│   ├── app/
│   │   ├── api/      # REST API 路由
│   │   ├── core/     # 配置、安全、中间件
│   │   ├── models/   # SQLAlchemy 数据模型
│   │   ├── services/ # 业务逻辑层
│   │   ├── utils/    # 工具函数
│   │   ├── ai_skills/# AI Berkshire skills 集成
│   │   └── data/     # 数据层（行情、新闻、公告）
│   └── requirements.txt
├── frontend/         # Next.js 前端应用
│   ├── src/
│   │   ├── app/      # Next.js App Router 页面
│   │   ├── components/ # React 组件
│   │   ├── hooks/    # 自定义 React Hooks
│   │   ├── lib/      # 工具库、API 客户端
│   │   └── types/    # TypeScript 类型定义
│   └── public/       # 静态资源
└── README.md
```

## 核心功能

- **每日市场复盘**: AI 自动生成结构化市场复盘报告
- **四大师投研框架**: 段永平/巴菲特/芒格/李录 多视角分析
- **自选股管理**: 跟踪关注股票，AI 每日摘要
- **持仓组合分析**: 收益统计、风险暴露、集中度检查
- **投资日志**: 记录交易决策，AI 行为复盘
- **公告/财报解读**: PDF 上传，AI 结构化分析
- **资产配置**: 风险偏好评估与再平衡建议
- **新闻脉搏**: 股价异动快速归因

## 个人本地部署方案

| 项目 | 方案 |
|------|------|
| 运行方式 | 本机启动前端 + 后端 |
| 前端 | Next.js, http://localhost:3000 |
| 后端 | FastAPI, http://localhost:8000 |
| 数据库 | SQLite, `backend/ai_berkshire.db` |
| 代码托管 | GitHub |
| 个人数据 | 本机保存，默认不进 Git |
| 备份 | `./scripts/backup_db.sh` 生成本地数据库备份 |

详细说明见 [docs/LOCAL_PERSONAL_DEPLOY.md](docs/LOCAL_PERSONAL_DEPLOY.md)。GitHub 同步说明见 [docs/GITHUB_SYNC.md](docs/GITHUB_SYNC.md)。

## 快速开始

### 首次初始化

```bash
chmod +x start.sh
chmod +x scripts/*.sh
./scripts/init_local.sh
```

### 一键启动（推荐）

```bash
./start.sh
```

### 方式二：手动启动

#### 后端
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 初始化数据库
python3 -c "from app.models.database import engine, Base; from app.data.seed_data import seed_all; Base.metadata.create_all(bind=engine); seed_all()"

# 启动服务
python3 run.py
```

#### 前端
```bash
cd frontend
npm install
npm run dev
```

## 默认访问

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/api/docs |

### 默认账号
- 用户名: `demo`
- 密码: `demo123456`

## 数据备份与恢复

备份本地个人数据库：

```bash
./scripts/backup_db.sh
```

恢复备份：

```bash
./scripts/restore_db.sh backups/ai_berkshire-YYYYMMDD-HHMMSS.db
```

`backups/` 和 `backend/ai_berkshire.db` 默认被 `.gitignore` 忽略，不会提交到 GitHub。

## 技术栈

- **前端**: Next.js 14, React 18, TypeScript, Tailwind CSS, Recharts
- **后端**: Python 3.10+, FastAPI, SQLAlchemy, SQLite (MVP)
- **AI**: OpenAI / DeepSeek API (可选，无 API key 时返回模拟数据)
- **数据**: 免费金融数据源优先，失败自动降级到本地兜底数据

## 免费金融 API

当前行情接入不需要付费 key：

| 市场 | 默认数据源 | 用途 |
|------|------------|------|
| A 股指数 | 新浪财经实时行情 | 上证指数、深证成指、创业板指、科创50、沪深300 |
| A 股个股 | 新浪财经实时行情 | 自选股、持仓、个股详情 |
| 美股/港股 | Yahoo Finance chart API | 美股/港股个股详情 |
| A 股排行 | AkShare（可选） | 涨跌排行、市场广度；超时自动降级 |

关键环境变量：

```bash
USE_REAL_DATA=true
NETWORK_TIMEOUT=3
ENABLE_AKSHARE_BREADTH=false
```

`ENABLE_AKSHARE_BREADTH=false` 是线上推荐默认值，可避免首页为了全市场广度统计等待较重的 AkShare 请求。需要更完整的 A 股排行时可改为 `true`。

## 环境变量

复制 `backend/.env.example` 为 `backend/.env` 并配置：

```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./ai_berkshire.db
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=...
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
USE_REAL_DATA=true
NETWORK_TIMEOUT=3
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

复制 `frontend/.env.example` 为 `frontend/.env.local`：

```bash
NEXT_PUBLIC_API_BASE_URL=/api
API_INTERNAL_URL=http://127.0.0.1:8000
```

线上如果前后端分开部署，将 `NEXT_PUBLIC_API_BASE_URL` 设置为后端公网地址，例如 `https://api.example.com/api`，并在后端 `CORS_ORIGINS` 中加入前端域名。

## Docker 部署

本仓库提供生产 Docker 配置：

```bash
docker compose up --build -d
```

默认端口：

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| 健康检查 | http://localhost:8000/api/health |

Docker 部署默认会设置 `AUTO_SEED_DB=true`，首次启动自动创建 demo 账号和示例数据。

## 验证命令

```bash
# 后端测试
cd backend && python3 -m pytest -q

# 前端类型检查/构建
cd frontend
node ./node_modules/typescript/bin/tsc --noEmit
node ./node_modules/next/dist/bin/next build

# 真实免费行情快速检查
cd backend
python3 - <<'PY'
import asyncio
from app.services.market_service import MarketService

async def main():
    svc = MarketService()
    for ticker in ["600519.SS", "002475.SZ", "AAPL", "00700.HK"]:
        print(ticker, await svc.get_stock_detail(ticker))

asyncio.run(main())
PY
```

## 已修复的 Bug

1. **bcrypt/passlib 兼容性**: `passlib` 与新版本 `bcrypt` 存在兼容性问题，已直接改用 `bcrypt` 库进行密码哈希
2. **useAuth.tsx 文件扩展名**: 包含 JSX 的 hook 文件从 `.ts` 重命名为 `.tsx`
3. **lucide-react 图标导入**: `IdCard` 图标不存在，替换为 `BadgeCheck`
4. **种子数据解包错误**: `journal_items` 中一个元组元素数量不匹配，已修复
5. **路由顺序**: `/api/users/me` 路由被 `/{user_id}` 拦截，已调整顺序
6. **A 股个股详情 500**: 补齐真实行情源，修复不存在的 `_source_akshare_stock_spot` 调用
7. **线上 API 地址写死 localhost**: 前端改为 `NEXT_PUBLIC_API_BASE_URL`/同源 `/api`，Next rewrite 支持 `API_INTERNAL_URL`
8. **港股 Yahoo 代码不兼容**: 自动将 `00700.HK` 归一化为 Yahoo 可识别的 `0700.HK`
9. **首页行情慢**: AkShare 全市场广度统计改为可选开关，默认不阻塞首页

## 当前验证结果

- 后端测试：`2 passed`
- 前端类型检查：通过
- 前端生产构建：通过
- 免费行情实测：`600519.SS`、`002475.SZ` 来自新浪；`AAPL`、`00700.HK` 来自 Yahoo；失败时自动降级到 mock 数据

## 合规声明

> 本平台内容仅用于学习、研究和个人投资复盘，不构成任何投资建议、投资顾问服务或收益承诺。市场有风险，投资需谨慎。用户应结合自身风险承受能力、投资目标和财务状况独立决策。

## License

MIT
