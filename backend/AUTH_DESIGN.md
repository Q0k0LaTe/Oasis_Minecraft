# 多用户认证与Session管理设计文档

## 📋 功能需求分析

### 1. 核心功能
- **用户注册**: 新用户可以通过邮箱/用户名和密码注册账户
- **用户登录**: 已注册用户可以通过凭证登录
- **Session管理**: 登录后创建session，session与用户账户关联
- **Session验证**: API请求时验证session是否有效且属于当前用户
- **用户信息管理**: 用户可以查看和更新自己的信息

### 2. 安全要求
- 密码需要加密存储（使用bcrypt）
- Session token需要安全生成（使用UUID）
- Session永不过期（类似ChatGPT的conversation，需要时手动创建新session）
- 需要防止SQL注入（使用ORM）
- 需要防止暴力破解（可选的登录尝试限制）

### 3. 数据关联
- 每个用户可以有多个sessions（类似ChatGPT的多个conversations）
- 每个job需要关联到session（每个session有自己的历史jobs）
- 每个session属于一个用户
- Session需要记录创建时间、最后使用时间
- Session可以命名（可选，方便用户识别不同的会话）

---

## 🗄️ 数据库模型设计

### 表结构

#### 1. `users` 表
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt加密后的密码
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

**字段说明:**
- `id`: 主键，自增
- `username`: 用户名，唯一，用于登录
- `email`: 邮箱，唯一，用于登录和找回密码
- `password_hash`: 加密后的密码（使用bcrypt）
- `created_at`: 账户创建时间
- `updated_at`: 最后更新时间
- `is_active`: 账户是否激活（可用于禁用账户）

#### 2. `sessions` 表
```sql
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,  -- UUID格式的token
    name VARCHAR(255),  -- 可选：session名称（类似ChatGPT的conversation标题）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,  -- 可选：记录登录设备信息
    ip_address VARCHAR(45),  -- 可选：记录IP地址
    is_active BOOLEAN DEFAULT TRUE  -- 可用于主动删除session
);
```

**字段说明:**
- `id`: 主键
- `user_id`: 外键，关联到users表
- `session_token`: 唯一的session标识符（UUID），用于API认证
- `name`: session名称（可选），用户可以自定义，方便识别不同的会话
- `created_at`: session创建时间
- `last_used_at`: 最后使用时间（每次使用该session时更新）
- `user_agent`: 浏览器/设备信息（可选）
- `ip_address`: IP地址（可选）
- `is_active`: 是否激活（可用于主动删除session，类似ChatGPT删除conversation）

**设计理念:**
- Session永不过期，类似ChatGPT的conversation
- 用户可以创建多个sessions，每个session有独立的历史记录
- 每个session可以命名，方便用户管理

#### 3. `jobs` 表（重构现有的内存存储）
```sql
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    job_id VARCHAR(255) UNIQUE NOT NULL,  -- 现有的UUID格式job_id
    status VARCHAR(50) NOT NULL,  -- queued, analyzing, generating, completed, failed等
    progress INTEGER DEFAULT 0,
    spec JSONB,  -- AI生成的spec信息
    result JSONB,  -- 最终生成结果
    logs JSONB,  -- 日志数组
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**字段说明:**
- `id`: 主键
- `user_id`: 外键，关联到users表（每个job属于一个用户）
- `session_id`: 外键，关联到sessions表（每个job属于一个session，类似ChatGPT的conversation中的消息）
- `job_id`: 现有的UUID格式job_id，保持兼容
- `status`: job状态
- `progress`: 进度百分比
- `spec`: JSON格式存储AI spec
- `result`: JSON格式存储最终结果
- `logs`: JSON数组格式存储日志

**设计理念:**
- 每个job必须属于一个session
- 每个session可以有多个jobs（历史记录）
- 删除session时，相关的jobs也会被删除（CASCADE）
- 这样用户可以查看每个session的历史jobs

---

## 🔌 API接口设计

### 认证相关接口

#### 1. 用户注册
```
POST /api/auth/register
```

**请求体:**
```json
{
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepassword123"
}
```

**响应 (成功):**
```json
{
    "success": true,
    "message": "User registered successfully",
    "user": {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "created_at": "2024-01-01T00:00:00Z"
    }
}
```

**响应 (失败):**
```json
{
    "success": false,
    "error": "Username already exists"
}
```

#### 2. 用户登录
```
POST /api/auth/login
```

**请求体:**
```json
{
    "username": "testuser",  // 或 "email": "test@example.com"
    "password": "securepassword123"
}
```

**响应 (成功):**
```json
{
    "success": true,
    "message": "Login successful",
    "session": {
        "id": 1,
        "token": "550e8400-e29b-41d4-a716-446655440000",
        "name": null,
        "created_at": "2024-01-01T00:00:00Z"
    },
    "user": {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com"
    }
}
```

**注意:** 登录时自动创建第一个session，或者返回现有session（如果存在）

**响应 (失败):**
```json
{
    "success": false,
    "error": "Invalid credentials"
}
```

#### 3. 验证Session
```
GET /api/auth/verify
```

**请求头:**
```
Authorization: Bearer 550e8400-e29b-41d4-a716-446655440000
```
或
```
X-Session-Token: 550e8400-e29b-41d4-a716-446655440000
```

**响应 (成功):**
```json
{
    "success": true,
    "valid": true,
    "user": {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com"
    },
    "session": {
        "id": 1,
        "name": "My First Session",
        "created_at": "2024-01-01T00:00:00Z",
        "last_used_at": "2024-01-15T10:30:00Z"
    }
}
```

**响应 (失败):**
```json
{
    "success": false,
    "valid": false,
    "error": "Invalid session"
}
```

#### 4. 登出
```
POST /api/auth/logout
```

**请求头:**
```
Authorization: Bearer 550e8400-e29b-41d4-a716-446655440000
```

**响应:**
```json
{
    "success": true,
    "message": "Logged out successfully"
}
```

#### 5. 获取当前用户信息
```
GET /api/auth/me
```

**请求头:**
```
Authorization: Bearer 550e8400-e29b-41d4-a716-446655440000
```

**响应:**
```json
{
    "success": true,
    "user": {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "created_at": "2024-01-01T00:00:00Z"
    },
    "current_session": {
        "id": 1,
        "name": "My First Session",
        "created_at": "2024-01-01T00:00:00Z"
    }
}
```

### Session管理接口（类似ChatGPT的conversation管理）

#### 6. 创建新Session（New Conversation）
```
POST /api/sessions/new
```

**请求头:**
```
Authorization: Bearer 550e8400-e29b-41d4-a716-446655440000
```

**请求体（可选）:**
```json
{
    "name": "My New Session"  // 可选：给session起个名字
}
```

**响应:**
```json
{
    "success": true,
    "message": "New session created",
    "session": {
        "id": 2,
        "token": "660e8400-e29b-41d4-a716-446655440001",
        "name": "My New Session",
        "created_at": "2024-01-15T10:30:00Z"
    }
}
```

#### 7. 列出所有Sessions
```
GET /api/sessions
```

**请求头:**
```
Authorization: Bearer 550e8400-e29b-41d4-a716-446655440000
```

**响应:**
```json
{
    "success": true,
    "sessions": [
        {
            "id": 1,
            "name": "My First Session",
            "created_at": "2024-01-01T00:00:00Z",
            "last_used_at": "2024-01-15T10:30:00Z",
            "job_count": 5  // 该session下的jobs数量
        },
        {
            "id": 2,
            "name": "My New Session",
            "created_at": "2024-01-15T10:30:00Z",
            "last_used_at": "2024-01-15T10:30:00Z",
            "job_count": 0
        }
    ]
}
```

#### 8. 获取Session详情（包含所有Jobs历史）
```
GET /api/sessions/{session_id}
```

**请求头:**
```
Authorization: Bearer 550e8400-e29b-41d4-a716-446655440000
```

**响应:**
```json
{
    "success": true,
    "session": {
        "id": 1,
        "name": "My First Session",
        "created_at": "2024-01-01T00:00:00Z",
        "last_used_at": "2024-01-15T10:30:00Z"
    },
    "jobs": [
        {
            "job_id": "abc-123-def",
            "status": "completed",
            "progress": 100,
            "created_at": "2024-01-01T00:00:00Z",
            "aiDecisions": {
                "itemName": "Ruby Gem",
                "modName": "Ruby Mod"
            }
        },
        {
            "job_id": "xyz-789-ghi",
            "status": "completed",
            "progress": 100,
            "created_at": "2024-01-02T00:00:00Z",
            "aiDecisions": {
                "itemName": "Diamond Sword",
                "modName": "Diamond Mod"
            }
        }
    ]
}
```

#### 9. 更新Session名称
```
PATCH /api/sessions/{session_id}
```

**请求头:**
```
Authorization: Bearer 550e8400-e29b-41d4-a716-446655440000
```

**请求体:**
```json
{
    "name": "Updated Session Name"
}
```

**响应:**
```json
{
    "success": true,
    "message": "Session updated",
    "session": {
        "id": 1,
        "name": "Updated Session Name",
        "created_at": "2024-01-01T00:00:00Z"
    }
}
```

#### 10. 删除Session
```
DELETE /api/sessions/{session_id}
```

**请求头:**
```
Authorization: Bearer 550e8400-e29b-41d4-a716-446655440000
```

**响应:**
```json
{
    "success": true,
    "message": "Session deleted"
}
```

**注意:** 删除session时，相关的所有jobs也会被删除（CASCADE）

### 受保护的接口修改

所有现有的API接口需要添加认证中间件，例如：

#### 修改后的接口
```
POST /api/generate-mod  # 需要认证，job自动关联到当前session
GET /api/status/{job_id}  # 需要认证，且只能查看自己session的job
GET /downloads/{filename}  # 需要认证，且只能下载自己session的文件
POST /api/jobs/{job_id}/select-image  # 需要认证
POST /api/jobs/{job_id}/regenerate-images  # 需要认证
```

**重要说明:**
- 所有API请求都需要在Header中携带 `Authorization: Bearer <session_token>`
- 从token中解析出session_id，所有创建的jobs自动关联到该session
- 用户只能访问自己sessions下的jobs
- 如果需要切换到另一个session，使用新的session_token即可

---

## 🛠️ 技术栈选择

### 数据库ORM
- **SQLAlchemy**: Python最流行的ORM，支持PostgreSQL
- **Alembic**: 数据库迁移工具（SQLAlchemy的官方迁移工具）

### 密码加密
- **bcrypt**: 行业标准的密码哈希库

### Session管理
- **UUID**: 生成唯一的session token
- **datetime**: 记录创建时间和最后使用时间
- **无过期机制**: Session永不过期，类似ChatGPT的conversation

### 依赖包
需要添加到 `requirements.txt`:
```
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9  # PostgreSQL驱动
bcrypt==4.1.1
python-jose[cryptography]==3.3.0  # 可选：如果未来想用JWT
```

---

## 📝 实施步骤

### 阶段1: 数据库设置
1. ✅ 安装PostgreSQL和必要的Python包
2. ✅ 创建数据库连接配置
3. ✅ 设置SQLAlchemy和Alembic
4. ✅ 创建数据库模型（users, sessions, jobs）
5. ✅ 运行数据库迁移

### 阶段2: 认证核心功能
6. ✅ 实现密码加密/验证工具函数
7. ✅ 实现用户注册接口
8. ✅ 实现用户登录接口
9. ✅ 实现Session创建和管理（创建新session、列出sessions等）
10. ✅ 实现Session验证中间件

### 阶段3: API保护
11. ✅ 修改现有API接口，添加认证要求
12. ✅ 修改jobs存储，从内存迁移到数据库
13. ✅ 确保用户只能访问自己的jobs

### 阶段4: 测试
14. ✅ 使用curl测试所有接口
15. ✅ 测试各种边界情况（无效session等）

---

## 🔒 安全考虑

1. **密码安全**
   - 使用bcrypt加密，salt自动生成
   - 密码最小长度要求（建议8字符）
   - 不在响应中返回密码或密码哈希

2. **Session安全**
   - Session token使用UUID，足够随机
   - Session永不过期，但支持主动删除
   - 用户可以创建多个sessions，每个session独立管理
   - 记录IP和User-Agent（可选，用于安全审计）

3. **API安全**
   - 所有敏感操作需要认证
   - 用户只能访问自己的资源
   - 使用HTTPS（生产环境）

4. **数据库安全**
   - 使用参数化查询（ORM自动处理）
   - 数据库连接使用环境变量配置
   - 定期备份数据库

---

## 📊 数据库关系图

```
users (1) ──< (N) sessions
sessions (1) ──< (N) jobs
users (1) ──< (N) jobs (通过sessions间接关联)
```

- 一个用户可以有多个sessions（类似ChatGPT的多个conversations）
- 一个session可以有多个jobs（每个session有独立的历史记录）
- 删除用户时，相关的sessions和jobs也会被删除（CASCADE）
- 删除session时，相关的jobs也会被删除（CASCADE）

---

## 🧪 测试计划

### 注册流程测试
```bash
# 1. 注册新用户
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"test123456"}'

# 2. 尝试注册重复用户名（应该失败）
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test2@example.com","password":"test123456"}'
```

### 登录流程测试
```bash
# 1. 正确登录
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test123456"}'

# 2. 错误密码（应该失败）
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"wrongpassword"}'
```

### Session验证测试
```bash
# 1. 验证有效session
curl -X GET http://localhost:3000/api/auth/verify \
  -H "Authorization: Bearer <session_token>"

# 2. 验证无效session（应该失败）
curl -X GET http://localhost:3000/api/auth/verify \
  -H "Authorization: Bearer invalid-token-12345"
```

### Session管理测试
```bash
# 1. 创建新session
curl -X POST http://localhost:3000/api/sessions/new \
  -H "Authorization: Bearer <session_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"My New Session"}'

# 2. 列出所有sessions
curl -X GET http://localhost:3000/api/sessions \
  -H "Authorization: Bearer <session_token>"

# 3. 获取某个session的详情和历史jobs
curl -X GET http://localhost:3000/api/sessions/1 \
  -H "Authorization: Bearer <session_token>"

# 4. 更新session名称
curl -X PATCH http://localhost:3000/api/sessions/1 \
  -H "Authorization: Bearer <session_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Name"}'

# 5. 删除session
curl -X DELETE http://localhost:3000/api/sessions/1 \
  -H "Authorization: Bearer <session_token>"
```

### 受保护接口测试
```bash
# 1. 无认证访问（应该失败）
curl -X POST http://localhost:3000/api/generate-mod \
  -H "Content-Type: application/json" \
  -d '{"prompt":"test item"}'

# 2. 有认证访问（应该成功，job会自动关联到当前session）
curl -X POST http://localhost:3000/api/generate-mod \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <session_token>" \
  -d '{"prompt":"test item"}'

# 3. 查看当前session的所有jobs
curl -X GET http://localhost:3000/api/sessions/current/jobs \
  -H "Authorization: Bearer <session_token>"
```

---

## 📌 下一步行动

1. 确认设计是否符合需求
2. 开始实施阶段1：数据库设置
3. 每完成一个阶段，使用curl测试
4. 逐步完善和优化

