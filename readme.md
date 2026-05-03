# SuperTech Program Manager

少儿舞蹈展演素材交付系统，管理展演活动中的视频与照片素材，提供管理后台和家长端两个访问入口。

## 功能概览

### 管理后台

- **活动管理** — 创建/编辑/删除展演活动，支持活动主图、开始/结束时间、地点和喔图相册配置
- **节目管理** — 单个/批量/Excel 导入节目，自动生成访问令牌，支持按节目号或节目名搜索
- **视频上传** — 支持七牛客户端直传，OBS 自动推送上传
- **照片同步与管理** — 活动详情内配置喔图相册并同步照片，按拍摄时间自动匹配到节目，支持查看已同步照片
- **打印管理** — 支持照片打印、打印记录、重打操作和活动级打印模板配置
- **定制分享与观众管理** — 支持活动分享封面/标题/描述配置，记录微信观众信息并提供观众管理
- **就绪判定** — 自动模式（视频+照片齐即就绪）或手动模式
- **系统设置** — 云存储、蓝阔云打印、微信服务号配置和连接测试
- **同步记录** — 查看照片同步操作历史

### 家长端

- 通过 `/p/index` 浏览所有活动卡片
- 通过 `/p/:activityId` 查看活动详情，家长可输入节目号或节目名搜索节目
- 通过 `/p/:token` 访问节目素材交付页，查看视频与照片，支持照片预览、下载和打印
- 在微信浏览器内访问时支持获取 openid、头像和昵称，用于观众记录和打印记录关联

## 近期改动总结

### 管理后台体验

- 活动创建页移除了活动描述，新增活动主图上传、活动开始日期时间和结束日期时间选择。
- 活动管理卡片改为 4:3 布局，上半部分使用 16:9 主图，无主图时显示默认图；活动状态根据开始/结束时间自动判断。
- 活动卡片展示节目数、已就绪数、活动时间、活动地点和右下角快捷操作；状态标签改为高对比胶囊样式，避免受主图影响。
- 活动详情页增加多个 Tab：节目管理、照片同步、照片管理、打印记录、打印模板、定制分享、观众管理。
- 节目管理 Tab 将“序号”改为“节目号”，并增加按节目号/节目名筛选搜索。
- 侧栏“照片同步”改名为“同步记录”，页面只保留同步操作历史；系统设置移动到侧栏底部。
- 修改管理员密码功能改为从右上角 admin 悬停菜单进入。

### 照片同步与打印

- 喔图抓取规则兼容 `/rest/v4c/fplN/` 这类接口路径，解决新版接口无法识别的问题。
- 照片同步功能放入活动详情页，可配置相册 URL 并启动同步。
- 照片管理 Tab 展示已同步照片，并在照片上提供打印操作。
- 打印记录 Tab 支持自动轮询刷新后端打印记录，管理员可对记录执行重打。
- 打印模板 Tab 支持设置每用户免费打印次数、纸张大小、贴纸、边框、文字和底图；活动级纸张大小会覆盖系统打印机配置。
- 素材交付页照片预览弹窗重做样式，增加打印图标。

### 系统设置

- 系统设置由卡片式布局调整为 Tab 切换。
- 云存储配置支持阿里云、腾讯云、七牛云启用开关和参数配置。
- 新增蓝阔云打印配置项，包括商户/设备、打印机类型、纸张尺寸、回调和打印选项等。
- 新增微信服务号 appid、appsecret、OAuth scope 等配置。

### 家长端与微信

- 新增 `/p/index` 活动列表页，用于展示所有活动卡片。
- 新增 `/p/:activityId` 活动详情页，用于展示活动信息并支持节目搜索跳转。
- 家长端访问时支持微信 OAuth 获取 openid、头像、昵称，并上报观众访问记录。
- 观众管理中用户 ID 仅展示 openid 后 6 位，并精简首次观看时间和终端列。

### 部署与运行

- 网页标题从 `Vite + Vue + TS` 改为 `SuperTech快速交付系统`。
- Nginx 增加 `/uploads/` 代理，支持访问活动主图等上传资源。
- Docker Compose 为 API 容器挂载 `server/uploads`，保留上传文件目录。
- 本地运行时上传文件已加入 Git 忽略，仅保留目录占位文件。

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
| 家长端活动列表 | http://localhost:3000/p/index |
| 家长端活动详情 | http://localhost:3000/p/:activityId |
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
| POST | `/admin/activities/cover/upload` | 上传活动主图 |
| GET | `/admin/activities/{id}/print-records` | 活动打印记录 |
| POST | `/admin/activities/{id}/print-records` | 创建打印记录 |
| POST | `/admin/print-records/{id}/reprint` | 重打 |
| GET | `/admin/activities/{id}/audiences` | 活动观众列表 |
| POST | `/admin/audiences/{id}/blacklist` | 更新观众黑名单 |

### 家长端 `/api/public`（access_token 访问）

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/public/programs/{token}` | 获取节目信息 |
| GET | `/public/programs/{token}/photos` | 获取节目照片 |
| POST | `/public/programs/{token}/photos/{photo_id}/print` | 家长端照片打印 |
| GET | `/public/activities` | 获取公开活动列表 |
| GET | `/public/activities/{id}` | 获取公开活动详情 |
| GET | `/public/activities/{id}/programs/search` | 按节目号或节目名搜索节目 |
| GET | `/public/wechat/config` | 获取微信服务号配置状态 |
| GET | `/public/wechat/oauth-url` | 获取微信 OAuth 跳转地址 |
| GET | `/public/wechat/oauth-profile` | 微信 OAuth 换取用户资料 |
| POST | `/public/wechat/track` | 上报微信观众访问记录 |

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
                  └──────────────────────1:N──> PrintRecord (打印记录)
                  └──────────────────────1:N──> Audience (观众)
```

- **Activity** — 展演活动，关联喔图相册、活动主图、开始/结束时间
- **Program** — 节目，核心实体，含 `access_token` 供家长端访问
- **Video** — 视频文件记录
- **Photo** — 照片记录，可按拍摄时间自动匹配到节目
- **PrintRecord** — 打印记录，关联活动、节目、照片和微信用户
- **Audience** — 观众记录，保存微信 openid、昵称、头像、访问状态和黑名单状态
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
