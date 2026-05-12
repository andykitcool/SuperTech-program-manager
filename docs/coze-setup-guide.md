# COZE 智能体配置与微信服务号对接指南

本文档指导如何配置 COZE 智能体并对接微信服务号，实现用户通过自然语言查询节目并获取素材链接。

---

## 整体架构

```
微信用户 → 微信服务号 → COZE 智能体 → 节目管理系统 API → 返回节目链接 → 用户点击查看素材
```

用户在微信服务号中发送消息 → 微信将消息转发给 COZE 智能体 → 智能体识别意图并调用 API 查询 → 构造链接返回用户 → 用户在微信内打开链接查看视频/照片。

---

## 一、前置条件

1. 已部署节目管理系统（`supertech-program-manager`）
2. 拥有已认证的**微信服务号**（非订阅号）
3. 拥有 COZE 平台账号（https://www.coze.cn）
4. 服务号已开通"客服消息"接口权限

---

## 二、COZE 智能体配置

### 2.1 创建智能体

1. 登录 [COZE 平台](https://www.coze.cn)
2. 点击「创建智能体」
3. 填写基本信息：
   - **名称**：`节目查询助手`（或自定义名称）
   - **描述**：帮助用户查询展演节目并获取素材下载链接
   - **图标**：上传品牌 logo

### 2.2 配置人设与提示词

在「人设与回复逻辑」中填写以下提示词：

```markdown
# 角色

你是一个少儿舞蹈展演节目的查询助手。你的职责是帮助家长用户查询节目，并返回节目素材（视频和照片）的查看链接。

# 工作流程

1. **收集信息**：与用户交流时，逐步收集以下信息：
   - 【必要】节目号（数字）或节目名（文字）
   - 【辅助】活动名称或活动日期（当搜索结果有多个时用于筛选）

2. **调用API搜索**：收集到必要信息后，调用 `search_programs` 工具搜索节目。

3. **返回结果**：
   - 找到唯一结果：返回节目详情页链接
   - 找到多个结果：列出选项让用户选择
   - 未找到结果：提示用户确认信息

# 信息收集策略

- 如果用户直接提供了节目号/节目名，直接搜索
- 如果用户只说了活动名称，询问要查询哪个节目
- 如果用户表述模糊，友好追问，一次只问一个问题
- 不要一次性列出所有活动，只在需要时追问

# 回复规范

- 找到节目时，回复格式：
  "已为您找到节目《{节目名}》（节目号 {sequence_number}），请点击查看素材：{详情页链接}
  该节目有 {photo_count} 张照片{视频状态提示}。"

- 视频状态提示规则：
  - video_status 为 ready → "和视频"
  - video_status 为 uploading → "，视频正在上传中，请稍后查看"
  - video_status 为 none → "，视频暂未上传"

- 详情页链接格式：https://your-domain.com/p/{access_token}

- 未找到节目时：
  "抱歉，未找到匹配的节目。请确认节目号或节目名是否正确，也可以告诉我活动名称来缩小范围。"

- 找到多个结果时：
  "找到多个匹配的节目，请确认您要查看的是：
  1. 【{活动名}】{节目号} - {节目名}
  2. 【{活动名}】{节目号} - {节目名}
  请回复序号或告诉我更多活动信息。"

# 注意事项

- 保持友好、简洁的语气
- 不要暴露 API 的技术细节
- 链接中只使用 access_token，不要包含其他参数
- 仅返回 ready 状态的节目（API 已自动过滤）
- 不要编造节目信息，所有信息来自 API 查询结果
```

> **重要**：将提示词中的 `https://your-domain.com` 替换为实际部署域名。

### 2.3 配置工具（API 插件）

在 COZE 智能体的「技能」→「插件」中添加自定义 API 插件：

#### 方式一：通过 OpenAPI Schema 导入

在「添加插件」→「云服务」→「OpenAPI Schema」中粘贴以下内容：

```yaml
openapi: 3.0.0
info:
  title: 节目管理系统 API
  description: 查询展演节目并获取素材链接
  version: 1.0.0
servers:
  - url: https://your-domain.com/api/public
    description: 生产环境
paths:
  /programs/search:
    get:
      operationId: search_programs
      summary: 跨活动搜索节目
      description: 通过节目号/节目名搜索节目，支持按活动名称或日期筛选。至少需要提供 q 参数。
      parameters:
        - name: q
          in: query
          required: true
          description: 节目号或节目名关键词
          schema:
            type: string
        - name: activity_name
          in: query
          required: false
          description: 活动名称（模糊匹配）
          schema:
            type: string
        - name: activity_date
          in: query
          required: false
          description: 活动日期，格式 YYYY-MM-DD
          schema:
            type: string
      responses:
        "200":
          description: 搜索结果列表
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    id:
                      type: integer
                      description: 节目ID
                    name:
                      type: string
                      description: 节目名称
                    sequence_number:
                      type: integer
                      description: 节目号
                    access_token:
                      type: string
                      description: 访问令牌
                    photo_count:
                      type: integer
                      description: 照片数量
                    video_status:
                      type: string
                      enum: [none, uploading, ready]
                      description: 视频状态
                    activity_id:
                      type: integer
                      description: 活动ID
                    activity_name:
                      type: string
                      description: 活动名称
                    activity_event_date:
                      type: string
                      description: 活动日期
                    activity_venue:
                      type: string
                      description: 活动地点
  /activities:
    get:
      operationId: list_activities
      summary: 获取活动列表
      description: 获取所有当前活跃的活动列表
      parameters: []
      responses:
        "200":
          description: 活动列表
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    id:
                      type: integer
                    name:
                      type: string
                    event_date:
                      type: string
                    venue:
                      type: string
                    program_count:
                      type: integer
```

> **重要**：将 `https://your-domain.com` 替换为实际部署域名。

#### 方式二：手动创建工具

如果 Schema 导入不可用，可手动添加工具：

**工具 1：搜索节目**

| 配置项 | 值 |
|--------|-----|
| 工具名称 | `search_programs` |
| 描述 | 通过节目号/节目名搜索节目，支持按活动名称或日期筛选 |
| 请求方式 | GET |
| URL | `https://your-domain.com/api/public/programs/search` |
| 参数 q | string，必填，节目号或节目名 |
| 参数 activity_name | string，可选，活动名称 |
| 参数 activity_date | string，可选，活动日期 YYYY-MM-DD |

**工具 2：获取活动列表**

| 配置项 | 值 |
|--------|-----|
| 工具名称 | `list_activities` |
| 描述 | 获取所有当前活跃的活动列表 |
| 请求方式 | GET |
| URL | `https://your-domain.com/api/public/activities` |
| 参数 | 无 |

### 2.4 开场白配置

在「对话开场白」中设置：

```
您好！我是节目查询助手 🎭
请告诉我您想查询的节目号或节目名，我帮您找到对应的素材链接。
例如：
- "5号节目"
- "小星星"
- "春季展演的12号节目"
```

---

## 三、微信服务号对接

### 3.1 前置准备

确保微信服务号已：
- 完成认证（已认证服务号才能使用客服消息接口）
- 在「设置与开发」→「基本配置」中记录 **AppID** 和 **AppSecret**

### 3.2 COZE 发布到微信服务号

1. 在 COZE 智能体页面，点击「发布」
2. 选择发布渠道为「微信服务号」
3. 点击「授权绑定」
4. 使用服务号管理员微信扫码授权
5. 授权成功后，COZE 将自动配置消息接收服务器
6. 选择发布版本，点击「发布」

### 3.3 扫码授权流程

```
COZE平台 → 发布渠道选择微信服务号 → 扫码授权 → 管理员用微信扫码确认 → 授权完成 → 自动配置
```

授权后，COZE 会自动完成以下配置：
- 设置消息接收 URL
- 配置消息加解密密钥
- 绑定消息处理规则

### 3.4 验证对接

1. 在微信中搜索并关注服务号
2. 发送测试消息，如 "你好"
3. 确认收到智能体回复
4. 发送节目查询测试，如 "5号节目"
5. 确认收到含链接的回复

---

## 四、消息处理流程

```
用户发送消息
    ↓
微信服务器转发到 COZE
    ↓
COZE 智能体识别意图
    ↓
┌─ 闲聊/非查询 → 直接回复
│
└─ 节目查询意图
    ↓
    判断信息是否充分
    ├─ 不充分 → 追问用户
    └─ 充分 → 调用 search_programs API
        ↓
        分析搜索结果
        ├─ 唯一结果 → 返回详情页链接
        ├─ 多个结果 → 列表让用户选择
        └─ 无结果 → 提示用户确认信息
```

---

## 五、注意事项

### 5.1 微信服务号限制

- **消息时间限制**：用户发送消息后，服务号需在 **48 小时内**回复，否则无法再主动推送
- **消息条数限制**：每次用户消息后，服务号最多可发送 **5 条**客服消息
- **链接跳转**：返回的链接在微信浏览器中直接打开，无需额外授权

### 5.2 安全注意事项

- 公开 API 无需认证，但仅返回已就绪（`ready`）状态的节目
- `access_token` 为随机生成的 12 位字符串，不易被猜测
- 建议对 API 访问频率进行限流（可使用 Nginx 限流配置）

### 5.3 COZE 智能体调优

- **测试不同问法**：确保智能体能识别 "第5个节目"、"5号"、"节目5" 等不同表述
- **测试模糊查询**：如 "那个舞蹈的节目"，智能体应追问节目名
- **测试多结果场景**：当多个活动有相同节目号时，智能体应正确引导用户选择
- **持续优化提示词**：根据实际用户对话反馈调整提示词

### 5.4 节目详情页兼容性

- 节目详情页（`/p/:token`）已适配微信内置浏览器
- 支持视频在线播放和照片预览/下载
- 微信浏览器中下载照片可能需要长按保存图片

---

## 六、故障排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 消息无回复 | COZE 未正确绑定服务号 | 检查授权状态，重新扫码绑定 |
| 智能体无法调用 API | API 地址配置错误 | 检查 COZE 插件中的 URL 是否正确 |
| 返回空结果 | 节目未就绪 | 检查节目 ready_status 是否为 ready |
| 链接无法打开 | 域名未备案或 SSL 证书问题 | 微信要求链接必须为已备案域名的 HTTPS |
| API 调用超时 | 网络不通 | 检查服务器防火墙和 COZE 出口 IP 白名单 |

---

## 七、扩展建议

1. **访问统计**：在智能体返回链接时，可记录用户查询日志，用于后续分析热门节目
2. **多语言支持**：如需支持多语言，可在提示词中增加语言处理逻辑
3. **菜单配置**：在微信服务号底部菜单增加"查询节目"入口，引导用户使用
4. **关注后自动回复**：设置关注后的欢迎语，引导用户查询节目
