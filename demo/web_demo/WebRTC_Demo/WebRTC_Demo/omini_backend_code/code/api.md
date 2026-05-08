# MiniCPM-o WebRTC Demo Backend API 文档

> Base URL: `http://localhost:8021`  
> FastAPI 版本，支持自动生成的交互式文档：`/docs`（Swagger UI）、`/redoc`（ReDoc）

---

## 目录

- [通用接口](#通用接口)
- [推理服务管理](#推理服务管理)
- [语音会话（Token）](#语音会话token)
- [数据模型](#数据模型)
- [错误说明](#错误说明)

---

## 通用接口

### `GET /`

根路径，返回服务基本信息。

**响应示例：**
```json
{
  "message": "minicpmo-backend",
  "version": "1.0.0",
  "environment": "local",
  "status": "running"
}
```

---

### `GET /health`

服务健康检查。

**响应示例：**
```json
{
  "status": "healthy",
  "service": "minicpmo-backend"
}
```

---

### `GET /health/redis`

存储健康检查（本地模式使用内存存储）。

**响应示例：**
```json
{
  "status": "healthy",
  "redis": {
    "connected": true,
    "mode": "in-memory",
    "version": "memory-store-1.0"
  },
  "service": "minicpmo-backend"
}
```

---

### `GET /download/test`

下载测试文件 `test.txt`。

**响应：** `text/plain` 文件流

---

## 推理服务管理

前缀：`/api/inference`

### `POST /api/inference/register`

注册一个 C++ 推理服务到后端，供语音会话调度使用。

**请求体：** `ServiceRegisterRequest`
```json
{
  "ip": "192.168.1.100",
  "port": 9060,
  "model_port": 19060,
  "service_name": "o45-cpp",
  "model_type": "duplex",
  "session_type": "release"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ip` | string | 是 | 推理服务所在 IP |
| `port` | int | 是 | 推理服务 HTTP 端口 |
| `model_port` | int | 是 | llama-server 内部端口（通常为 port + 10000） |
| `service_name` | string | 是 | 服务名称，如 `o45-cpp` |
| `model_type` | string | 是 | `simplex` / `duplex` / `release` |
| `session_type` | string | 是 | 会话类型，如 `release` |

**响应：** `ServiceRegisterResponse`
```json
{
  "service_id": "192.168.1.100:9060",
  "message": "服务注册成功"
}
```

---

### `DELETE /api/inference/unregister/{service_id}`

注销指定推理服务。

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `service_id` | string | 服务 ID，格式为 `ip:port` |

**响应示例：**
```json
{
  "message": "服务注销成功"
}
```

---

### `GET /api/inference/services`

获取已注册的推理服务列表。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `available_only` | bool | 否 | 是否只返回状态为 `available` 的服务（默认 `false`） |

**响应：** `ServiceListResponse`
```json
{
  "services": [
    {
      "service_id": "192.168.1.100:9060",
      "ip": "192.168.1.100",
      "port": 9060,
      "model_port": 19060,
      "service_name": "o45-cpp",
      "model_type": "duplex",
      "session_type": "release",
      "status": "available",
      "heartbeat_time": "2025-01-01T12:00:00",
      "locked_by": null,
      "lock_time": null
    }
  ],
  "total": 1
}
```

#### ServiceInfo 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `service_id` | string | 唯一标识 `ip:port` |
| `ip` | string | 服务 IP |
| `port` | int | HTTP 端口 |
| `model_port` | int | llama-server 端口 |
| `service_name` | string | 服务名称 |
| `model_type` | string | `simplex` / `duplex` / `release` |
| `session_type` | string | 会话类型 |
| `status` | string | `available`（可用） / `busy`（被占用） / `offline`（离线） |
| `heartbeat_time` | datetime | 最后一次心跳时间 |
| `locked_by` | string | 锁定该服务的用户 ID |
| `lock_time` | datetime | 锁定时间 |

---

## 语音会话（Token）

前缀：`/api`

### `POST /api/login`

用户登录，分配一个 LiveKit Token 并锁定一个可用的推理服务。

**请求体：** `LoginRequest`
```json
{
  "userId": "default_user",
  "modelType": "simplex",
  "serviceName": null,
  "durVadTime": 0.4,
  "durVadThreshold": 0.1,
  "vadRace": false,
  "sessionId": null,
  "sessionType": null,
  "saveData": true,
  "modelConfig": {},
  "highRefresh": false,
  "highImage": false,
  "language": null,
  "timbreId": null,
  "base64String": null,
  "audioFormat": "wav"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `userId` | string | 否 | 用户 ID（留空由后端生成 UUID） |
| `modelType` | string | 否 | 推理模式：`simplex` / `duplex`（默认 `simplex`） |
| `serviceName` | string | 否 | 指定服务名称过滤 |
| `durVadTime` | float | 否 | VAD 检测时长阈值（默认 0.4s） |
| `durVadThreshold` | float | 否 | VAD 阈值（默认 0.1） |
| `vadRace` | bool | 否 | 是否启用 VAD 竞争模式 |
| `sessionId` | string | 否 | 会话 ID（留空自动生成） |
| `sessionType` | string | 否 | 会话类型 |
| `saveData` | bool | 否 | 是否保存数据（默认 `true`） |
| `modelConfig` | ModelConfig | 否 | 模型配置 |
| `highRefresh` | bool | 否 | 是否高频刷新 |
| `highImage` | bool | 否 | 是否高清图片 |
| `language` | string | 否 | 语言偏好 |
| `timbreId` | int | 否 | 音色 ID |
| `base64String` | string | 否 | 克隆音色音频 Base64 |
| `audioFormat` | string | 否 | 音频格式：`wav` / `mp3`（默认 `wav`） |

**响应：** `LoginResponse`
```json
{
  "success": true,
  "userId": "uuid-xxxx",
  "sessionId": "uuid-xxxx123",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "message": "登录成功",
  "expires_in": 600
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `userId` | string | 分配的用户 ID |
| `sessionId` | string | 会话/房间 ID |
| `token` | string | LiveKit JWT Token |
| `message` | string | 提示信息 |
| `expires_in` | int | Token 有效期（秒） |

**错误码：**
- `503` - 没有可用的推理服务
- `503` - 无法锁定推理服务
- `500` - 登录失败

---

### `POST /api/logout`

用户登出，释放占用的推理服务锁定。

**请求体：** `LogoutRequest`
```json
{
  "userId": "uuid-xxxx",
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `userId` | string | 是 | 用户 ID |
| `token` | string | 是 | LiveKit Token |

**响应：** `LogoutResponse`
```json
{
  "success": true,
  "message": "登出成功"
}
```

**错误码：**
- `500` - 登出失败

---

### `GET /api/get_system_time`

获取当前系统时间。

**响应示例：**
```json
{
  "time": "2025-01-01 12:00:00.123456"
}
```

---

## 数据模型

### ModelConfig

```json
{
  "media_type": null,
  "audio_prompt_text": null,
  "task_prompt_text": null,
  "timbre_id": null,
  "checkpoint_id": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `media_type` | string | 媒体类型 |
| `audio_prompt_text` | string | 音频提示文本 |
| `task_prompt_text` | string | 任务提示文本 |
| `timbre_id` | int | 音色 ID |
| `checkpoint_id` | int | 检查点 ID |

---

### StatusResponse

```json
{
  "success": true,
  "tokens": {}
}
```

---

### HealthResponse

```json
{
  "success": true,
  "message": "healthy",
  "timestamp": "2025-01-01T12:00:00"
}
```

---

### SessionFeedbackRequest / SessionFeedbackResponse

```json
// Request
{
  "userId": "uuid-xxxx",
  "sessionId": "session-yyyy",
  "cancel": false,
  "like": true,
  "feedback": "很好"
}

// Response
{
  "success": true,
  "message": "反馈已提交"
}
```

---

## 错误说明

| HTTP 状态码 | 含义 | 常见场景 |
|-------------|------|----------|
| `200` | 成功 | 请求正常处理 |
| `404` | 未找到 | 服务不存在（注销时） |
| `500` | 服务器内部错误 | 注册/注销/列表查询失败 |
| `503` | 服务不可用 | 没有可用推理服务、无法锁定服务 |

---

## 模型类型枚举

| 值 | 说明 |
|----|------|
| `simplex` | 半双工模式（一问一答） |
| `duplex` | 全双工模式（实时对话） |
| `release` | 发布版本（通用） |

---

## 服务状态枚举

| 值 | 说明 |
|----|------|
| `available` | 可用，等待用户连接 |
| `busy` | 被占用，已有用户会话 |
| `offline` | 离线，心跳超时 |

---

## 使用流程

```
1. C++ 推理服务启动后
   → POST /api/inference/register    (注册自己)

2. 前端用户点击"开始对话"
   → POST /api/login                  (获取 LiveKit Token)
   → 前端用 token 连接 LiveKit 房间
   → 后端自动启动机器人监听房间音频

3. 用户结束对话
   → POST /api/logout                 (释放推理服务)

4. C++ 推理服务关闭前（可选）
   → DELETE /api/inference/unregister/{service_id}
```
