# SuperTech Program Manager

少儿舞蹈展演素材交付系统，管理展演活动中的视频与照片素材，提供管理后台和家长端两个访问入口。

## 功能概览

### 管理后台

- **活动管理** — 创建/编辑/删除展演活动，关联喔图相册
- **节目管理** — 单个/批量/Excel 导入节目，自动生成访问令牌
- **视频上传** — 支持七牛客户端直传，OBS 自动推送上传
- **照片管理** — 喔图平台照片同步，按拍摄时间自动匹配到节目
- **就绪判定** — 自动模式（视频+照片齐即就绪）或手动模式
- **系统设置** — 云存储配置、连接测试
- **喔图同步** — 爬取喔图相册 → 下载照片 → 上传云存储 → 匹配节目

### 家长端

- 通过 COZE 智能体返回的链接（`/p/:token`）访问节目详情
- 查看节目视频与照片，无需登录

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + TypeScript + Ant Design Vue + Pinia + Vue Router |
| 后端 | FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Uvicorn |
| 数据库 | MySQL 8.0 |
| 云存储 | 阿里云 OSS / 腾讯云 COS / 七牛（适配器模式） |
| 部署 | Docker Compose + Nginx |

## 快速启动

### 前置要求

- Docker & Docker Compose

### 启动服务

```bash
docker compose up -d
```

启动完成后访问：

| 页面 | 地址 |
|------|------|
| 管理员登录 | http://localhost:3000/admin/login |
| 管理后台 | http://localhost:3000/admin |
| 家长端节目 | http://localhost:3000/p/:token |

### 默认管理员账号

| 用户名 | 密码 |
|--------|------|
| admin | admin123 |

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| web | 3000 | Nginx 托管前端 + 反向代理 API |
| api | 8000 | FastAPI 后端 |
| db | 3306 | MySQL 数据库 |

## 项目结构

```
├── docker-compose.yml        # Docker Compose 编排
├── server/                   # 后端
│   ├── app/
│   │   ├── main.py           # 应用入口
│   │   ├── config.py         # 配置管理
│   │   ├── database.py       # 数据库连接
│   │   ├── models/           # SQLAlchemy 模型
│   │   ├── schemas/          # Pydantic Schema
│   │   ├── api/              # API 路由
│   │   │   ├── admin.py      # 管理后台 CRUD
│   │   │   ├── public.py     # 家长端公开接口
│   │   │   ├── upload.py     # 上传接口
│   │   │   ├── settings.py   # 系统设置
│   │   │   └── wotu.py       # 喔图同步
│   │   ├── services/         # 业务逻辑
│   │   ├── storage/          # 云存储适配器
│   │   ├── tasks/            # 定时任务
│   │   └── utils/            # 工具函数
│   ├── migrations/           # 数据库迁移
│   ├── Dockerfile
│   └── requirements.txt
├── web/                      # 前端
│   ├── src/
│   │   ├── views/admin/      # 管理后台页面
│   │   ├── views/public/     # 家长端页面
│   │   ├── api/              # API 调用封装
│   │   ├── stores/           # Pinia 状态管理
│   │   ├── router/           # 路由配置
│   │   └── styles/           # 全局样式
│   ├── nginx.conf            # Nginx 配置
│   ├── Dockerfile
│   └── package.json
└── readme.md
```

## API 概览

### 管理后台 `/api/admin`（需 JWT 认证）

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/admin/login` | 管理员登录 |
| GET/POST | `/admin/activities` | 活动列表 / 创建活动 |
| GET/PUT/DELETE | `/admin/activities/{id}` | 活动详情 / 更新 / 删除 |
| GET/POST | `/admin/activities/{id}/programs` | 节目列表 / 创建节目 |
| POST | `/admin/activities/{id}/programs/batch` | 批量创建节目 |
| POST | `/admin/activities/{id}/programs/import` | Excel 导入节目 |
| PUT/DELETE | `/admin/programs/{id}` | 更新 / 删除节目 |
| POST | `/admin/sync/start` | 启动喔图同步 |
| POST | `/admin/sync/stop` | 停止喔图同步 |
| GET | `/admin/sync/status` | 同步状态 |
| GET | `/admin/sync/history` | 同步历史 |
| GET | `/admin/photos/activities` | 有照片的活动 |
| GET | `/admin/photos/activity/{id}` | 活动照片列表 |

### 家长端 `/api/public`（access_token 访问）

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/public/programs/{token}` | 获取节目信息 |
| GET | `/public/programs/{token}/photos` | 获取节目照片 |

### 其他

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/upload/video/token` | 获取七牛上传凭证 |
| POST | `/upload/video/confirm` | 确认视频上传 |
| POST | `/upload/auto/{activity_id}/{program_name}` | OBS 自动推送 |
| GET/PUT | `/settings` | 系统设置管理 |
| POST | `/settings/storage/test` | 测试云存储连接 |
| GET | `/api/health` | 健康检查 |

## 数据模型

```
Activity (活动) ──1:N──> Program (节目) ──1:N──> Video (视频)
                  └──────────────────────1:N──> Photo (照片)
```

- **Activity** — 展演活动，关联喔图相册
- **Program** — 节目，核心实体，含 `access_token` 供家长端访问
- **Video** — 视频文件记录
- **Photo** — 照片记录，可按拍摄时间自动匹配到节目
- **SystemSettings** — KV 配置存储
- **SyncTask** — 喔图同步任务记录

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DB_HOST` | localhost | 数据库主机 |
| `DB_PORT` | 3306 | 数据库端口 |
| `DB_USER` | root | 数据库用户 |
| `DB_PASSWORD` | — | 数据库密码 |
| `DB_NAME` | supertech_pm | 数据库名 |
| `JWT_SECRET_KEY` | — | JWT 签名密钥 |
| `JWT_EXPIRE_MINUTES` | 1440 | Token 有效期（分钟） |
| `DEFAULT_STORAGE_PROVIDER` | aliyun | 默认云存储 |

## 本地开发

### 后端

```bash
cd server
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd web
npm install
npm run dev
```

> 前端开发时需将 API 请求代理到后端 `http://localhost:8000`，可在 `vite.config.ts` 中配置 proxy。

## License

Private
