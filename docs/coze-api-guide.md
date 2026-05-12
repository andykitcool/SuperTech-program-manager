# COZE 智能体 API 指南

本文档供 COZE 智能体使用，用于通过 API 查询节目信息并返回节目素材详情页链接给用户。

---

## 基础信息

| 项目 | 值 |
|------|-----|
| API 基础地址 | `https://your-domain.com/api/public` |
| 认证方式 | 无需认证（公开接口） |
| 响应格式 | JSON |
| 字符编码 | UTF-8 |

> 部署后请将 `https://your-domain.com` 替换为实际的服务域名。

---

## 核心工作流

```
用户提问 → 智能体收集信息 → 调用搜索API → 返回节目链接
```

### 智能体信息收集策略

与用户交流时，逐步收集以下信息：

1. **必要信息**（至少一项）：
   - 节目号（数字，如 `5`、`12`）
   - 节目名（文字，如 `小星星`、`芭蕾舞`）

2. **辅助筛选信息**（可选，用于缩小范围）：
   - 活动名称（如 `2025春季展演`）
   - 活动日期（如 `2025-05-01`）

> 当搜索结果有多个匹配时，活动名称/日期可帮助精准定位。如果用户只提供了节目号/名且结果唯一，可直接返回。

---

## API 接口

### 1. 跨活动搜索节目（核心接口）

这是 COZE 智能体最常用的接口，支持跨所有活动搜索节目。

**请求**

```
GET /api/public/programs/search
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `q` | string | **是** | 节目号或节目名关键词 |
| `activity_name` | string | 否 | 活动名称（模糊匹配） |
| `activity_date` | string | 否 | 活动日期，格式 `YYYY-MM-DD` |

**请求示例**

示例 1：仅通过节目号搜索
```
GET /api/public/programs/search?q=5
```

示例 2：通过节目名 + 活动名称搜索
```
GET /api/public/programs/search?q=小星星&activity_name=春季展演
```

示例 3：通过节目号 + 活动日期搜索
```
GET /api/public/programs/search?q=12&activity_date=2025-05-01
```

**响应**

```json
[
  {
    "id": 42,
    "name": "小星星",
    "sequence_number": 5,
    "access_token": "a3b5c7d9e1f2",
    "photo_count": 15,
    "video_status": "ready",
    "activity_id": 3,
    "activity_name": "2025春季少儿舞蹈展演",
    "activity_event_date": "2025-05-01",
    "activity_venue": "星光剧院"
  }
]
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 节目ID |
| `name` | string | 节目名称 |
| `sequence_number` | int | 节目号（序号） |
| `access_token` | string | 访问令牌，用于构造详情页链接 |
| `photo_count` | int | 照片数量 |
| `video_status` | string | 视频状态：`none`（无视频）、`uploading`（上传中）、`ready`（可观看） |
| `activity_id` | int | 所属活动ID |
| `activity_name` | string | 所属活动名称 |
| `activity_event_date` | string | 活动日期 |
| `activity_venue` | string | 活动地点 |

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 400 | 缺少 `q` 参数或 `activity_date` 格式错误 |
| 200 | 空数组 `[]` 表示未找到匹配节目 |

**构造详情页链接**

搜索结果中的 `access_token` 用于构造节目素材详情页链接：

```
https://your-domain.com/p/{access_token}
```

例如：`https://your-domain.com/p/a3b5c7d9e1f2`

用户点击该链接即可在微信浏览器中打开节目素材详情页，观看视频和下载照片。

---

### 2. 获取公开活动列表

获取所有当前活跃的活动，可用于向用户展示可选活动。

**请求**

```
GET /api/public/activities
```

**参数**

无

**响应**

```json
[
  {
    "id": 1,
    "name": "2025春季少儿舞蹈展演",
    "description": "年度春季展演活动",
    "event_date": "2025-05-01",
    "start_time": "09:00:00",
    "end_time": "17:00:00",
    "venue": "星光剧院",
    "cover_image": "https://cdn.example.com/cover.jpg",
    "program_count": 25,
    "photo_count": 300
  },
  {
    "id": 2,
    "name": "2025夏季汇报演出",
    "event_date": "2025-07-15",
    "start_time": "14:00:00",
    "end_time": "18:00:00",
    "venue": "大剧院",
    "cover_image": null,
    "program_count": 18,
    "photo_count": 200
  }
]
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 活动ID |
| `name` | string | 活动名称 |
| `description` | string\|null | 活动描述 |
| `event_date` | string\|null | 活动日期 |
| `start_time` | string\|null | 开始时间 |
| `end_time` | string\|null | 结束时间 |
| `venue` | string\|null | 活动地点 |
| `cover_image` | string\|null | 封面图URL |
| `program_count` | int | 已就绪节目数 |
| `photo_count` | int | 照片总数 |

---

### 3. 获取活动详情

获取单个活动的详细信息。

**请求**

```
GET /api/public/activities/{activity_id}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `activity_id` | int | 是 | 活动ID（路径参数） |

**响应**

```json
{
  "id": 1,
  "name": "2025春季少儿舞蹈展演",
  "description": "年度春季展演活动",
  "event_date": "2025-05-01",
  "start_time": "09:00:00",
  "end_time": "17:00:00",
  "venue": "星光剧院",
  "cover_image": "https://cdn.example.com/cover.jpg",
  "share_config": {},
  "program_count": 25,
  "photo_count": 300
}
```

---

### 4. 活动内搜索节目

在指定活动内搜索节目。需要先知道活动ID。

**请求**

```
GET /api/public/activities/{activity_id}/programs/search?q={keyword}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `activity_id` | int | 是 | 活动ID（路径参数） |
| `q` | string | 否 | 节目号或节目名关键词 |

**响应**

```json
[
  {
    "id": 42,
    "name": "小星星",
    "sequence_number": 5,
    "access_token": "a3b5c7d9e1f2",
    "photo_count": 15,
    "video_status": "ready"
  }
]
```

> **注意**：此接口需要 `activity_id`，建议优先使用"跨活动搜索节目"接口。

---

### 5. 获取节目详情

通过节目的访问令牌获取节目详细信息。

**请求**

```
GET /api/public/programs/{token}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `token` | string | 是 | 节目访问令牌（路径参数） |

**响应**

```json
{
  "id": 42,
  "name": "小星星",
  "sequence_number": 5,
  "video_url": "https://cdn.example.com/video.mp4",
  "video_status": "ready",
  "photo_count": 15,
  "access_token": "a3b5c7d9e1f2"
}
```

---

## 典型对话流程示例

### 场景 1：用户提供节目号

```
用户：我想看5号节目的视频
智能体：
  1. 调用 GET /api/public/programs/search?q=5
  2. 若结果唯一：返回链接 "您的5号节目《小星星》素材已就绪，请点击查看：https://your-domain.com/p/a3b5c7d9e1f2"
  3. 若结果多个：提示用户选择活动
     "找到多个5号节目：
      1. 春季展演 - 小星星
      2. 夏季演出 - 芭蕾舞
      请问是哪个活动的？"
```

### 场景 2：用户提供活动名称 + 节目名

```
用户：春季展演的小星星节目
智能体：
  1. 调用 GET /api/public/programs/search?q=小星星&activity_name=春季展演
  2. 返回链接 "春季展演的小星星节目素材已就绪，请点击查看：https://your-domain.com/p/a3b5c7d9e1f2"
```

### 场景 3：用户提供日期 + 节目号

```
用户：5月1号的活动，12号节目
智能体：
  1. 调用 GET /api/public/programs/search?q=12&activity_date=2025-05-01
  2. 返回链接
```

### 场景 4：未找到结果

```
用户：我要看99号节目
智能体：
  1. 调用 GET /api/public/programs/search?q=99
  2. 返回空数组
  3. 回复 "抱歉，未找到99号节目，请确认节目号是否正确。您可以告诉我活动名称来缩小搜索范围。"
```

### 场景 5：节目素材未就绪

```
智能体检查 video_status：
  - "ready"：视频已就绪，正常返回链接
  - "uploading"：视频上传中，提示用户稍后再试
  - "none"：视频暂无，提示用户仅可查看照片
```

---

## 重要提示

1. **链接构造**：节目详情页链接格式为 `https://your-domain.com/p/{access_token}`，务必将搜索结果中的 `access_token` 替换到链接中。
2. **仅返回就绪节目**：搜索接口只返回 `ready_status=ready` 的节目，未就绪的节目不会出现在搜索结果中。
3. **模糊匹配**：`activity_name` 和 `q` 参数均为模糊匹配（包含即可），无需精确输入。
4. **结果限制**：搜索接口最多返回 50 条结果，建议引导用户提供更精确的筛选条件。
5. **节目号 vs 节目名**：当 `q` 为纯数字时，会同时匹配节目号（`sequence_number`）和节目名；当 `q` 为文字时，仅匹配节目名。
