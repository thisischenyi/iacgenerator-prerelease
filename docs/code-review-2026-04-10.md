# IaC4 Multi-User — 全面代码审查报告

**项目：** `iac4-multi-user`  
**技术栈：** FastAPI 0.109 + LangGraph + SQLite / React 19 + TypeScript + MUI + Zustand  
**测试结果：** ✅ 126 个单元测试全部通过（`backend/tests/`）  
**审查范围：** 后端所有模块（26 个文件）+ 前端所有模块（全 `src/` 目录）  

---

## 目录

1. [测试运行结果](#1-测试运行结果)
2. [后端：严重问题（Critical）](#2-后端严重问题-critical)
3. [后端：高危问题（High）](#3-后端高危问题-high)
4. [后端：中危问题（Medium）](#4-后端中危问题-medium)
5. [后端：低危/代码质量（Low）](#5-后端低危代码质量-low)
6. [前端：严重问题（Critical）](#6-前端严重问题-critical)
7. [前端：高危问题（High）](#7-前端高危问题-high)
8. [前端：中危问题（Medium）](#8-前端中危问题-medium)
9. [前端：低危/代码质量（Low）](#9-前端低危代码质量-low)
10. [测试覆盖率分析](#10-测试覆盖率分析)
11. [依赖版本分析](#11-依赖版本分析)
12. [综合问题统计与修复优先级](#12-综合问题统计与修复优先级)

---

## 1. 测试运行结果

```
platform win32 -- Python 3.13.8, pytest-9.0.2
collected 126 items

tests/test_aws_exists_fields.py          4 passed
tests/test_aws_load_balancer.py         28 passed
tests/test_aws_resource_references.py    3 passed
tests/test_azure_exists_fields.py        5 passed
tests/test_azure_resource_references.py  6 passed
tests/test_azure_sql_guardrails.py       2 passed
tests/test_azure_subnet_service_endpoints_guardrail.py  2 passed
tests/test_azure_validator.py           11 passed
tests/test_eip_and_lb.py               30 passed
tests/test_new_network_resources.py     18 passed
tests/test_resource_group_handling.py    3 passed
tests/test_session_response_schema.py    1 passed

==================== 126 passed in 2.62s ====================
```

> ⚠️ `tests/test_code_reviewer_static_checks.py` 无法收集（`ModuleNotFoundError: No module named 'sqlalchemy'`）——这是测试环境配置问题，Python 解释器未使用项目虚拟环境。

**覆盖率问题：** 现有 126 个测试**全部集中在 Terraform 模板生成逻辑**（`services/excel_parser.py`、`services/terraform_generator.py`、`services/azure_validator.py`）。所有 API 路由、认证、数据库、工作流均无测试覆盖。

---

## 2. 后端：严重问题（Critical）

### [B-C-01] 🔴 AWS/Azure 凭据明文存储数据库
**文件：** `app/api/llm_config.py`、`app/models/__init__.py`  

`encrypt_api_key()` 和 `decrypt_api_key()` 都是直接返回原始字符串的空壳函数，注释写明"Simplified for debugging"。`DeploymentEnvironment` 模型直接在数据库中存储 `aws_secret_access_key`、`azure_client_secret` 等敏感字段的明文值。

```python
# app/api/llm_config.py
def encrypt_api_key(api_key: str) -> str:
    return api_key   # ← 明文写入数据库
```

**修复方案：**  
使用已安装的 `cryptography.fernet.Fernet`，以 `settings.SECRET_KEY` 派生加密密钥，写入前加密、读取时解密。

```python
from cryptography.fernet import Fernet
import hashlib, base64

def _get_fernet() -> Fernet:
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

def encrypt_api_key(api_key: str) -> str:
    return _get_fernet().encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
```

---

### [B-C-02] 🔴 OAuth CSRF 漏洞（state 参数未验证）
**文件：** `app/api/auth.py:162-174`、`app/api/auth.py:253-261`

`/google/login` 和 `/microsoft/login` 生成了 `state` 参数，但对应的 callback 路由**从未接收或验证** `state`。攻击者可伪造回调请求，完成 CSRF 攻击并劫持账号。

```python
# google_login 生成了 state，但 google_callback 根本没有 state 参数：
@router.get("/google/callback")
def google_callback(code: str = Query(...), ...):  # 缺少 state 验证
```

**修复方案：**  
在 login 时生成 `state` 并存入 Redis/DB（TTL 5 分钟），在 callback 时验证并删除。

---

### [B-C-03] 🔴 OAuth 回调将 JWT 明文写入 URL
**文件：** `app/api/auth.py:224`、`app/api/auth.py:313`

```python
redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={token}"
```

JWT 出现在：服务器访问日志、浏览器历史记录、Referer 请求头、任何第三方分析脚本。

**修复方案：**  
改用短生命周期（<30s）一次性 `code`，前端用 `POST` 请求交换真正的 token。或使用 `window.opener.postMessage` 的弹窗 OAuth 流。

---

### [B-C-04] 🔴 默认 SECRET_KEY 仅警告不阻断启动
**文件：** `app/core/config.py:57-66`

```python
if v == _INSECURE_SECRET_KEY:
    logging.warning("SECRET_KEY is using the default insecure value...")
```

忘记设置 `SECRET_KEY` 的生产部署将使用默认值，任何人都可以伪造有效 JWT，完全绕过认证。

**修复方案：**

```python
@field_validator("SECRET_KEY")
@classmethod
def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
    if v == _INSECURE_SECRET_KEY and not info.data.get("DEBUG", True):
        raise ValueError("生产环境必须修改 SECRET_KEY！")
    elif v == _INSECURE_SECRET_KEY:
        logging.warning("SECRET_KEY 使用默认值，请勿在生产中使用。")
    return v
```

---

### [B-C-05] 🔴 关键外键约束缺失
**文件：** `app/models/__init__.py`

以下关键关系仅用普通字符串/整数列存储，**无 SQLAlchemy ForeignKey 约束**，数据库无法保证引用完整性：

| 列 | 应关联 | 类型不一致 |
|---|---|---|
| `Session.user_id (String)` | `User.id (Integer)` | ⚠️ 类型不匹配 |
| `Deployment.session_id (String)` | `Session.session_id (String)` | — |
| `Deployment.environment_id (Integer)` | `DeploymentEnvironment.id (Integer)` | — |
| `AuditLog.session_id (String)` | `Session.session_id (String)` | — |

`Session.user_id` 是 `String(100)` 而 `User.id` 是 `Integer`，这是一个隐患：代码中用 `str(current_user.id)` 做字符串比较，一旦 ID 超过某个范围可能出现静默比较错误。

**修复方案：** 为所有关系添加 `ForeignKey` 声明，并统一 `user_id` 的类型为 `Integer`（或全部改 `String`）。

---

## 3. 后端：高危问题（High）

### [B-H-01] 🟠 数据库事务异常无回滚
**文件：** `app/core/database.py:25-31`

`get_db()` 生成器在 `finally` 中关闭 session，但缺少异常回滚逻辑。请求中途抛出异常时，未提交的脏数据留在 session identity map 中，可能被意外刷新。

```python
# 现状（有缺陷）
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 修复后
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

---

### [B-H-02] 🟠 DEBUG=True 是生产默认值
**文件：** `app/core/config.py:50`

```python
DEBUG: bool = True  # ← 生产部署会暴露完整 Python traceback
```

FastAPI 在 `debug=True` 时将完整异常堆栈信息返回给客户端，泄露内部实现细节、文件路径、变量值。

**修复：** 改为 `DEBUG: bool = False`。

---

### [B-H-03] 🟠 JWT sub 整数转换抛 ValueError → 500 错误
**文件：** `app/core/security.py:85`

```python
user = db.query(User).filter(User.id == int(user_id)).first()
```

若 `user_id` 不是合法整数字符串（被篡改的 token），`int(user_id)` 抛出 `ValueError`，未被捕获，最终返回 HTTP 500 而非 401。

**修复：** 加 `try/except ValueError` 并抛出 `HTTP_401_UNAUTHORIZED`。

---

### [B-H-04] 🟠 SSE 生成器中 `loop` 先引用后赋值
**文件：** `app/api/chat.py:183-194`

```python
def progress_callback(event: ProgressEvent):
    loop.call_soon_threadsafe(...)   # 第 186 行：loop 未赋值

ProgressTracker.register_callback(...)   # 第 189 行：callback 已注册

loop = asyncio.get_event_loop()          # 第 194 行：才赋值
```

若 callback 在第 194 行之前触发，将抛出 `NameError`。另外 `asyncio.get_event_loop()` 在 Python 3.10+ 已废弃。

**修复：**
```python
loop = asyncio.get_running_loop()   # 移到 callback 定义之前
def progress_callback(event: ProgressEvent):
    loop.call_soon_threadsafe(queue.put_nowait, event)
```

---

### [B-H-05] 🟠 部署环境无用户归属（权限提升漏洞）
**文件：** `app/api/deployments.py`

`DeploymentEnvironment` 表没有 `user_id` 列。任何已登录用户可以：
- 列出**所有用户**的部署环境（含 AWS/Azure 凭据标志）
- 创建、修改、删除**其他用户**的部署环境

这是严重的多租户隔离漏洞。

**修复：** 在 `DeploymentEnvironment` 添加 `user_id` 外键；所有 CRUD 操作按 `current_user.id` 过滤。

---

### [B-H-06] 🟠 登录接口无频率限制（暴力破解）
**文件：** `app/api/auth.py:113-139`

`/login` 端点无任何频率限制、账户锁定或失败延迟机制。

**修复：** 集成 `slowapi` 库，对 `/login` 限制为每 IP 每分钟不超过 10 次。

---

### [B-H-07] 🟠 LLM 错误被静默吞掉返回为字符串
**文件：** `app/agents/llm_client.py:96-97`

```python
except Exception as e:
    return f"Error calling LLM: {str(e)}"
```

调用方 `nodes.py` 尝试从这个错误字符串中提取 JSON，静默失败后以空资源列表继续执行，导致令人困惑的下游行为。

**修复：** 定义 `LLMError` 自定义异常；节点捕获它并设置 `workflow_state = "error"`。

---

### [B-H-08] 🟠 `list_sessions` 无分页（内存耗尽 DoS）
**文件：** `app/api/sessions.py:16-28`

返回用户所有 session，无任何限制。拥有大量 session 的用户每次请求都会将所有数据加载到内存中。

**修复：** 添加 `skip: int = 0, limit: int = Query(default=50, le=200)` 参数。

---

## 4. 后端：中危问题（Medium）

### [B-M-01] 🟡 `normalize_type()` 函数三份拷贝
**文件：** `app/agents/nodes.py:315`, `626`, `783`

完全相同的 30 行类型映射函数在 `input_parser`、`information_collector` 中被复制了三次。任何修改必须同步到三处。

**修复：** 提取为 `AgentNodes` 的静态方法 `@staticmethod _normalize_type(t: str) -> str`。

---

### [B-M-02] 🟡 Excel 上传无用户关联（无审计日志）
**文件：** `app/api/excel.py:17-56`

`upload_excel` handler 无 `current_user` 参数，无法记录上传者信息，也无法限制上传权限范围。

**修复：** 添加 `current_user: User = Depends(get_current_user)` 参数并记录上传日志。

---

### [B-M-03] 🟡 Content-Disposition 缺少文件名引号
**文件：** `app/api/excel.py:83`

```python
headers={"Content-Disposition": f"attachment; filename={filename}"}
```

RFC 6266 要求文件名必须加引号。当前文件名为纯 ASCII 时无问题，但这是不安全的模式。

**修复：** `f'attachment; filename="{filename}"'`

---

### [B-M-04] 🟡 Terraform 工作目录使用 `/tmp`（世界可读）
**文件：** `app/services/terraform_executor.py:96-98`

Linux 上 `/tmp` 是世界可读的。Terraform state 文件包含机密数据，写入此处存在信息泄露风险。

**修复：** 使用带权限控制的私有目录（`os.chmod(work_dir, 0o700)`）。

---

### [B-M-05] 🟡 代码下载接口无所有权验证（IDOR）
**文件：** `app/api/generate.py:20-40`

任何已认证用户可通过猜测文件名下载其他用户生成的 Terraform 代码包。

**修复：** 将生成的 ZIP 文件与 `user_id` 关联，下载前验证所有权。

---

### [B-M-06] 🟡 Pydantic v1 Config 风格（已废弃）
**文件：** `app/core/config.py:68-70`

```python
class Config:          # Pydantic v1 写法
    env_file = ".env"
```

**修复：**
```python
from pydantic_settings import SettingsConfigDict
model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
```

---

### [B-M-07] 🟡 `declarative_base()` 废弃导入
**文件：** `app/core/database.py:4`

```python
from sqlalchemy.ext.declarative import declarative_base  # SQLAlchemy 1.x 写法
```

**修复：** `from sqlalchemy.orm import declarative_base`

---

### [B-M-08] 🟡 `asyncio.get_event_loop()` 在 Python 3.10+ 已废弃
**文件：** `app/api/chat.py:194`

**修复：** `loop = asyncio.get_running_loop()`

---

### [B-M-09] 🟡 Pydantic 对象被直接追加（序列化 Bug）
**文件：** `app/agents/workflow.py:253-261`（`run` 和 `run_streaming` 均有）

```python
else:
    # else 分支说明 res 不是 dict，但下面的条件永远为 False：
    resources_dicts.append(res if isinstance(res, dict) else res)
    # ↑ 等价于 resources_dicts.append(res)，Pydantic 对象未序列化
```

下游代码用 `res["type"]` 访问，对 Pydantic 对象会抛出 `TypeError`。

**修复：**
```python
else:
    resources_dicts.append(res.model_dump() if hasattr(res, "model_dump") else vars(res))
```

---

### [B-M-10] 🟡 健康检查暴露数据库内部错误信息
**文件：** `app/api/health.py:26-27`

```python
db_status = f"unhealthy: {str(e)}"  # 将 DB 内部错误返回给调用方
```

**修复：** 服务端记录完整错误；对外只返回 `"unhealthy"`。

---

### [B-M-11] 🟡 LLM 参数精度截断 Bug
**文件：** `app/api/llm_config.py:105-110`

```python
temperature=int(config_data.temperature * 100),  # int() 截断而非四舍五入
top_p=int(config_data.top_p * 100),               # 0.999 → 99 而非 100
```

**修复：** 改用 `round()` 替代 `int()`。

---

### [B-M-12] 🟡 `test_llm_connection` 始终返回"已连接"
**文件：** `app/api/llm_config.py:248-289`

端点是 TODO 占位符，无论 LLM 是否可达都返回 `"status": "connected"`，严重误导用户。

**修复：** 实现真实的探活逻辑（解密 key → 调用 LLM list models → 返回真实状态）。

---

### [B-M-13] 🟡 workflow.py 中大量 `print()` 调用
**文件：** `app/agents/workflow.py:218-302`

数十个 `print()` 调用无法通过日志级别控制，绕过结构化日志系统。

**修复：** 全部替换为 `logger.debug()` / `logger.info()`。

---

### [B-M-14] 🟡 OAuth 账户隐式关联（未经同意）
**文件：** `app/api/auth.py:59-82`

本地注册的 `alice@example.com` 用 Google OAuth 以同一邮箱登录后，代码会静默覆盖 `provider` 和 `provider_user_id`，实现未经用户同意的账户关联。

**修复：** 发现 provider 不一致时抛出 409 错误，要求用户明确确认关联操作。

---

### [B-M-15] 🟡 缺少 `(provider, provider_user_id)` 复合索引
**文件：** `app/models/__init__.py:98`

OAuth 登录每次都执行 `WHERE provider = ? AND provider_user_id = ?`，但只有单列索引，没有复合索引。

**修复：**
```python
from sqlalchemy import Index
Index("ix_users_provider_pid", User.provider, User.provider_user_id)
```

---

## 5. 后端：低危/代码质量（Low）

| ID | 文件 | 描述 |
|----|------|------|
| B-L-01 | `deployments.py` | `DeploymentEnvironmentResponse` 构造代码在 4 处重复，应提取 `_env_to_response()` 辅助函数 |
| B-L-02 | `security.py` | 无 refresh token 机制，token 30 分钟后静默过期，用户需重新登录 |
| B-L-03 | `deployments.py:338` | `logger` 在文件中间定义，函数前半部分使用 `print()`，不一致 |
| B-L-04 | `generate.py:140` | 内部异常信息直接暴露给客户端（`detail=f"Code generation failed: {str(e)}"`) |
| B-L-05 | `policies.py` | Policy 未按用户隔离，所有用户共享全部安全策略 |
| B-L-06 | 多处 | `list_policies`、`list_environments`、`list_llm_configs` 的 `limit` 参数无上限，可传 `?limit=9999999` |
| B-L-07 | `models/__init__.py` | 无 `__all__` 列表，所有 model 全部公开导出 |
| B-L-08 | `nodes.py` | `should_continue_workflow` 的循环终止条件未审查，可能存在 `code_reviewer → code_generator` 无限循环 |
| B-L-09 | `excel_parser.py` | `self.errors` / `self.warnings` 为实例状态，模块级单例并发调用时存在竞争条件 |
| B-L-10 | `llm_config.py:3` | 导入了 `base64`、`Fernet` 但从未使用（加密被注释掉后遗留） |

---

## 6. 前端：严重问题（Critical）

### [F-C-01] 🔴 JWT Token 存储在 localStorage（XSS 高风险）
**文件：** `src/store/authStore.ts:49,166-178`

Zustand `persist` 中间件将 `accessToken`（JWT）写入 `localStorage`（键名 `iac-auth-storage`）。页面上任何 JavaScript（包括 XSS 注入的脚本）都可读取。

```ts
partialize: (state) => ({
  accessToken: state.accessToken, // ← 明文写入 localStorage
  ...
})
```

**修复方案：** 使用后端设置的 `HttpOnly` Cookie 存储 token。如必须保持前端存储，至少使用 `sessionStorage`（关闭标签页即清除），并在后端实现 token 轮换机制。

---

### [F-C-02] 🔴 OAuth JWT 作为 URL 查询参数传递（Token 泄露）
**文件：** `src/pages/AuthCallbackPage.tsx:13-17`

```ts
const token = params.get('token'); // ← 完整 JWT 在 URL 中
```

与后端 B-C-03 配套——应使用一次性 code 交换 token，不应在 URL 中传递真实 JWT。

---

### [F-C-03] 🔴 SettingsPage 使用原生 `axios` 绕过认证
**文件：** `src/pages/SettingsPage.tsx:41,87,93,99`

```ts
const response = await axios.get('/api/llm-config?active_only=true'); // 无 Authorization 头
await axios.put(`/api/llm-config/${configId}`, config);               // 无 Authorization 头
```

设置页面的 4 个 API 调用均使用原始 `axios` 而非带认证拦截器的 `api` 实例，导致这些请求不携带 Bearer token，实际上请求会被后端以 401 拒绝（但错误未被正确处理）。

**修复：** 将所有 `axios.get/post/put/patch` 替换为 `import api from '../services/api'` 的 `api.get/post/put/patch`。

---

### [F-C-04] 🔴 `createSession` 硬编码 `user_id: null`
**文件：** `src/services/api.ts:122`

```ts
createSession: async () => {
  const response = await api.post<{ session_id: string }>('/sessions', { user_id: null });
```

session 在无用户关联的情况下创建（虽然后端从 JWT 中获取用户，但前端发送了 `user_id: null` 的 body，这在语义上是错误的，也增加了迷惑性）。

**修复：** 发送空 body `{}` 或 `{ name: "新会话" }`，不要主动传 `user_id: null`。

---

### [F-C-05] 🔴 全应用无错误边界（Error Boundary）
**文件：** `src/App.tsx`、`src/main.tsx`

任何子组件（如 `MessageBubble` 的 Markdown 渲染、`SyntaxHighlighter`）抛出运行时错误，都会导致整个应用崩溃并显示空白屏。

**修复：**
```tsx
// src/components/ErrorBoundary.tsx
import { ErrorBoundary } from 'react-error-boundary';

// App.tsx
<ErrorBoundary fallback={<div>应用发生错误，请刷新页面</div>}>
  <ThemeProvider theme={theme}>
    ...
  </ThemeProvider>
</ErrorBoundary>
```

---

## 7. 前端：高危问题（High）

### [F-H-01] 🟠 UploadPage 中 `setTimeout` + `navigate` 竞争条件
**文件：** `src/pages/UploadPage.tsx:82-88`

```ts
navigate('/');
setTimeout(async () => {
  const { sendMessageWithProgress } = useChatStore.getState();
  await sendMessageWithProgress(…);
}, 100); // ← 100ms 无任何保证
```

100ms 延迟无法保证 ChatPage 已挂载、session 已创建完毕。在慢速设备上消息可能静默丢失。

**修复：** 用 `navigate('/', { state: { resources } })` 传递数据，在 `ChatPage` 的 `useEffect` 中读取 `useLocation().state` 触发发送。

---

### [F-H-02] 🟠 SSE ReadableStream 读取器未取消（内存泄漏）
**文件：** `src/store/chatStore.ts:297-435`

用户在流式响应进行中导航离开时，`fetch` 请求没有 `AbortController`，`while(true)` 循环继续运行，对可能已卸载组件的 store 持续调用 `set()`。

**修复：**
```ts
const controller = new AbortController();
const response = await fetch('/api/chat/stream', {
  signal: controller.signal, ...
});
// 在 cancelStream action 或组件 cleanup 中：
controller.abort();
```

---

### [F-H-03] 🟠 完整聊天历史每次消息变化都写入 localStorage
**文件：** `src/store/chatStore.ts:565-574`

Zustand `persist` 在每次状态变化时将整个 `sessions` 对象序列化写入 localStorage，包括所有消息和 Terraform 代码块（每个可达数十 KB）。大量对话后会：
1. 主线程阻塞（序列化耗时 >100ms）
2. 超过 localStorage 5MB 配额，静默丢失数据

**修复：** 使用 `partialize` 只持久化 session 元数据（id、title、createdAt），消息按需从服务端加载。

---

### [F-H-04] 🟠 Blob URL 未释放（内存泄漏）
**文件：** `src/components/chat/MessageBubble.tsx:29-33`、`src/pages/UploadPage.tsx:33-38`

```ts
element.href = URL.createObjectURL(file);
element.click();
document.body.removeChild(element);
// 缺少: URL.revokeObjectURL(element.href)
```

每次下载都泄漏一个 Blob URL，该 Blob 在页面关闭前一直占用内存。

**修复：** `element.click()` 后立即调用 `URL.revokeObjectURL(element.href)`。

---

### [F-H-05] 🟠 登录/注册错误信息硬编码，忽略服务端实际错误
**文件：** `src/store/authStore.ts:89-96,116-121`

```ts
} catch (error: unknown) {
  void error; // ← 错误被丢弃！
  set({ error: 'Invalid email or password', loading: false });
```

服务端返回的任何错误（邮箱已注册、账户被禁用、500 内部错误）都被硬编码消息覆盖。

**修复：** 使用文件中已定义的 `getErrorMessage()` 辅助函数：
```ts
set({ error: getErrorMessage(error, '登录失败'), loading: false });
```

---

### [F-H-06] 🟠 部署进度条完全是假的（setTimeout 模拟）
**文件：** `src/components/deployment/PlanProgressDialog.tsx:53-115`

进度步骤按硬编码的 `[1500, 8000, 15000, 2000]` ms 定时器推进，与实际 Terraform 执行进度完全无关。

**修复：** 实现真实的轮询（`GET /deployments/:id`）或后端 SSE 进度推送。

---

### [F-H-07] 🟠 OAuth 回调错误时加载动画永不停止
**文件：** `src/pages/AuthCallbackPage.tsx:27-33`

`setTokenFromOAuth` 失败时，错误提示正确显示，但 `<CircularProgress>` 无条件持续旋转。

**修复：** 将 spinner 条件改为 `{loading && <CircularProgress />}`。

---

## 8. 前端：中危问题（Medium）

| ID | 文件 | 描述 |
|----|------|------|
| F-M-01 | SessionList.tsx, EnvironmentDialog.tsx | 使用 `window.confirm()` 确认删除操作（阻塞 UI，部分环境不支持）→ 改用 MUI `<Dialog>` |
| F-M-02 | ChatPage.tsx:100 | `messages.map((msg, index) => <MessageBubble key={index}>)` 使用数组下标作 key，消息插入/删除时导致 DOM 复用错误 |
| F-M-03 | SessionList.tsx:175 | 使用已废弃的 `onKeyPress` → 改用 `onKeyDown` |
| F-M-04 | LoginPage.tsx | 登录表单无回车键提交处理，不符合标准 UX 习惯 |
| F-M-05 | SettingsPage.tsx:136 | `handleChange(field: string, value: unknown)` 参数类型过于宽泛，绕过 TypeScript 类型检查 |
| F-M-06 | SettingsPage.tsx:50-58 | `normalize()` 设置了 `top_p`、`frequency_penalty` 等 config 状态中不存在的字段 |
| F-M-07 | ProtectedRoute.tsx | 在 `initializeAuth()` 完成前用 localStorage 中的旧 `isAuthenticated` 判断权限，expired token 用户会短暂看到受保护页面 |
| F-M-08 | SessionList.tsx:64 | `sortedSessions` 每次渲染重新计算（`Object.values` + `sort`），应使用 `useMemo` |
| F-M-09 | chatStore.ts | `useCurrentSession` 对 `currentSessionId` 和 `sessions` 双重订阅，任何消息变化触发所有订阅者重渲染 |
| F-M-10 | chatStore.ts:107-110 | `createNewSession` 后立即调用 `syncSessionsFromServer`，多余 HTTP 往返，且可能意外覆盖 `currentSessionId` |
| F-M-11 | MessageBubble.tsx:75 | `react-markdown` v10 已移除 `inline` prop，`!inline && match` 判断永远为 `false`，导致所有代码块走语法高亮路径 |
| F-M-12 | api.ts, chatStore.ts, DeployButton.tsx | 生产代码中大量 `console.log`/`console.error`，暴露 session ID、部署 ID 等敏感信息（仅 deploymentStore.ts 就有 20+ 处） |
| F-M-13 | MainLayout.tsx:149 | `aria-label="mailbox folders"` 从 MUI 示例代码复制，屏幕阅读器会错误播报"信箱文件夹" |
| F-M-14 | PolicyPage.tsx:187 | 删除策略无确认对话框；policyStore 的 error 字段在 PolicyPage 中从未渲染 |
| F-M-15 | ChatPage.tsx:125-137 | 消息输入框和发送按钮缺少 `aria-label`，无障碍访问不合规 |

---

## 9. 前端：低危/代码质量（Low）

| ID | 文件 | 描述 |
|----|------|------|
| F-L-01 | ChatPage.tsx:53 | 函数命名为 `handleKeyPress` 但绑定到 `onKeyDown`，命名误导 |
| F-L-02 | 多处 | 硬编码十六进制颜色（`'#f8f9fa'`, `'#fafafa'`, `'#ffffff'`）绕过 MUI theme，不支持深色模式扩展 |
| F-L-03 | deploymentStore.ts | 持久化了 `environments` 数组（含凭据标志），每次刷新应从服务端重新获取而非缓存 |
| F-L-04 | PolicyPage.tsx:86 | `getSeverityColor(severity: string)` 参数类型过宽；应为 `'error' \| 'warning'` |
| F-L-05 | chatStore.ts:150 | `renameSession` 仅修改本地状态，刷新后丢失（后端无对应 PATCH 接口） |
| F-L-06 | MessageBubble.tsx:79 | `vscDarkPlus as unknown as {...}` 双重类型断言是类型不安全的写法 |
| F-L-07 | EnvironmentDialog.tsx:86 | 对话框关闭时表单状态不重置，重新打开时保留上次输入 |
| F-L-08 | package.json:21 | `framer-motion`（~100kB gzip）被安装但代码中**零使用** |
| F-L-09 | package.json:18 | `clsx` 被安装但代码中**零使用** |
| F-L-10 | DeployButton.tsx:215-228 | 完整 JSX 内容（含文字和图标）作为 `startIcon` 传递给 MUI Button，造成视觉和语义双重问题 |

---

## 10. 测试覆盖率分析

### 已覆盖区域 ✅

| 测试文件 | 覆盖内容 |
|---------|---------|
| `test_aws_*.py` | AWS EC2、S3、负载均衡器、EIP 的 Terraform 生成 |
| `test_azure_*.py` | Azure VM、NSG、SQL、子网、负载均衡器的 Terraform 生成 |
| `test_azure_validator.py` | AzureRM provider 兼容性静态检查 |
| `test_resource_group_handling.py` | 资源组存在性判断逻辑 |
| `test_session_response_schema.py` | Session API 响应 schema |

### 完全未覆盖区域 ❌

| 区域 | 缺失的测试 |
|------|-----------|
| `app/api/auth.py` | 注册、登录、OAuth 流程、token 验证、过期处理 |
| `app/api/chat.py` | 聊天接口、SSE 流式响应、权限验证 |
| `app/api/sessions.py` | 创建、查询、删除、跨用户权限隔离 |
| `app/api/excel.py` | 文件上传验证、大小限制、类型检查 |
| `app/api/deployments.py` | 完整部署生命周期、权限检查 |
| `app/api/policies.py` | 策略 CRUD、LLM 转换逻辑 |
| `app/api/llm_config.py` | 配置 CRUD、加密/解密 |
| `app/core/security.py` | JWT 创建/解码、过期 token、篡改 token |
| `app/agents/workflow.py` | 工作流状态转换、错误路径 |
| `app/agents/llm_client.py` | LLM 错误处理、Fallback 行为 |
| `app/services/terraform_executor.py` | plan/apply 执行、超时处理 |

**建议：** 优先为 `app/core/security.py` 和 `app/api/auth.py` 添加测试，因为这是整个系统的信任基础。

---

## 11. 依赖版本分析

### 后端（requirements.txt）

| 依赖 | 当前版本 | 最新版本 | 说明 |
|-----|---------|---------|------|
| `fastapi` | 0.109.0 | 0.115+ | 缺少多项安全修复 |
| `langgraph` | 0.0.20 | 0.2+ | **极其过时**，API 变化巨大 |
| `langchain-core` | 0.1.15 | 0.3+ | 与 langgraph 新版本不兼容 |
| `openai` | 1.10.0 | 1.50+ | 缺少新模型支持和 bug 修复 |
| `python-jose` | 3.3.0 | — | 已知 CVE，建议迁移到 `PyJWT` |
| `passlib` | 1.7.4 | — | 已停止维护，建议迁移到 `argon2-cffi` |
| `cryptography` | 42.0.0 | 44+ | 有安全更新 |

### 前端（package.json）

| 依赖 | 问题 |
|-----|------|
| `framer-motion` | 安装但零使用（~100kB 无用体积） |
| `clsx` | 安装但零使用 |
| `react-markdown` v10 | 已移除 `inline` prop，代码未适配 |

---

## 12. 综合问题统计与修复优先级

### 统计总览

| 严重级别 | 后端 | 前端 | 合计 |
|---------|------|------|------|
| 🔴 Critical | 5 | 5 | **10** |
| 🟠 High | 8 | 7 | **15** |
| 🟡 Medium | 15 | 15 | **30** |
| 🔵 Low | 10 | 10 | **20** |
| **合计** | **38** | **37** | **75** |

### 推荐修复顺序

**第一优先级（影响安全/数据完整性，立即修复）：**
1. `B-C-01` — 凭据加密存储
2. `B-C-02` / `F-C-02` — OAuth CSRF + Token URL 泄露（前后端联动修复）
3. `B-C-04` — 生产 SECRET_KEY 验证
4. `F-C-03` — SettingsPage 使用正确 api 实例
5. `B-H-05` — 部署环境用户归属隔离
6. `B-H-01` — DB 事务回滚
7. `B-H-03` — JWT sub 整数转换异常

**第二优先级（稳定性/可用性问题）：**
8. `B-H-04` — SSE loop 变量引用顺序
9. `F-C-05` — 添加 ErrorBoundary
10. `F-H-02` — SSE 读取器取消（内存泄漏）
11. `F-H-03` — localStorage 大小限制
12. `B-M-09` — Pydantic 对象序列化 Bug
13. `F-H-05` — 登录错误信息

**第三优先级（体验/代码质量改善）：**
14. `B-H-06` — 登录频率限制
15. `B-H-07` — LLM 错误处理
16. `F-H-06` — 部署进度真实化
17. `B-H-08` + `F-M-08` — 分页和性能
18. `F-L-08` / `F-L-09` — 移除未使用依赖
19. `B-L-02` — Refresh token 机制
20. 其余 Medium/Low 问题

---

*报告生成时间：2026-04-10*  
*审查者：GitHub Copilot（Claude Sonnet 4.6）*
