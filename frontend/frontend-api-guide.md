# Oasis Minecraft - 前端 API 完整指南

> 本文档覆盖从用户注册到 Mod Build 的完整流程所需的所有 API。

## 目录

- [认证方式](#认证方式)
- [完整流程概览](#完整流程概览)
- [Step 1: 用户注册/登录](#step-1-用户注册登录)
- [Step 2: 创建 Workspace](#step-2-创建-workspace)
- [Step 3: 创建 Conversation](#step-3-创建-conversation)
- [Step 4: 发送 Message 触发 AI 生成](#step-4-发送-message-触发-ai-生成)
- [Step 5: 订阅 SSE 事件流](#step-5-订阅-sse-事件流)
- [Step 6: 批准/拒绝 AI 生成的 Spec](#step-6-批准拒绝-ai-生成的-spec)
- [Step 7: 手动编辑 Spec](#step-7-手动编辑-spec)
- [Step 8: 触发 Build](#step-8-触发-build)
- [Step 9: 下载产物](#step-9-下载产物)
- [附录: 完整前端示例](#附录-完整前端示例)

---

## 认证方式

所有需要认证的 API 支持两种方式（二选一）：

### 方式 1: Cookie（推荐 - Web 端）
```javascript
// 登录后自动设置 HttpOnly Cookie，无需额外处理
fetch('/api/workspaces', {
  credentials: 'include'  // 带上 cookie
})
```

### 方式 2: Authorization Header（适合移动端/API 调用）
```javascript
fetch('/api/workspaces', {
  headers: {
    'Authorization': `Bearer ${sessionToken}`
  }
})
```

---

## 完整流程概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           OASIS MINECRAFT FLOW                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. 注册/登录                                                            │
│     POST /api/auth/send-verification-code                               │
│     POST /api/auth/register                                             │
│     POST /api/auth/login                                                │
│         ↓                                                               │
│  2. 创建 Workspace                                                       │
│     POST /api/workspaces                                                │
│         ↓                                                               │
│  3. 创建 Conversation                                                    │
│     POST /api/workspaces/{id}/conversations                             │
│         ↓                                                               │
│  4. 发送 Message (触发 Run)                                              │
│     POST /api/conversations/{id}/messages                               │
│         ↓                                                               │
│  5. 订阅 SSE 事件流                                                      │
│     GET /api/runs/{run_id}/events                                       │
│         ↓                                                               │
│  6. 收到 awaiting_approval 事件                                          │
│     ├─ 批准: POST /api/runs/{run_id}/approve                            │
│     └─ 拒绝: POST /api/runs/{run_id}/reject                             │
│         ↓                                                               │
│  7. 手动编辑 Spec (可选)                                                  │
│     PUT/PATCH /api/workspaces/{id}/spec                                 │
│         ↓                                                               │
│  8. 触发 Build                                                           │
│     POST /api/runs/workspace/{id}/build                                 │
│         ↓                                                               │
│  9. 下载 JAR                                                             │
│     GET /api/runs/{run_id}/artifacts/{artifact_id}/download             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: 用户注册/登录

### 1.1 邮箱注册流程

#### 发送验证码
```http
POST /api/auth/send-verification-code
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**响应：**
```json
{
  "success": true,
  "message": "Verification code sent to email"
}
```

#### 注册账号
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "my_username",
  "email": "user@example.com",
  "password": "secure_password123",
  "verification_code": "123456"
}
```

**响应：**
```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "my_username",
    "email": "user@example.com",
    "created_at": "2026-01-17T10:00:00Z"
  }
}
```

### 1.2 登录

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password123"
}
```

**响应：**
```json
{
  "success": true,
  "message": "Login successful",
  "session": {
    "id": "session-uuid",
    "token": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "name": null,
    "created_at": "2026-01-17T10:00:00Z"
  },
  "user": {
    "id": "user-uuid",
    "username": "my_username",
    "email": "user@example.com",
    "created_at": "2026-01-17T09:00:00Z"
  }
}
```

> **注意**: 登录成功后会自动设置 `session_token` HttpOnly Cookie

### 1.3 Google OAuth 登录

```http
POST /api/auth/google-login
Content-Type: application/json

{
  "id_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**首次登录响应（需要设置用户名）：**
```json
{
  "success": true,
  "message": "Please set your username to complete registration",
  "requires_username": true,
  "session": null,
  "user": null
}
```

**设置用户名：**
```http
POST /api/auth/set-username
Content-Type: application/json

{
  "id_token": "eyJhbGciOiJSUzI1NiIs...",
  "username": "my_username"
}
```

---

## Step 2: 创建 Workspace

### 创建新 Workspace

```http
POST /api/workspaces
Authorization: Bearer {session_token}
Content-Type: application/json

{
  "name": "My Awesome Mod",
  "description": "A mod with ruby gems and tools",
  "spec": {
    "mod_name": "Ruby Mod",
    "mod_id": "ruby_mod",
    "version": "1.0.0",
    "mc_version": "1.20.1",
    "items": [],
    "blocks": [],
    "tools": []
  }
}
```

**响应：**
```json
{
  "id": "ws-550e8400-e29b-41d4-a716-446655440000",
  "owner_id": "user-uuid",
  "name": "My Awesome Mod",
  "description": "A mod with ruby gems and tools",
  "cover_image_url": null,
  "spec": { ... },
  "spec_version": 1,
  "last_modified_at": "2026-01-17T10:00:00Z",
  "created_at": "2026-01-17T10:00:00Z",
  "updated_at": "2026-01-17T10:00:00Z"
}
```

### 列出所有 Workspace

```http
GET /api/workspaces
Authorization: Bearer {session_token}
```

**响应：**
```json
{
  "workspaces": [
    {
      "id": "ws-uuid-1",
      "name": "My Awesome Mod",
      "spec_version": 1,
      "last_modified_at": "2026-01-17T10:00:00Z",
      ...
    }
  ],
  "total": 1
}
```

### 获取单个 Workspace

```http
GET /api/workspaces/{workspace_id}
Authorization: Bearer {session_token}
```

---

## Step 3: 创建 Conversation

```http
POST /api/workspaces/{workspace_id}/conversations
Authorization: Bearer {session_token}
Content-Type: application/json

{
  "title": "Creating Ruby Mod"
}
```

**响应：**
```json
{
  "id": "conv-550e8400-e29b-41d4-a716-446655440000",
  "workspace_id": "ws-uuid",
  "title": "Creating Ruby Mod",
  "message_count": 0,
  "created_at": "2026-01-17T10:00:00Z",
  "updated_at": "2026-01-17T10:00:00Z"
}
```

### 列出 Workspace 的所有 Conversation

```http
GET /api/workspaces/{workspace_id}/conversations
Authorization: Bearer {session_token}
```

---

## Step 4: 发送 Message 触发 AI 生成

### 发送消息并触发 Run

```http
POST /api/conversations/{conversation_id}/messages
Authorization: Bearer {session_token}
Content-Type: application/json

{
  "content": "Create a ruby gem item that glows in the dark and has RARE rarity",
  "trigger_run": true,
  "run_type": "generate"
}
```

**响应：**
```json
{
  "message": {
    "id": "msg-uuid",
    "conversation_id": "conv-uuid",
    "role": "user",
    "content": "Create a ruby gem item that glows in the dark...",
    "content_type": "text",
    "created_at": "2026-01-17T10:01:00Z"
  },
  "run_id": "run-550e8400-e29b-41d4-a716-446655440000",
  "run_status": "queued"
}
```

### 获取 Conversation 的所有消息

```http
GET /api/conversations/{conversation_id}/messages
Authorization: Bearer {session_token}
```

---

## Step 5: 订阅 SSE 事件流

### 订阅 Run 事件

```http
GET /api/runs/{run_id}/events
Authorization: Bearer {session_token}
Accept: text/event-stream
```

### 事件类型

| 事件类型 | 说明 | Payload |
|---------|------|---------|
| `run.status` | 状态变更 | `{status, workspace_id, run_id}` |
| `run.progress` | 进度更新 | `{progress: 0-100}` |
| `run.awaiting_approval` | 等待用户批准 | `{pending_deltas, deltas_count, ...}` |
| `run.awaiting_input` | 等待用户回答问题 | `{clarifying_questions, reasoning, ...}` |
| `log.append` | 日志消息 | `{message, level, phase}` |
| `spec.preview` | Spec 变更预览 | `{delta, delta_index, total_deltas}` |
| `spec.saved` | Spec 已保存 | `{spec_version, items_count, ...}` |
| `artifact.created` | 产物创建 | `{artifact_id, file_name, artifact_type}` |

### SSE 响应示例

```
event: run.status
data: {"event_type":"run.status","payload":{"status":"running","workspace_id":"ws-uuid","run_id":"run-uuid"}}

event: log.append
data: {"event_type":"log.append","payload":{"message":"Phase 1: Processing user request...","level":"info","phase":"orchestrator"}}

event: spec.preview
data: {"event_type":"spec.preview","payload":{"delta":{"operation":"add","path":"items[0]","value":{"item_name":"Ruby Gem","rarity":"RARE"}},"delta_index":0,"total_deltas":1}}

event: run.awaiting_approval
data: {"event_type":"run.awaiting_approval","payload":{"pending_deltas":[...],"deltas_count":1,"clarifying_questions":[],"spec_version":0}}
```

### 获取历史事件（非 SSE）

```http
GET /api/runs/{run_id}/events/history
Authorization: Bearer {session_token}
```

---

## Step 6: 批准/拒绝 AI 生成的 Spec

### 批准 Deltas

```http
POST /api/runs/{run_id}/approve
Authorization: Bearer {session_token}
Content-Type: application/json

{
  "modified_deltas": null
}
```

> **注意**: 如果用户在 UI 中编辑了 deltas，可以传入 `modified_deltas`

**响应：**
```json
{
  "success": true,
  "spec_version": 1,
  "status": "succeeded",
  "spec_summary": {
    "mod_name": "Ruby Mod",
    "items_count": 1,
    "blocks_count": 0,
    "tools_count": 0
  }
}
```

### 拒绝 Deltas

```http
POST /api/runs/{run_id}/reject
Authorization: Bearer {session_token}
Content-Type: application/json

{
  "reason": "I want a different item instead"
}
```

**响应：**
```json
{
  "success": true,
  "status": "rejected",
  "message": "Changes rejected and discarded"
}
```

---

## Step 7: 手动编辑 Spec

### 获取当前 Spec

```http
GET /api/workspaces/{workspace_id}/spec
Authorization: Bearer {session_token}
```

**响应：**
```json
{
  "workspace_id": "ws-uuid",
  "spec": {
    "mod_name": "Ruby Mod",
    "mod_id": "ruby_mod",
    "version": "1.0.0",
    "mc_version": "1.20.1",
    "items": [
      {
        "item_name": "Ruby Gem",
        "item_id": "ruby_gem",
        "rarity": "RARE",
        "description": "A glowing gem"
      }
    ],
    "blocks": [],
    "tools": []
  },
  "version": 1,
  "last_modified_at": "2026-01-17T10:05:00Z"
}
```

### 整包更新 Spec

```http
PUT /api/workspaces/{workspace_id}/spec
Authorization: Bearer {session_token}
Content-Type: application/json

{
  "spec": {
    "mod_name": "Ruby Mod",
    "mod_id": "ruby_mod",
    "version": "1.0.0",
    "mc_version": "1.20.1",
    "items": [
      {
        "item_name": "Ruby Gem",
        "item_id": "ruby_gem",
        "rarity": "EPIC",
        "description": "A glowing gem of epic power"
      }
    ],
    "blocks": [],
    "tools": []
  },
  "change_notes": "Changed rarity to EPIC"
}
```

**响应：**
```json
{
  "workspace_id": "ws-uuid",
  "spec": { ... },
  "version": 2,
  "last_modified_at": "2026-01-17T10:10:00Z"
}
```

### 部分更新 Spec (Patch)

```http
PATCH /api/workspaces/{workspace_id}/spec
Authorization: Bearer {session_token}
Content-Type: application/json

{
  "operations": [
    {
      "op": "update",
      "path": "items[0].rarity",
      "value": "LEGENDARY"
    },
    {
      "op": "add",
      "path": "items[1]",
      "value": {
        "item_name": "Ruby Sword",
        "item_id": "ruby_sword"
      }
    }
  ],
  "change_notes": "Updated rarity and added sword"
}
```

### 获取 Spec 历史

```http
GET /api/workspaces/{workspace_id}/spec/history
Authorization: Bearer {session_token}
```

**响应：**
```json
{
  "history": [
    {
      "id": "history-uuid",
      "workspace_id": "ws-uuid",
      "version": 2,
      "spec": { ... },
      "delta": { "operations": [...] },
      "change_source": "user",
      "change_notes": "Changed rarity to EPIC",
      "created_at": "2026-01-17T10:10:00Z"
    },
    {
      "id": "history-uuid-1",
      "workspace_id": "ws-uuid",
      "version": 1,
      "spec": { ... },
      "delta": null,
      "change_source": "ai",
      "change_notes": "AI generated initial spec",
      "created_at": "2026-01-17T10:05:00Z"
    }
  ],
  "total": 2
}
```

### 回滚到历史版本

```http
POST /api/workspaces/{workspace_id}/spec/rollback/{version}
Authorization: Bearer {session_token}
```

---

## Step 8: 触发 Build

### 触发构建

```http
POST /api/runs/workspace/{workspace_id}/build
Authorization: Bearer {session_token}
```

**响应：**
```json
{
  "id": "run-build-uuid",
  "workspace_id": "ws-uuid",
  "run_type": "build",
  "status": "queued",
  "progress": 0,
  "created_at": "2026-01-17T10:15:00Z"
}
```

### 订阅 Build 事件

```http
GET /api/runs/{run_id}/events
Authorization: Bearer {session_token}
Accept: text/event-stream
```

**Build 事件示例：**
```
event: run.status
data: {"event_type":"run.status","payload":{"status":"running"}}

event: log.append
data: {"event_type":"log.append","payload":{"message":"Phase 3: Compiling spec to IR...","level":"info"}}

event: run.progress
data: {"event_type":"run.progress","payload":{"progress":30}}

event: log.append
data: {"event_type":"log.append","payload":{"message":"Phase 7: Building JAR with Gradle...","level":"info"}}

event: artifact.created
data: {"event_type":"artifact.created","payload":{"artifact_id":"artifact-uuid","file_name":"ruby_mod-1.0.0.jar","artifact_type":"jar"}}

event: run.status
data: {"event_type":"run.status","payload":{"status":"succeeded"}}
```

---

## Step 9: 下载产物

### 列出 Run 的所有产物

```http
GET /api/runs/{run_id}/artifacts
Authorization: Bearer {session_token}
```

**响应：**
```json
{
  "artifacts": [
    {
      "id": "artifact-uuid",
      "run_id": "run-uuid",
      "workspace_id": "ws-uuid",
      "artifact_type": "jar",
      "file_name": "ruby_mod-1.0.0.jar",
      "file_size": 1024000,
      "mime_type": "application/java-archive",
      "download_url": "/api/runs/{run_id}/artifacts/{artifact_id}/download",
      "created_at": "2026-01-17T10:20:00Z"
    }
  ],
  "total": 1
}
```

### 下载产物文件

```http
GET /api/runs/{run_id}/artifacts/{artifact_id}/download
Authorization: Bearer {session_token}
```

> **响应**: 返回文件流（`application/java-archive`）

---

## 附录: 完整前端示例

### JavaScript/TypeScript 完整流程

```typescript
// ==========================================
// Oasis Minecraft - Frontend API Client
// ==========================================

const API_BASE = 'http://localhost:3000';

// 存储 session token
let sessionToken: string | null = null;

// ==========================================
// 1. 认证
// ==========================================

async function register(email: string, username: string, password: string, code: string) {
  // 1.1 发送验证码
  await fetch(`${API_BASE}/api/auth/send-verification-code`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });

  // 1.2 注册
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, username, password, verification_code: code })
  });
  
  return res.json();
}

async function login(email: string, password: string) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',  // 自动处理 cookie
    body: JSON.stringify({ email, password })
  });
  
  const data = await res.json();
  if (data.success) {
    sessionToken = data.session.token;
  }
  return data;
}

// ==========================================
// 2. 创建 Workspace
// ==========================================

async function createWorkspace(name: string, description: string) {
  const res = await fetch(`${API_BASE}/api/workspaces`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${sessionToken}`
    },
    body: JSON.stringify({
      name,
      description,
      spec: {
        mod_name: name,
        mod_id: name.toLowerCase().replace(/\s+/g, '_'),
        version: '1.0.0',
        mc_version: '1.20.1',
        items: [],
        blocks: [],
        tools: []
      }
    })
  });
  
  return res.json();
}

// ==========================================
// 3. 创建 Conversation
// ==========================================

async function createConversation(workspaceId: string, title: string) {
  const res = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/conversations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${sessionToken}`
    },
    body: JSON.stringify({ title })
  });
  
  return res.json();
}

// ==========================================
// 4. 发送消息并触发 AI
// ==========================================

async function sendMessage(conversationId: string, content: string) {
  const res = await fetch(`${API_BASE}/api/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${sessionToken}`
    },
    body: JSON.stringify({
      content,
      trigger_run: true,
      run_type: 'generate'
    })
  });
  
  return res.json();
}

// ==========================================
// 5. 订阅 SSE 事件流
// ==========================================

function subscribeToEvents(
  runId: string,
  handlers: {
    onStatus?: (status: string) => void;
    onProgress?: (progress: number) => void;
    onLog?: (message: string, level: string) => void;
    onSpecPreview?: (delta: any) => void;
    onAwaitingApproval?: (data: any) => void;
    onAwaitingInput?: (questions: string[]) => void;
    onArtifact?: (artifact: any) => void;
    onError?: (error: any) => void;
  }
) {
  const url = `${API_BASE}/api/runs/${runId}/events`;
  const eventSource = new EventSource(url, {
    // 如果使用 cookie 认证，需要 withCredentials
    // 如果使用 header，需要用 fetch + ReadableStream
  });

  // 如果需要 Authorization header，使用这种方式：
  /*
  fetch(url, {
    headers: { 'Authorization': `Bearer ${sessionToken}` }
  }).then(response => {
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    
    function read() {
      reader.read().then(({ done, value }) => {
        if (done) return;
        const text = decoder.decode(value);
        // 解析 SSE 格式
        const lines = text.split('\n');
        // ...处理事件
        read();
      });
    }
    read();
  });
  */

  // 使用 EventSource（需要 cookie 认证）
  eventSource.addEventListener('run.status', (e) => {
    const data = JSON.parse(e.data);
    handlers.onStatus?.(data.payload.status);
  });

  eventSource.addEventListener('run.progress', (e) => {
    const data = JSON.parse(e.data);
    handlers.onProgress?.(data.payload.progress);
  });

  eventSource.addEventListener('log.append', (e) => {
    const data = JSON.parse(e.data);
    handlers.onLog?.(data.payload.message, data.payload.level);
  });

  eventSource.addEventListener('spec.preview', (e) => {
    const data = JSON.parse(e.data);
    handlers.onSpecPreview?.(data.payload);
  });

  eventSource.addEventListener('run.awaiting_approval', (e) => {
    const data = JSON.parse(e.data);
    handlers.onAwaitingApproval?.(data.payload);
  });

  eventSource.addEventListener('run.awaiting_input', (e) => {
    const data = JSON.parse(e.data);
    handlers.onAwaitingInput?.(data.payload.clarifying_questions);
  });

  eventSource.addEventListener('artifact.created', (e) => {
    const data = JSON.parse(e.data);
    handlers.onArtifact?.(data.payload);
  });

  eventSource.onerror = (e) => {
    handlers.onError?.(e);
  };

  return () => eventSource.close();
}

// ==========================================
// 6. 批准/拒绝
// ==========================================

async function approveDeltas(runId: string, modifiedDeltas?: any[]) {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${sessionToken}`
    },
    body: JSON.stringify({ modified_deltas: modifiedDeltas || null })
  });
  
  return res.json();
}

async function rejectDeltas(runId: string, reason?: string) {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${sessionToken}`
    },
    body: JSON.stringify({ reason })
  });
  
  return res.json();
}

// ==========================================
// 7. 手动编辑 Spec
// ==========================================

async function getSpec(workspaceId: string) {
  const res = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/spec`, {
    headers: { 'Authorization': `Bearer ${sessionToken}` }
  });
  
  return res.json();
}

async function updateSpec(workspaceId: string, spec: any, changeNotes?: string) {
  const res = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/spec`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${sessionToken}`
    },
    body: JSON.stringify({ spec, change_notes: changeNotes })
  });
  
  return res.json();
}

async function patchSpec(workspaceId: string, operations: any[], changeNotes?: string) {
  const res = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/spec`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${sessionToken}`
    },
    body: JSON.stringify({ operations, change_notes: changeNotes })
  });
  
  return res.json();
}

// ==========================================
// 8. 触发 Build
// ==========================================

async function triggerBuild(workspaceId: string) {
  const res = await fetch(`${API_BASE}/api/runs/workspace/${workspaceId}/build`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${sessionToken}` }
  });
  
  return res.json();
}

// ==========================================
// 9. 下载产物
// ==========================================

async function listArtifacts(runId: string) {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/artifacts`, {
    headers: { 'Authorization': `Bearer ${sessionToken}` }
  });
  
  return res.json();
}

function getDownloadUrl(runId: string, artifactId: string) {
  return `${API_BASE}/api/runs/${runId}/artifacts/${artifactId}/download`;
}

// ==========================================
// 完整流程示例
// ==========================================

async function fullDemo() {
  console.log('🚀 Starting Oasis Minecraft Demo...\n');

  // Step 1: 登录
  console.log('Step 1: Logging in...');
  const loginResult = await login('demo@example.com', 'password123');
  console.log('✅ Logged in:', loginResult.user.username, '\n');

  // Step 2: 创建 Workspace
  console.log('Step 2: Creating workspace...');
  const workspace = await createWorkspace('Ruby Mod', 'A mod with ruby gems');
  console.log('✅ Created workspace:', workspace.id, '\n');

  // Step 3: 创建 Conversation
  console.log('Step 3: Creating conversation...');
  const conversation = await createConversation(workspace.id, 'Creating Ruby Items');
  console.log('✅ Created conversation:', conversation.id, '\n');

  // Step 4: 发送消息
  console.log('Step 4: Sending message...');
  const { run_id } = await sendMessage(
    conversation.id,
    'Create a ruby gem item with RARE rarity that glows in the dark'
  );
  console.log('✅ Created run:', run_id, '\n');

  // Step 5: 订阅事件
  console.log('Step 5: Subscribing to events...');
  
  return new Promise<void>((resolve) => {
    const unsubscribe = subscribeToEvents(run_id, {
      onStatus: (status) => {
        console.log(`📊 Status: ${status}`);
        if (status === 'succeeded' || status === 'failed') {
          unsubscribe();
          resolve();
        }
      },
      onProgress: (progress) => {
        console.log(`📈 Progress: ${progress}%`);
      },
      onLog: (message, level) => {
        console.log(`📝 [${level}] ${message}`);
      },
      onSpecPreview: (data) => {
        console.log(`👁️ Spec preview:`, data.delta);
      },
      onAwaitingApproval: async (data) => {
        console.log(`⏳ Awaiting approval. ${data.deltas_count} delta(s) pending.`);
        
        // Step 6: 自动批准 (实际应用中应该等待用户确认)
        console.log('\nStep 6: Approving deltas...');
        const result = await approveDeltas(run_id);
        console.log('✅ Approved! New spec version:', result.spec_version, '\n');
      },
      onArtifact: (artifact) => {
        console.log(`📦 Artifact created: ${artifact.file_name}`);
      }
    });
  });
}

// 运行示例
// fullDemo().then(() => console.log('\n🎉 Demo complete!'));
```

### React Hooks 示例

```tsx
// hooks/useRunEvents.ts
import { useEffect, useState, useCallback } from 'react';

interface RunState {
  status: string;
  progress: number;
  logs: string[];
  pendingDeltas: any[];
  clarifyingQuestions: string[];
}

export function useRunEvents(runId: string | null) {
  const [state, setState] = useState<RunState>({
    status: 'idle',
    progress: 0,
    logs: [],
    pendingDeltas: [],
    clarifyingQuestions: []
  });

  useEffect(() => {
    if (!runId) return;

    const eventSource = new EventSource(
      `/api/runs/${runId}/events`,
      { withCredentials: true }
    );

    eventSource.addEventListener('run.status', (e) => {
      const data = JSON.parse(e.data);
      setState(s => ({ ...s, status: data.payload.status }));
    });

    eventSource.addEventListener('run.progress', (e) => {
      const data = JSON.parse(e.data);
      setState(s => ({ ...s, progress: data.payload.progress }));
    });

    eventSource.addEventListener('log.append', (e) => {
      const data = JSON.parse(e.data);
      setState(s => ({ ...s, logs: [...s.logs, data.payload.message] }));
    });

    eventSource.addEventListener('run.awaiting_approval', (e) => {
      const data = JSON.parse(e.data);
      setState(s => ({
        ...s,
        status: 'awaiting_approval',
        pendingDeltas: data.payload.pending_deltas
      }));
    });

    eventSource.addEventListener('run.awaiting_input', (e) => {
      const data = JSON.parse(e.data);
      setState(s => ({
        ...s,
        status: 'awaiting_input',
        clarifyingQuestions: data.payload.clarifying_questions
      }));
    });

    return () => eventSource.close();
  }, [runId]);

  const approve = useCallback(async () => {
    if (!runId) return;
    await fetch(`/api/runs/${runId}/approve`, {
      method: 'POST',
      credentials: 'include'
    });
  }, [runId]);

  const reject = useCallback(async (reason?: string) => {
    if (!runId) return;
    await fetch(`/api/runs/${runId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ reason })
    });
  }, [runId]);

  return { ...state, approve, reject };
}
```

---

## API 总结表

| 功能 | 方法 | 路径 |
|------|------|------|
| **认证** | | |
| 发送验证码 | POST | `/api/auth/send-verification-code` |
| 注册 | POST | `/api/auth/register` |
| 登录 | POST | `/api/auth/login` |
| Google 登录 | POST | `/api/auth/google-login` |
| 设置用户名 | POST | `/api/auth/set-username` |
| 登出 | POST | `/api/auth/logout` |
| **Workspace** | | |
| 创建 | POST | `/api/workspaces` |
| 列表 | GET | `/api/workspaces` |
| 获取 | GET | `/api/workspaces/{id}` |
| 更新 | PATCH | `/api/workspaces/{id}` |
| 删除 | DELETE | `/api/workspaces/{id}` |
| **Spec** | | |
| 获取 | GET | `/api/workspaces/{id}/spec` |
| 整包更新 | PUT | `/api/workspaces/{id}/spec` |
| 部分更新 | PATCH | `/api/workspaces/{id}/spec` |
| 历史记录 | GET | `/api/workspaces/{id}/spec/history` |
| 回滚 | POST | `/api/workspaces/{id}/spec/rollback/{version}` |
| **Conversation** | | |
| 创建 | POST | `/api/workspaces/{id}/conversations` |
| 列表 | GET | `/api/workspaces/{id}/conversations` |
| 获取 | GET | `/api/conversations/{id}` |
| 更新 | PATCH | `/api/conversations/{id}` |
| 删除 | DELETE | `/api/conversations/{id}` |
| **Message** | | |
| 发送 | POST | `/api/conversations/{id}/messages` |
| 列表 | GET | `/api/conversations/{id}/messages` |
| 获取 | GET | `/api/messages/{id}` |
| **Run** | | |
| 获取 | GET | `/api/runs/{id}` |
| 取消 | POST | `/api/runs/{id}/cancel` |
| 批准 | POST | `/api/runs/{id}/approve` |
| 拒绝 | POST | `/api/runs/{id}/reject` |
| 事件流 | GET | `/api/runs/{id}/events` |
| 历史事件 | GET | `/api/runs/{id}/events/history` |
| 列出 (按 workspace) | GET | `/api/runs/workspace/{id}` |
| 触发 Build | POST | `/api/runs/workspace/{id}/build` |
| **Artifact** | | |
| 列表 | GET | `/api/runs/{id}/artifacts` |
| 获取 | GET | `/api/runs/{id}/artifacts/{aid}` |
| 下载 | GET | `/api/runs/{id}/artifacts/{aid}/download` |

---

## Run 状态流转图

```
                    ┌──────────────┐
                    │   queued     │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   running    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
    ┌─────────────────┐  ┌────────┐  ┌────────┐
    │awaiting_approval│  │ failed │  │canceled│
    └────────┬────────┘  └────────┘  └────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌──────────┐    ┌──────────┐
│succeeded │    │ rejected │
└──────────┘    └──────────┘
    │
    │ (has questions)
    ▼
┌──────────────┐
│awaiting_input│
└──────────────┘
```

