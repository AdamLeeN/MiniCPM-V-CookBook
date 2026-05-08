# MiniCPM-o WebRTC Demo - 公网 API 文档

> **版本**: v1.0  
> **适用场景**: 外网第三方应用集成实时语音对话  
> **最后更新**: 2026-05-06

---

## 📡 端点配置

### 公网部署（穿透模式）

| 服务 | 内网地址 | 公网地址 | 协议 | 用途 |
|------|---------|---------|------|------|
| **后端 API** | `127.0.0.1:8021` | `http://117.72.163.123:3666` | HTTP | REST API（登录、会话管理） |
| **LiveKit 信令** | `127.0.0.1:7880` | `ws://117.72.163.123:7882` | WebSocket | WebRTC 信令（SDP/ICE 交换） |
| **LiveKit 媒体** | `127.0.0.1:7881` | `tcp://117.72.163.123:7881` | TCP | WebRTC over TCP（音视频传输） |

> **注意**: `7881` 为 **1:1 端口映射**，LiveKit 宣告的 ICE candidate 端口与公网端口一致，客户端可直接连接。

### WSL2 本地部署（推荐开发测试）

| 服务 | 地址 | 说明 |
|------|------|------|
| **前端** | `https://127.0.0.1:8088` | Vue 前端 + serve-prod.mjs |
| **后端 API** | `http://127.0.0.1:8021` | FastAPI（WSL2 内运行） |
| **LiveKit** | `ws://127.0.0.1:7880` | **Windows 原生运行** |
| **C++ 推理** | `http://127.0.0.1:9060` | llama-server（WSL2 内运行） |

> **WSL2 关键**：LiveKit 必须在 **Windows 侧**运行，不能在 WSL2 内。WSL2 NAT 模式下 UDP 回环单向不通，导致 WebRTC ICE 失败。

### WSL2 部署步骤

1. **启用 WSL2 mirrored 模式**
   ```powershell
   # C:\Users\<你的用户名>\.wslconfig
   [wsl2]
   networkingMode=mirrored
   ```
   然后 `wsl --shutdown` 重启。

2. **下载 Windows LiveKit**
   从 [GitHub Releases](https://github.com/livekit/livekit/releases) 下载 `livekit-server.exe`，放到项目根目录。

3. **启动 Windows LiveKit**
   ```powershell
   cd D:\MiniCPM-V-CookBook-1\demo\web_demo\WebRTC_Demo
   .\start-livekit-windows.ps1
   ```

4. **启动 WSL2 服务**
   ```bash
   cd /mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo
   bash oneclick.sh start
   ```

5. **访问前端**
   浏览器打开 `https://127.0.0.1:8088`

---

## 🔧 服务端配置（必须）

### 1. LiveKit 配置

修改 `livekit.yaml`（位于项目根目录或 `livekit/` 目录下）：

```yaml
port: 7880

rtc:
  tcp_port: 7881        # WebRTC over TCP
  use_external_ip: true # 允许使用外部 IP

node:
  ip: 117.72.163.123   # 公网 IP，LiveKit 对外宣告此地址
```

**重启 LiveKit** 后生效。

### 2. 后端 CORS 配置

确保 `omini_backend_code/main.py`（或后端入口文件）已启用跨域：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. 防火墙/穿透确认

确保以下端口在穿透工具和服务器防火墙中均已放行：
- `TCP 3666` → `8021`
- `TCP 7882` → `7880`
- `TCP 7881` → `7881`

---

## 🔄 实时通话流程

```
┌─────────────┐  POST /api/inference/register  ┌─────────────┐
│  第三方应用  │ ─────────────────────────────→ │             │
│             │ ←───────────────────────────── │   后端 3666   │
│   注册推理服务 │                                │             │
└──────┬──────┘                                └──────┬──────┘
       │                                              │
       │  POST /login                                 │
       ▼                                              ▼
┌─────────────┐    获取 Token    ┌─────────────────────────┐
│             │ ←────────────────│  分配可用推理节点 127.0.0.1:9060 │
│  第三方应用  │                  └─────────────────────────┘
└──────┬──────┘
       │ ws://117.72.163.123:7882
       ▼
┌─────────────┐   WebRTC over TCP    ┌─────────────┐
│   LiveKit   │ ←──────────────────→ │  第三方应用  │
│ 7882/7881  │   (ICE via 7881)     │ (麦克风/扬声器)│
└──────┬──────┘                      └─────────────┘
       │
       │ 音频流转发
       ▼
┌─────────────┐
│ C++ 推理 9060│ ← 后端内部调用，不对外暴露
│  (MiniCPM-o) │
└─────────────┘
```

**流程说明**:
1. ⭐ **【必须先执行】第三方应用调用 `/api/inference/register` 注册 C++ 推理服务**
2. 第三方应用调用后端 `/login` 获取 LiveKit Token（后端会分配一个已注册的推理节点）
3. 使用 Token 连接 LiveKit WebSocket (`ws://117.72.163.123:7882`)
4. 通过 WebRTC 发布本地音频轨道
5. LiveKit 将音频转发给后端 Bot
6. 后端调用 C++ 推理服务 (`127.0.0.1:9060`)
7. C++ 返回 AI 语音，经 LiveKit 转发回第三方应用

> ⚠️ **重要**: 后端使用内存存储管理推理服务，以下情况会导致注册丢失，需要重新调用 `/api/inference/register`：
> - 后端 8021 重启
> - C++ 推理服务 9060 超过 20 秒未发送心跳
> - 推理服务进程被杀死未自动重启

---

## 🔑 API 端点

### 1. 登录获取 Token

获取加入 LiveKit 房间的 JWT Token。

```http
POST http://117.72.163.123:3666/api/login
Content-Type: application/json
```

#### 请求参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `uid` | string | ✅ | - | 用户唯一标识，建议 UUID |
| `language` | string | ❌ | `"zh"` | 语言代码，`zh` / `en` |
| `voice` | string | ❌ | `"default"` | 语音音色 |
| `priority` | int | ❌ | `0` | 用户优先级 |
| `use_video` | bool | ❌ | `false` | 是否启用视频 |
| `local_test` | bool | ❌ | `true` | **外网应用务必设为 `false`** |
| `bot_id` | int | ❌ | `-1` | 机器人 ID |
| `custom_prompt` | string | ❌ | `""` | 自定义系统提示词 |
| `tts_base_url` | string | ❌ | `""` | TTS 服务地址 |

#### 请求示例

```json
{
  "uid": "user-123456",
  "language": "zh",
  "voice": "default",
  "priority": 0,
  "use_video": false,
  "local_test": false,
  "bot_id": -1,
  "custom_prompt": "",
  "tts_base_url": ""
}
```

#### 成功响应 (200 OK)

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "livekitServer": "ws://127.0.0.1:7880",
  "userId": "user-123456",
  "sessionId": "user-12345672"
}
```

| 字段 | 说明 |
|------|------|
| `token` | LiveKit 连接用 JWT Token |
| `livekitServer` | ⚠️ 外网应用请**忽略**此字段，直接使用 `ws://117.72.163.123:7882` |
| `userId` | 用户 ID |
| `sessionId` | 会话 ID（房间名） |

#### 错误响应

```json
{
  "detail": "错误描述"
}
```

---

### 2. 登出结束会话

```http
POST http://117.72.163.123:3666/api/logout
Content-Type: application/json
```

#### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `token` | string | ✅ | `/login` 返回的 Token |

#### 请求示例

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

#### 成功响应 (200 OK)

```json
{
  "success": true
}
```

---

### 3. 健康检查

```http
GET http://117.72.163.123:3666/health
```

#### 成功响应 (200 OK)

```json
{
  "status": "ok"
}
```

---

### 4. 系统时间

```http
GET http://117.72.163.123:3666/api/get_system_time
```

#### 成功响应 (200 OK)

```json
{
  "time": "2026-05-06T10:38:00"
}
```

---

### 5. 推理服务注册（⭐ 必须先调用）

将 C++ 推理服务注册到后端调度中心。**在调用 `/login` 之前，必须先完成此步骤**，否则 `/login` 会返回 `503 没有可用的推理服务`。

```http
POST http://117.72.163.123:3666/api/inference/register
Content-Type: application/json
```

#### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ip` | string | ✅ | 推理服务 IP，本地部署填 `"127.0.0.1"` |
| `port` | int | ✅ | 推理服务端口，默认 `9060` |
| `model_port` | int | ✅ | 模型服务端口，通常与 `port` 相同 |
| `model_type` | string | ✅ | `"simplex"` 或 `"duplex"` |
| `session_type` | string | ✅ | `"release"`（固定值） |
| `service_name` | string | ✅ | 服务名称，如 `"o45-cpp"` |

#### 请求示例

```json
{
  "ip": "127.0.0.1",
  "port": 9060,
  "model_port": 9060,
  "model_type": "simplex",
  "session_type": "release",
  "service_name": "o45-cpp"
}
```

#### 成功响应 (200 OK)

```json
{
  "service_id": "127.0.0.1:9060",
  "status": "available",
  "message": "服务注册成功"
}
```

#### 常见错误

```json
{
  "detail": "服务已存在"
}
```

---

### 6. 推理服务注销

结束会话后，注销推理服务释放资源。

```http
POST http://117.72.163.123:3666/api/inference/unregister
Content-Type: application/json
```

#### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `service_id` | string | ✅ | 注册时返回的服务 ID，如 `"127.0.0.1:9060"` |

#### 请求示例

```json
{
  "service_id": "127.0.0.1:9060"
}
```

#### 成功响应 (200 OK)

```json
{
  "success": true,
  "message": "服务注销成功"
}
```

---

### 7. 推理服务列表

查询当前已注册的 C++ 推理节点状态。

```http
GET http://117.72.163.123:3666/api/inference/services
```

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `available_only` | int | ❌ | `1` 只返回可用服务 |

#### 成功响应 (200 OK)

```json
{
  "services": [
    {
      "service_id": "127.0.0.1:9060",
      "status": "available",
      "gpu_devices": "0"
    }
  ]
}
```

---

## 💻 客户端示例

### Python 实时通话客户端

依赖: `pip install livekit livekit-api aiohttp`

```python
import asyncio
import json
import uuid
import aiohttp
from livekit import rtc

# ==================== 配置 ====================
BACKEND_URL = "http://117.72.163.123:3666"
LIVEKIT_URL = "ws://117.72.163.123:7882"
# =============================================

async def get_token() -> tuple[str, str]:
    """1. 登录获取 LiveKit Token"""
    async with aiohttp.ClientSession() as session:
        payload = {
            "uid": str(uuid.uuid4()),
            "language": "zh",
            "voice": "default",
            "priority": 0,
            "use_video": False,
            "local_test": False,  # 外网必须 False
            "bot_id": -1,
            "custom_prompt": "",
            "tts_base_url": ""
        }
        async with session.post(f"{BACKEND_URL}/login", json=payload) as resp:
            resp.raise_for_status()
            data = await resp.json()
            print(f"✅ 登录成功 | sessionId: {data['sessionId']}")
            return data["token"], data["sessionId"]

async def main():
    token, session_id = await get_token()
    
    # 2. 连接 LiveKit
    room = rtc.Room()
    
    @room.on("connected")
    def on_connected():
        print(f"✅ 已连接房间: {room.name}")
    
    @room.on("disconnected")
    def on_disconnected():
        print("❌ 已断开连接")
    
    @room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant
    ):
        """3. 订阅到 AI 返回的音频轨道"""
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print(f"🎵 收到 AI 音频轨道: {publication.sid}")
            # 实际播放需接音频渲染，此处仅打印
            asyncio.create_task(audio_consumer(track))
    
    async def audio_consumer(track: rtc.Track):
        """消费音频帧（示例：打印音量）"""
        audio_stream = rtc.AudioStream(track)
        async for frame in audio_stream:
            # frame.data 为 PCM 16-bit 数据
            # 实际项目中送入音频播放器
            pass
    
    await room.connect(LIVEKIT_URL, token)
    
    # 4. 发布本地麦克风音频
    source = rtc.AudioSource(48000, 1)  # 48kHz, mono
    local_track = rtc.LocalAudioTrack.create_audio_track("microphone", source)
    await room.local_participant.publish_track(local_track)
    print("🎤 麦克风已发布，开始对话...")
    
    # 5. 保持运行，按 Ctrl+C 退出
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        # 6. 登出 + 断开
        async with aiohttp.ClientSession() as session:
            await session.post(f"{BACKEND_URL}/logout", json={"token": token})
        await room.disconnect()
        print("👋 会话已结束")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### JavaScript (Node.js / 浏览器) 示例

依赖: `npm install livekit-client`

```javascript
import { Room } from 'livekit-client';

const BACKEND_URL = 'http://117.72.163.123:3666';
const LIVEKIT_URL = 'ws://117.72.163.123:7882';

async function startConversation() {
  // 1. 登录获取 Token
  const loginRes = await fetch(`${BACKEND_URL}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      uid: crypto.randomUUID(),
      language: 'zh',
      voice: 'default',
      use_video: false,
      local_test: false,  // 外网必须 false
      bot_id: -1
    })
  });
  const { token } = await loginRes.json();

  // 2. 连接 LiveKit，强制走 TCP（避免 UDP 不通）
  const room = new Room({
    rtcConfig: {
      iceTransportPolicy: 'relay',  // 强制 relay，配合服务器 TCP
    }
  });

  room.on('trackSubscribed', (track, publication, participant) => {
    if (track.kind === 'audio') {
      console.log('🎵 收到 AI 音频:', publication.trackSid);
      // 浏览器中直接挂载到 audio 元素播放
      const audioElement = document.createElement('audio');
      audioElement.srcObject = new MediaStream([track.mediaStreamTrack]);
      audioElement.autoplay = true;
      document.body.appendChild(audioElement);
    }
  });

  await room.connect(LIVEKIT_URL, token);
  console.log('✅ 已连接房间:', room.name);

  // 3. 发布麦克风
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  await room.localParticipant.publishTrack(stream.getAudioTracks()[0]);
  console.log('🎤 麦克风已发布');

  // 4. 挂断时调用
  window.addEventListener('beforeunload', async () => {
    await fetch(`${BACKEND_URL}/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    });
    await room.disconnect();
  });
}

startConversation().catch(console.error);
```

---

### cURL 测试

#### 1. 注册推理服务（必须先做）

```bash
curl -X POST http://117.72.163.123:3666/api/inference/register \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "127.0.0.1",
    "port": 9060,
    "model_port": 9060,
    "model_type": "simplex",
    "session_type": "release",
    "service_name": "o45-cpp"
  }'
```

#### 2. 确认服务可用

```bash
curl "http://117.72.163.123:3666/api/inference/services?available_only=1"
```

#### 3. 登录获取 Token

```bash
curl -X POST http://117.72.163.123:3666/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "test-user-001",
    "language": "zh",
    "use_video": false,
    "local_test": false,
    "bot_id": -1
  }'
```

#### 4. 健康检查

```bash
curl http://117.72.163.123:3666/health
```

---

## ⚠️ 重要注意事项

### 1. `local_test` 参数

| 环境 | 值 | 原因 |
|------|-----|------|
| 本地/WSL 内测试 | `true` | 返回 `ws://127.0.0.1:7880` |
| **公网第三方应用** | **`false`** | 避免收到内网地址，客户端应直接写死公网地址 |

### 2. WebSocket 协议

- 公网地址为 `ws://`（非加密），如果第三方应用是 **HTTPS 网页**，浏览器会拦截 `ws://` 连接。
- **解决方案**: 在穿透工具或 Nginx 上加 TLS 反代，提供 `wss://117.72.163.123:7882`。
- 手机 App / 桌面应用不受此限制，可直接用 `ws://`。

### 3. WebRTC over TCP

当前穿透仅暴露 TCP 端口（无 UDP），客户端必须能接受 TCP candidates：

| SDK | 配置 |
|-----|------|
| Python `livekit` | 自动 fallback 到 TCP，无需额外配置 |
| JS `livekit-client` | `rtcConfig: { iceTransportPolicy: 'relay' }` |

### 4. 安全建议

当前接口无鉴权，暴露在公网存在风险，建议：

1. **后端加 API Key**
   ```python
   # 在 /login 等接口前加校验
   API_KEY = "your-secret-key"  # 放入环境变量
   
   @app.post("/login")
   async def login(request: Request, ...):
       if request.headers.get("X-API-Key") != API_KEY:
           raise HTTPException(status_code=401, detail="Invalid API Key")
   ```

2. **IP 白名单**
   在穿透工具或服务器防火墙限制 `3666` 端口的来源 IP。

3. **HTTPS/WSS**
   生产环境务必使用 TLS，避免 Token 在公网明文传输。

### 5. 调试 ICE 连接

如果客户端连接后 15 秒断开（ICE failed），检查：

```bash
# 在客户端运行，查看 ICE candidates
curl http://117.72.163.123:3666/api/inference/services
# 确认服务正常

# 检查 LiveKit 日志，确认宣告了正确的公网 IP
grep -i "advertise\|external ip" /path/to/livekit.log
```

期望看到包含 `117.72.163.123:7881` 的 TCP candidate。

---

## 📂 相关文件

| 文件 | 说明 |
|------|------|
| `test_api.py` | 后端 API 自动化测试脚本 |
| `oneclick.sh` | 一键启动所有服务 |
| `livekit.yaml` | LiveKit 配置文件（需改 `node.ip`） |
| `omini_backend_code/` | 后端 FastAPI 源码 |
| `cpp_server/` | C++ 推理服务源码 |
