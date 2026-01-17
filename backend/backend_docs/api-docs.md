# Minecraft Mod Generator API

AI-powered Minecraft Fabric mod generator - IDE Edition

**版本**: 2.0.0
**生成时间**: 2026-01-14 16:32:26

---

## API 端点

### /

#### `GET` /

**Root**

Root endpoint

**响应:**

**200** - Successful Response

```json
{}
```

---

### /api/assets/{asset_id}

#### `GET` /api/assets/{asset_id}

**Get Asset File**

Get an asset file by ID

Returns the actual file for display/download.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `asset_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
{}
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

#### `DELETE` /api/assets/{asset_id}

**Delete Asset**

Delete an asset

Removes both the database record and the file.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `asset_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**204** - Successful Response

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/assets/{asset_id}/info

#### `GET` /api/assets/{asset_id}/info

**Get Asset Info**

Get asset metadata (without file content)

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `asset_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/AssetResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/auth/deactivate

#### `POST` /api/auth/deactivate

**Deactivate**

Deactivate user account (soft delete)

Sets User.is_active=False, invalidates all sessions, and clears the HttpOnly cookie.

Requires additional verification:
- For email/password users: must provide password
- For Google OAuth users: must provide valid id_token

Idempotent: can be called multiple times without error.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `authorization` | header | string | ❌ |  |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/DeactivateRequest

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/DeactivateResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/auth/delete-account

#### `POST` /api/auth/delete-account

**Delete Account**

Permanently delete user account (hard delete)

This will permanently delete the user account and all associated data:
- All sessions
- All workspaces and their contents (conversations, runs, assets, etc.)

Requires additional verification:
- For email/password users: must provide password
- For Google OAuth users: must provide valid id_token
- Must type 'DELETE' in confirmation field to prevent accidental deletion

WARNING: This action is irreversible!

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `authorization` | header | string | ❌ |  |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/DeleteAccountRequest

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/DeleteAccountResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/auth/google-client-id

#### `GET` /api/auth/google-client-id

**Get Google Client Id**

Get Google OAuth Client ID for frontend

Returns the Google Client ID that frontend needs to initialize Google Sign-In.

**响应:**

**200** - Successful Response

```json
{}
```

---

### /api/auth/google-login

#### `POST` /api/auth/google-login

**Google Login**

Login with Google OAuth

Verifies Google ID Token and either:
- Creates a session for existing users (sets HttpOnly cookie)
- Returns requires_username=true for first-time users

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/GoogleLoginRequest

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/GoogleLoginResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/auth/login

#### `POST` /api/auth/login

**Login**

Login user and create session

Can login with either username or email.
Creates a new session and sets HttpOnly cookie.

Security:
- Session token stored in HttpOnly cookie (XSS protection)
- Session expires after configured duration (default 7 days)

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/LoginRequest

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/LoginResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/auth/logout

#### `POST` /api/auth/logout

**Logout**

Logout from current session

Invalidates the current session token and clears the HttpOnly cookie.

Idempotent: returns success even if token is already invalid or doesn't exist
(to prevent information leakage about token existence).

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `authorization` | header | string | ❌ |  |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/LogoutResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/auth/logout-all

#### `POST` /api/auth/logout-all

**Logout All**

Logout from all sessions

Invalidates all active sessions for the current user and clears the HttpOnly cookie.
Requires a valid session token to identify the user.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `authorization` | header | string | ❌ |  |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/LogoutAllResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/auth/reactivate

#### `POST` /api/auth/reactivate

**Reactivate**

Reactivate a deactivated user account

Re-enables a user account that was previously deactivated (soft deleted).
User must provide authentication credentials to verify identity.

Requires:
- Email or username to identify the account
- For email/password users: must provide password
- For Google OAuth users: must provide valid id_token

Note: This endpoint can be called without authentication since the user
cannot login when their account is deactivated.

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/ReactivateRequest

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/ReactivateResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/auth/register

#### `POST` /api/auth/register

**Register**

Register a new user with email verification

Requires valid verification code before creating account.
Username and email must be unique.

Note: Registration does NOT auto-login. User must call /login after registration.

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/RegisterRequest

**响应:**

**201** - Successful Response

```json
// 引用: #/components/schemas/RegisterResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/auth/send-verification-code

#### `POST` /api/auth/send-verification-code

**Send Verification Code Endpoint**

Send verification code to email address

Generates a 6-digit code, stores it in Redis, and sends it via email.
Code expires in 10 minutes.

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/SendVerificationCodeRequest

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/SendVerificationCodeResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/auth/set-username

#### `POST` /api/auth/set-username

**Set Username**

Set username for first-time Google login users

Creates a new user account with Google OAuth information and sets HttpOnly cookie.

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/SetUsernameRequest

**响应:**

**201** - Successful Response

```json
// 引用: #/components/schemas/SetUsernameResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/auth/verify-code

#### `POST` /api/auth/verify-code

**Verify Code Endpoint**

Verify email verification code

Checks if the provided code matches the stored code for the email.
Code is NOT deleted here, allowing it to be used again during registration.

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/VerifyCodeRequest

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/VerifyCodeResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/conversations/{conversation_id}

#### `GET` /api/conversations/{conversation_id}

**Get Conversation**

Get a single conversation by ID

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `conversation_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/ConversationResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

#### `PATCH` /api/conversations/{conversation_id}

**Update Conversation**

Update conversation metadata (title)

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `conversation_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/ConversationUpdate

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/ConversationResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

#### `DELETE` /api/conversations/{conversation_id}

**Delete Conversation**

Delete a conversation and all its messages

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `conversation_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**204** - Successful Response

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/conversations/{conversation_id}/messages

#### `GET` /api/conversations/{conversation_id}/messages

**List Messages**

List all messages in a conversation

Messages are returned in chronological order (oldest first).

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `conversation_id` | path | string (uuid) | ✅ |  |
| `skip` | query | integer | ❌ |  |
| `limit` | query | integer | ❌ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/MessageListResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

#### `POST` /api/conversations/{conversation_id}/messages

**Send Message**

Send a user message to a conversation

If trigger_run=True (default), this will:
1. Create the user message
2. Create a Run in 'queued' status
3. Start the run in background
4. Return the message and run_id

The run will:
- Emit events as it progresses
- Eventually create an assistant message with results

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `conversation_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/MessageCreate

**响应:**

**201** - Successful Response

```json
// 引用: #/components/schemas/SendMessageResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/health

#### `GET` /api/health

**Health Check**

Health check endpoint

**响应:**

**200** - Successful Response

```json
{}
```

---

### /api/messages/{message_id}

#### `GET` /api/messages/{message_id}

**Get Message**

Get a single message by ID

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `message_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/MessageResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/runs/workspace/{workspace_id}

#### `GET` /api/runs/workspace/{workspace_id}

**List Workspace Runs**

List all runs for a workspace

Optional status filter: queued, running, succeeded, failed, canceled

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `skip` | query | integer | ❌ |  |
| `limit` | query | integer | ❌ |  |
| `status_filter` | query | string | ❌ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/RunListResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/runs/workspace/{workspace_id}/build

#### `POST` /api/runs/workspace/{workspace_id}/build

**Trigger Build**

Trigger a build run for a workspace

This will compile the current spec to a JAR using the V2 pipeline.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**201** - Successful Response

```json
// 引用: #/components/schemas/RunResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/runs/{run_id}

#### `GET` /api/runs/{run_id}

**Get Run**

Get a run by ID

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `run_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/RunResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/runs/{run_id}/approve

#### `POST` /api/runs/{run_id}/approve

**Approve Run**

Approve pending spec deltas and apply them to the workspace

Called when user reviews the AI-generated changes and clicks 'Approve'.
Optionally accepts modified deltas if user edited them before approving.

Only works for runs in 'awaiting_approval' status.

Returns:
    - success: bool
    - spec_version: new version number
    - status: new run status ('succeeded' or 'awaiting_input' if questions remain)
    - spec_summary: summary of the updated spec

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `run_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `application/json`

```json
{}
```

**响应:**

**200** - Successful Response

```json
{}
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/runs/{run_id}/artifacts

#### `GET` /api/runs/{run_id}/artifacts

**List Artifacts**

List all artifacts produced by a run

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `run_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/ArtifactListResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/runs/{run_id}/artifacts/{artifact_id}

#### `GET` /api/runs/{run_id}/artifacts/{artifact_id}

**Get Artifact**

Get a single artifact by ID

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `run_id` | path | string (uuid) | ✅ |  |
| `artifact_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/ArtifactResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/runs/{run_id}/artifacts/{artifact_id}/download

#### `GET` /api/runs/{run_id}/artifacts/{artifact_id}/download

**Download Artifact**

Download an artifact file

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `run_id` | path | string (uuid) | ✅ |  |
| `artifact_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
{}
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/runs/{run_id}/cancel

#### `POST` /api/runs/{run_id}/cancel

**Cancel Run**

Cancel a running job

Only works for runs in 'queued' or 'running' status.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `run_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/RunResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/runs/{run_id}/events

#### `GET` /api/runs/{run_id}/events

**Stream Events**

Stream run events via Server-Sent Events (SSE)

Connect to this endpoint to receive real-time updates about run progress.

Query params:
- since: Event ID to start from (for reconnection)

Event types:
- run.status: Status change (queued/running/succeeded/failed/canceled)
- run.progress: Progress update (0-100)
- log.append: Log message
- spec.preview / spec.patch / spec.saved: Spec changes
- asset.generated / asset.selected: Asset events
- artifact.created: New artifact available
- task.started / task.finished: Pipeline task events

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `run_id` | path | string (uuid) | ✅ |  |
| `since` | query | string | ❌ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
{}
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/runs/{run_id}/events/history

#### `GET` /api/runs/{run_id}/events/history

**Get Event History**

Get historical events for a run (non-streaming)

Useful for loading past events or catching up after reconnection.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `run_id` | path | string (uuid) | ✅ |  |
| `skip` | query | integer | ❌ |  |
| `limit` | query | integer | ❌ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
{}
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/runs/{run_id}/reject

#### `POST` /api/runs/{run_id}/reject

**Reject Run**

Reject pending spec deltas - discard them without applying

Called when user reviews the AI-generated changes and clicks 'Reject'.
The run is marked as rejected and no changes are made to the workspace spec.

Only works for runs in 'awaiting_approval' status.

Returns:
    - success: bool
    - status: 'rejected'
    - message: confirmation message

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `run_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `application/json`

```json
{}
```

**响应:**

**200** - Successful Response

```json
{}
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/subscriptions

#### `POST` /api/subscriptions

**Subscribe**

订阅产品更新通知

用户无需注册登录即可订阅。同一邮箱重复订阅会幂等返回成功。

**默认值**：
- 不需要登录
- 不需要邮箱验证（只做格式校验）
- 不允许重复订阅（同一 email 幂等）
- 记录来源信息（source/utm、ip、user_agent）

**安全防护**：
- 按 IP 和邮箱限流（防止滥用）
- 返回信息不泄露邮箱是否存在（防枚举）

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/SubscribeRequest

**响应:**

**201** - Successful Response

```json
// 引用: #/components/schemas/SubscribeResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/subscriptions/admin/list

#### `GET` /api/subscriptions/admin/list

**List Subscriptions**

管理员接口：获取订阅列表

需要管理员权限。支持分页、按状态过滤、按创建时间排序。

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `status_filter` | query | string | ❌ | Filter by status (subscribed, unsubscribed, bounced) |
| `page` | query | integer | ❌ | Page number |
| `page_size` | query | integer | ❌ | Page size |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/SubscriptionListResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/subscriptions/unsubscribe

#### `POST` /api/subscriptions/unsubscribe

**Unsubscribe**

退订产品更新通知

使用 unsubscribe_token 或 email + token 进行退订。
返回信息不泄露订阅状态（防枚举）。

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/UnsubscribeRequest

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/UnsubscribeResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/workspaces

#### `POST` /api/workspaces

**Create Workspace**

Create a new workspace

Creates a new Minecraft Mod project workspace for the current user.
Optionally initialize with a spec.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/WorkspaceCreate

**响应:**

**201** - Successful Response

```json
// 引用: #/components/schemas/WorkspaceResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

#### `GET` /api/workspaces

**List Workspaces**

List all workspaces for the current user

Returns workspaces sorted by last_modified_at (most recent first).

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `skip` | query | integer | ❌ |  |
| `limit` | query | integer | ❌ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/WorkspaceListResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/workspaces/{workspace_id}

#### `GET` /api/workspaces/{workspace_id}

**Get Workspace**

Get a single workspace by ID

Set include_spec=false to exclude the spec from the response.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `include_spec` | query | boolean | ❌ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/WorkspaceResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

#### `PATCH` /api/workspaces/{workspace_id}

**Update Workspace**

Update workspace metadata (name, description, cover)

Does not update spec - use the spec endpoints for that.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/WorkspaceUpdate

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/WorkspaceResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

#### `DELETE` /api/workspaces/{workspace_id}

**Delete Workspace**

Delete a workspace

This will cascade delete all conversations, messages, runs, and assets.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**204** - Successful Response

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/workspaces/{workspace_id}/assets

#### `POST` /api/workspaces/{workspace_id}/assets

**Upload Asset**

Upload an asset (texture, cover, etc.) to a workspace

Supported asset types:
- cover: Workspace cover image
- texture: Block/item/tool texture (16x16 PNG recommended)
- reference: Reference image for texture generation

For textures, optionally specify target_type and target_id to bind
the asset to a specific block/item/tool in the spec.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `multipart/form-data`

Schema: #/components/schemas/Body_upload_asset_api_workspaces__workspace_id__assets_post

**响应:**

**201** - Successful Response

```json
// 引用: #/components/schemas/AssetResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

#### `GET` /api/workspaces/{workspace_id}/assets

**List Assets**

List assets for a workspace

Optional filters:
- asset_type: Filter by type (cover, texture, reference)
- target_type: Filter by target type (block, item, tool)
- target_id: Filter by target element ID

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `asset_type` | query | string | ❌ |  |
| `target_type` | query | string | ❌ |  |
| `target_id` | query | string | ❌ |  |
| `skip` | query | integer | ❌ |  |
| `limit` | query | integer | ❌ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/AssetListResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/workspaces/{workspace_id}/assets/select

#### `POST` /api/workspaces/{workspace_id}/assets/select

**Select Asset**

Bind an asset to a spec element (block/item/tool)

This updates the asset's target_type and target_id to associate it
with a specific element in the workspace spec.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/AssetSelectRequest

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/AssetSelectResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/workspaces/{workspace_id}/conversations

#### `POST` /api/workspaces/{workspace_id}/conversations

**Create Conversation**

Create a new conversation in a workspace

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/ConversationCreate

**响应:**

**201** - Successful Response

```json
// 引用: #/components/schemas/ConversationResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

#### `GET` /api/workspaces/{workspace_id}/conversations

**List Conversations**

List all conversations in a workspace

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `skip` | query | integer | ❌ |  |
| `limit` | query | integer | ❌ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/ConversationListResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/workspaces/{workspace_id}/spec

#### `GET` /api/workspaces/{workspace_id}/spec

**Get Spec**

Get the current spec for a workspace

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/SpecResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

#### `PUT` /api/workspaces/{workspace_id}/spec

**Update Spec**

Replace the entire spec (full update)

This creates a new version in spec_history.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/SpecUpdate

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/SpecResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

#### `PATCH` /api/workspaces/{workspace_id}/spec

**Patch Spec**

Apply partial updates to the spec (patch)

Accepts a list of operations in the format:
[{"op": "add"|"update"|"remove", "path": "items[0].rarity", "value": "RARE"}]

This creates a new version in spec_history.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**请求体:**

Content-Type: `application/json`

Schema: #/components/schemas/SpecPatch

**响应:**

**200** - Successful Response

```json
// 引用: #/components/schemas/SpecResponse
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/workspaces/{workspace_id}/spec/history

#### `GET` /api/workspaces/{workspace_id}/spec/history

**Get Spec History**

Get spec version history for a workspace

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `skip` | query | integer | ❌ |  |
| `limit` | query | integer | ❌ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
{}
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

### /api/workspaces/{workspace_id}/spec/rollback/{version}

#### `POST` /api/workspaces/{workspace_id}/spec/rollback/{version}

**Rollback Spec**

Rollback spec to a previous version

Creates a new version with the old spec content.

**请求参数:**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| `workspace_id` | path | string (uuid) | ✅ |  |
| `version` | path | integer | ✅ |  |
| `authorization` | header | string | ❌ | Authorization header (Bearer token) |
| `session_token` | cookie | string | ❌ |  |

**响应:**

**200** - Successful Response

```json
{}
```

**422** - Validation Error

```json
// 引用: #/components/schemas/HTTPValidationError
```

---

## 数据模型

### ApproveRequest

Request body for approving run deltas

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `modified_deltas` | string | ❌ |  |

---

### ArtifactListResponse

Response schema for artifact list

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `artifacts` | array[object] | ✅ |  |
| `total` | integer | ✅ |  |

---

### ArtifactResponse

Response schema for an artifact

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `artifact_type` | string | ✅ |  |
| `created_at` | string (date-time) | ✅ |  |
| `download_url` | string | ❌ |  |
| `file_name` | string | ✅ |  |
| `file_path` | string | ✅ |  |
| `file_size` | string | ❌ |  |
| `id` | string (uuid) | ✅ |  |
| `meta_data` | string | ❌ |  |
| `mime_type` | string | ❌ |  |
| `run_id` | string (uuid) | ✅ |  |
| `workspace_id` | string (uuid) | ✅ |  |

---

### AssetListResponse

Response schema for asset list

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `assets` | array[object] | ✅ |  |
| `total` | integer | ✅ |  |

---

### AssetResponse

Response schema for an asset

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `asset_type` | string | ✅ |  |
| `created_at` | string (date-time) | ✅ |  |
| `file_name` | string | ✅ |  |
| `file_path` | string | ✅ |  |
| `id` | string (uuid) | ✅ |  |
| `meta_data` | string | ❌ |  |
| `mime_type` | string | ❌ |  |
| `target_id` | string | ❌ |  |
| `target_type` | string | ❌ |  |
| `updated_at` | string (date-time) | ✅ |  |
| `url` | string | ❌ |  |
| `workspace_id` | string (uuid) | ✅ |  |

---

### AssetSelectRequest

Request schema for binding an asset to a spec element

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `asset_id` | string (uuid) | ✅ | Asset ID to bind |
| `target_id` | string | ✅ | Target element ID in spec |
| `target_type` | string | ✅ | Target element type |

---

### AssetSelectResponse

Response schema for asset selection

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `asset` | string | ✅ |  |
| `message` | string | ✅ |  |
| `success` | boolean | ✅ |  |

---

### Body_upload_asset_api_workspaces__workspace_id__assets_post

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `asset_type` | string | ✅ |  |
| `file` | string (binary) | ✅ |  |
| `target_id` | string | ❌ |  |
| `target_type` | string | ❌ |  |

---

### ConversationCreate

Request schema for creating a conversation

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `title` | string | ❌ | Conversation title |

---

### ConversationListResponse

Response schema for conversation list

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `conversations` | array[object] | ✅ |  |
| `total` | integer | ✅ |  |

---

### ConversationResponse

Response schema for a single conversation

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `created_at` | string (date-time) | ✅ |  |
| `id` | string (uuid) | ✅ |  |
| `message_count` | string | ❌ |  |
| `title` | string | ❌ |  |
| `updated_at` | string (date-time) | ✅ |  |
| `workspace_id` | string (uuid) | ✅ |  |

---

### ConversationUpdate

Request schema for updating a conversation

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `title` | string | ❌ |  |

---

### DeactivateRequest

Deactivate account request

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `id_token` | string | ❌ | Google ID Token (required for Google OAuth users) |
| `password` | string | ❌ | Password (required for email/password users) |

---

### DeactivateResponse

Deactivate account response

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `success` | boolean | ✅ |  |

---

### DeleteAccountRequest

Delete account request (permanent deletion)

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `confirmation` | string | ✅ | Type 'DELETE' to confirm permanent account deletion |
| `id_token` | string | ❌ | Google ID Token (required for Google OAuth users) |
| `password` | string | ❌ | Password (required for email/password users) |

---

### DeleteAccountResponse

Delete account response

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `success` | boolean | ✅ |  |

---

### GoogleLoginRequest

Google OAuth login request

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `id_token` | string | ✅ | Google ID Token from client |

---

### GoogleLoginResponse

Google OAuth login response

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `requires_username` | boolean | ✅ | Whether user needs to set username (first-time login) |
| `session` | string | ❌ |  |
| `success` | boolean | ✅ |  |
| `user` | string | ❌ |  |

---

### HTTPValidationError

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `detail` | array[object] | ❌ |  |

---

### LoginRequest

User login request - can use username or email

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `email` | string | ❌ | Email for login |
| `password` | string | ✅ | Password |
| `username` | string | ❌ | Username for login |

---

### LoginResponse

User login response

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `session` | string | ❌ |  |
| `success` | boolean | ✅ |  |
| `user` | string | ❌ |  |

---

### LogoutAllResponse

Logout all sessions response

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `revoked_count` | integer | ❌ | Number of sessions revoked |
| `success` | boolean | ✅ |  |

---

### LogoutResponse

Logout response

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `revoked` | boolean | ❌ | Whether a session was actually revoked |
| `success` | boolean | ✅ |  |

---

### MessageCreate

Request schema for creating a message (user message)

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `content` | string | ✅ | Message content |
| `content_type` | string | ❌ | Content format |
| `metadata` | string | ❌ | Additional metadata |
| `run_type` | string | ❌ | Type of run to trigger |
| `trigger_run` | boolean | ❌ | Whether to start a generation run |

---

### MessageListResponse

Response schema for message list

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `conversation_id` | string (uuid) | ✅ |  |
| `messages` | array[object] | ✅ |  |
| `total` | integer | ✅ |  |

---

### MessageResponse

Response schema for a single message

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `content` | string | ❌ |  |
| `content_type` | string | ❌ |  |
| `conversation_id` | string (uuid) | ✅ |  |
| `created_at` | string (date-time) | ✅ |  |
| `id` | string (uuid) | ✅ |  |
| `meta_data` | string | ❌ |  |
| `role` | string | ✅ |  |
| `trigger_run_id` | string | ❌ |  |

---

### ReactivateRequest

Reactivate account request

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `email` | string | ❌ | Email address of the account to reactivate |
| `id_token` | string | ❌ | Google ID Token (required for Google OAuth users) |
| `password` | string | ❌ | Password (required for email/password users) |
| `username` | string | ❌ | Username of the account to reactivate |

---

### ReactivateResponse

Reactivate account response

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `success` | boolean | ✅ |  |
| `user` | string | ❌ |  |

---

### RegisterRequest

User registration request

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `email` | string (email) | ✅ | Valid email address |
| `password` | string | ✅ | Password (minimum 8 characters) |
| `username` | string | ✅ | Username (3-50 characters) |
| `verification_code` | string | ✅ | Email verification code (6 digits) |

---

### RegisterResponse

User registration response

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `success` | boolean | ✅ |  |
| `user` | string | ❌ |  |

---

### RejectRequest

Request body for rejecting run deltas

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `reason` | string | ❌ |  |

---

### RunListResponse

Response schema for run list

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `runs` | array[object] | ✅ |  |
| `total` | integer | ✅ |  |

---

### RunResponse

Response schema for a single run

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `conversation_id` | string | ❌ |  |
| `created_at` | string (date-time) | ✅ |  |
| `error` | string | ❌ |  |
| `error_details` | string | ❌ |  |
| `finished_at` | string | ❌ |  |
| `id` | string (uuid) | ✅ |  |
| `progress` | integer | ❌ |  |
| `result` | string | ❌ |  |
| `run_type` | string | ✅ |  |
| `started_at` | string | ❌ |  |
| `status` | string | ✅ |  |
| `trigger_message_id` | string | ❌ |  |
| `workspace_id` | string (uuid) | ✅ |  |

---

### SendMessageResponse

Response schema for sending a message (includes triggered run info)

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `run_id` | string | ❌ | ID of the triggered run (if trigger_run=True) |
| `run_status` | string | ❌ | Initial run status |

---

### SendVerificationCodeRequest

Request to send verification code to email

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `email` | string (email) | ✅ | Email address to send verification code |

---

### SendVerificationCodeResponse

Response for sending verification code

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `success` | boolean | ✅ |  |

---

### SessionInfo

Session information in responses

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `created_at` | string (date-time) | ✅ |  |
| `id` | integer | ✅ |  |
| `name` | string | ❌ |  |
| `token` | string | ✅ |  |

---

### SetUsernameRequest

Request to set username for first-time Google login

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `id_token` | string | ✅ | Google ID Token from client |
| `username` | string | ✅ | Username (3-50 characters) |

---

### SetUsernameResponse

Response for setting username

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `session` | string | ❌ |  |
| `success` | boolean | ✅ |  |
| `user` | string | ❌ |  |

---

### SpecPatch

Request schema for partial spec update (PATCH)

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `change_notes` | string | ❌ | Description of changes |
| `operations` | array[object] | ✅ | List of patch operations: [{op: 'add'|'update'|'remove', path: '...', value: ...}] |

---

### SpecResponse

Response schema for spec

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `last_modified_at` | string (date-time) | ✅ |  |
| `spec` | object | ✅ |  |
| `version` | integer | ✅ |  |
| `workspace_id` | string (uuid) | ✅ |  |

---

### SpecUpdate

Request schema for full spec update (PUT)

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `change_notes` | string | ❌ | Description of changes |
| `spec` | object | ✅ | Complete mod spec (JSON) |

---

### SubscribeRequest

Request schema for subscribing to updates

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `email` | string (email) | ✅ | Email address to subscribe |
| `source` | string | ❌ | Source of subscription (landing, cli, etc.) |
| `utm_campaign` | string | ❌ | UTM campaign parameter |
| `utm_content` | string | ❌ | UTM content parameter |
| `utm_medium` | string | ❌ | UTM medium parameter |
| `utm_source` | string | ❌ | UTM source parameter |
| `utm_term` | string | ❌ | UTM term parameter |

---

### SubscribeResponse

Response schema for subscription

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `success` | boolean | ✅ |  |

---

### SubscriptionListResponse

Response schema for subscription list

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `page` | integer | ✅ |  |
| `page_size` | integer | ✅ |  |
| `subscriptions` | array[object] | ✅ |  |
| `total` | integer | ✅ |  |

---

### SubscriptionResponse

Response schema for a single subscription

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `created_at` | string (date-time) | ✅ |  |
| `email` | string | ✅ |  |
| `id` | integer | ✅ |  |
| `ip_address` | string | ❌ |  |
| `source` | string | ❌ |  |
| `status` | string | ✅ |  |
| `unsubscribed_at` | string | ❌ |  |
| `utm_campaign` | string | ❌ |  |
| `utm_medium` | string | ❌ |  |
| `utm_source` | string | ❌ |  |

---

### UnsubscribeRequest

Request schema for unsubscribing

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `email` | string | ❌ | Email address (optional if token is provided) |
| `unsubscribe_token` | string | ✅ | Unsubscribe token |

---

### UnsubscribeResponse

Response schema for unsubscription

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `success` | boolean | ✅ |  |

---

### UserInfo

User information in responses

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `created_at` | string (date-time) | ✅ |  |
| `email` | string | ✅ |  |
| `id` | string (uuid) | ✅ |  |
| `username` | string | ✅ |  |

---

### ValidationError

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `loc` | array[object] | ✅ |  |
| `msg` | string | ✅ |  |
| `type` | string | ✅ |  |

---

### VerifyCodeRequest

Request to verify code

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `code` | string | ✅ | Verification code (6 digits) |
| `email` | string (email) | ✅ | Email address |

---

### VerifyCodeResponse

Response for code verification

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message` | string | ✅ |  |
| `success` | boolean | ✅ |  |
| `valid` | boolean | ✅ |  |

---

### WorkspaceCreate

Request schema for creating a workspace

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `cover_image_url` | string | ❌ | Cover image URL |
| `description` | string | ❌ | Workspace description |
| `name` | string | ✅ | Workspace name |
| `spec` | string | ❌ | Initial mod spec (JSON) |

---

### WorkspaceListResponse

Response schema for workspace list

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `total` | integer | ✅ |  |
| `workspaces` | array[object] | ✅ |  |

---

### WorkspaceResponse

Response schema for a single workspace

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `cover_image_url` | string | ❌ |  |
| `created_at` | string (date-time) | ✅ |  |
| `description` | string | ❌ |  |
| `id` | string (uuid) | ✅ |  |
| `last_modified_at` | string (date-time) | ✅ |  |
| `name` | string | ✅ |  |
| `owner_id` | string (uuid) | ✅ |  |
| `spec` | string | ❌ |  |
| `spec_version` | integer | ✅ |  |
| `updated_at` | string (date-time) | ✅ |  |

---

### WorkspaceUpdate

Request schema for updating a workspace

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `cover_image_url` | string | ❌ |  |
| `description` | string | ❌ |  |
| `name` | string | ❌ |  |

---
