# API 端点文档

本文档列出了 IaC4 项目中所有已实现的 API 端点。

## 服务器信息

- **基础 URL**: `http://localhost:8666`
- **API 文档**: `http://localhost:8666/docs` (Swagger UI)
- **备用文档**: `http://localhost:8666/redoc` (ReDoc)

## 启动服务器

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8666 --reload
```

## API 端点列表

### 1. 健康检查

#### GET /health
检查系统健康状态

**响应示例**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "healthy",
  "environment": "development"
}
```

---

### 2. 安全策略管理 (`/api/policies`)

#### GET /api/policies
获取所有安全策略

**查询参数**:
- `skip`: 跳过的记录数 (默认: 0)
- `limit`: 返回的最大记录数 (默认: 100)
- `enabled_only`: 仅返回已启用的策略 (默认: false)

#### POST /api/policies
创建新的安全策略

**请求体**:
```json
{
  "name": "禁止SSH公网访问",
  "description": "禁止开放0.0.0.0/0访问22端口",
  "natural_language_rule": "禁止开放0.0.0.0/0访问22端口(SSH)",
  "cloud_platform": "all",
  "severity": "error",
  "enabled": true
}
```

#### GET /api/policies/{policy_id}
获取指定ID的安全策略

#### PUT /api/policies/{policy_id}
更新安全策略

#### DELETE /api/policies/{policy_id}
删除安全策略

#### PATCH /api/policies/{policy_id}/toggle
切换策略启用状态

---

### 3. LLM 配置管理 (`/api/llm-config`)

#### GET /api/llm-config
获取所有 LLM 配置

**查询参数**:
- `skip`: 跳过的记录数 (默认: 0)
- `limit`: 返回的最大记录数 (默认: 100)
- `active_only`: 仅返回激活的配置 (默认: false)

#### POST /api/llm-config
创建新的 LLM 配置

**请求体**:
```json
{
  "config_name": "OpenAI GPT-4",
  "api_endpoint": "https://api.openai.com/v1",
  "api_key": "sk-xxx",
  "model_name": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 4000,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "timeout": 60
}
```

#### GET /api/llm-config/{config_id}
获取指定ID的LLM配置

#### PUT /api/llm-config/{config_id}
更新LLM配置

#### DELETE /api/llm-config/{config_id}
删除LLM配置

#### POST /api/llm-config/{config_id}/test
测试LLM配置连接

#### PATCH /api/llm-config/{config_id}/activate
激活指定配置（其他配置将被停用）

---

### 4. 会话管理 (`/api/sessions`)

#### POST /api/sessions
创建新的用户会话

**请求体**:
```json
{
  "user_id": "user@example.com"
}
```

**响应示例**:
```json
{
  "session_id": "uuid-generated-session-id",
  "created_at": "2026-01-18T12:00:00Z"
}
```

#### GET /api/sessions/{session_id}
获取会话信息

---

### 5. 聊天 (`/api/chat`)

#### POST /api/chat
发送聊天消息并获取AI响应

**请求体**:
```json
{
  "session_id": "optional-session-id",
  "message": "我需要创建一个AWS EC2实例",
  "context": {}
}
```

**响应示例**:
```json
{
  "session_id": "uuid-session-id",
  "message": "收到您的需求。我需要了解一些信息...",
  "code_blocks": null,
  "metadata": {
    "workflow_state": "initialized",
    "message_count": 2
  }
}
```

---

### 6. Excel 处理 (`/api/excel`)

#### POST /api/excel/upload
上传并解析 Excel 文件

**请求**:
- Content-Type: `multipart/form-data`
- Body: Excel 文件 (.xlsx 或 .xls)
- 文件大小限制: 10MB

**响应示例**:
```json
{
  "success": true,
  "resource_count": 5,
  "resource_types": ["AWS_EC2", "AWS_VPC"],
  "resources": [...],
  "errors": [],
  "warnings": []
}
```

#### GET /api/excel/template
下载 Excel 模板

**查询参数**:
- `template_type`: aws | azure | full (默认: full)

---

### 7. 代码生成 (`/api/generate`)

#### POST /api/generate
根据资源定义生成 IaC 代码

**请求体**:
```json
{
  "resources": [
    {
      "resource_type": "EC2",
      "cloud_platform": "aws",
      "resource_name": "web-server",
      "properties": {...}
    }
  ],
  "metadata": {}
}
```

**响应示例**:
```json
{
  "success": true,
  "files": [
    {
      "filename": "main.tf",
      "content": "...",
      "language": "hcl"
    }
  ],
  "summary": "生成了5个资源的Terraform代码",
  "download_url": "/download/uuid.zip"
}
```

---

## 状态码

- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `413 Payload Too Large`: 文件大小超过限制
- `500 Internal Server Error`: 服务器内部错误
- `501 Not Implemented`: 功能尚未实现

## 注意事项

1. **核心功能状态**:
   - ✅ **LangGraph Agent 集成**: 已完整实现基于输入解析、合规性检查、代码生成的自动化流水线。
   - ✅ **Excel 文件解析**: 已实现多 Sheet 复杂资源提取与字段预处理。
   - ✅ **Terraform 代码生成**: 已实现覆盖 18 种资源的 Jinja2 模板化生成引擎，支持 HCL 语法校验。

2. **安全性**: 
   - API 密钥已支持存储（建议生产环境启用更高级别的加密）。
   - 已实现基本的 ID 清洗机制防止代码注入。

3. **数据库**: 
   - 首次启动时自动创建数据库表。
   - 默认使用 SQLite (位于 `iac_generator.db`)。
   - 已配置 Alembic 处理数据库迁移。


## 下一步开发

根据优先级，下一个任务是：
- **第2优先级**: 实现 Excel 解析服务
- **第3优先级**: 实现 LangGraph Agent 工作流
- **第4优先级**: 实现 Terraform 代码生成模板
- **第5优先级**: 前端界面开发
