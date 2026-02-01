# IaC4 测试指南

## 📋 测试前检查清单

### ✅ 环境已就绪
- ✓ Python 3.13.8
- ✓ 所有依赖已安装
- ✓ .env 配置文件存在
- ✓ 数据库已创建

### ⚠️ 需要配置的内容

1. **检查 LLM API 密钥**
   ```bash
   cd backend
   cat .env | grep OPENAI_API_KEY
   ```
   
   如果显示 `your-api-key-here`，请更新为您的实际 API 密钥：
   ```bash
   # 编辑 .env 文件
   # OPENAI_API_KEY=sk-your-actual-key-here
   ```

## 🚀 测试方式

### 方式 1: 运行单元测试（最简单）

**不需要启动服务器**，直接运行测试脚本：

```bash
cd backend
python test_complete_flow.py
```

**预期输出：**
```
================================================================================
TERRAFORM CODE GENERATION TEST SUITE
================================================================================

Running Test Suite 1: Direct Generation

[TerraformGenerator] Starting code generation for 1 resources
[TerraformGenerator] Code generation complete. Total files: 5
[TerraformGenerator]   provider.tf: 189 bytes
[TerraformGenerator]   main.tf: 1123 bytes
...

✓ All tests passed!
```

**观察重点：**
- ✓ 每个 Agent 节点的详细日志（带 `===` 分隔符）
- ✓ 资源提取过程
- ✓ 生成的文件列表和大小
- ✓ 完整的 Terraform 代码内容

---

### 方式 2: API 测试（需要启动服务）

#### 步骤 1: 启动后端服务

在**第一个终端**运行：
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8666 --reload
```

**预期输出：**
```
INFO:     Uvicorn running on http://0.0.0.0:8666
INFO:     Application startup complete.
```

#### 步骤 2: 运行 API 测试

在**第二个终端**运行：
```bash
cd backend
python test_api.py
```

**预期输出：**
```
================================================================================
IaC4 API Test Suite
================================================================================

TEST 0: Health Check
Status: 200
✓ API is healthy

TEST 1: Create Session
✓ Session created: xxx-xxx-xxx

TEST 2: EC2 Creation Request
✓ Response received
✓ Generated 5 files:
  - provider.tf: 189 bytes
  - main.tf: 1123 bytes
  ...

✓ ALL TESTS PASSED
```

**观察重点：**
- ✓ 在第一个终端（后端服务）看到详细的 Agent 处理日志
- ✓ 每个节点的输入/输出
- ✓ 资源提取和验证过程
- ✓ Terraform 代码生成过程

---

### 方式 3: 前后端完整测试

#### 步骤 1: 启动后端
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8666 --reload
```

#### 步骤 2: 启动前端（新终端）
```bash
cd frontend
npm run dev
```

#### 步骤 3: 浏览器访问
打开浏览器访问：http://localhost:3000

**测试场景：**

1. **创建 AWS EC2 实例**
   ```
   我需要创建一个AWS EC2实例：
   - Region: us-east-1
   - InstanceType: t2.micro
   - AMI: ami-0c55b159cbfafe1f0
   - KeyPairName: my-key
   ```

2. **创建 AWS S3 存储桶**
   ```
   创建一个 S3 存储桶
   - Region: us-west-2
   - BucketName: my-unique-bucket-name-123
   - Versioning: Enabled
   ```

3. **测试合规性检查**（如果您配置了安全策略）
   ```
   创建一个 EC2 实例，开放 3389 端口到所有 IP
   ```
   应该会触发合规性检查失败（如果有阻止 3389 端口的策略）

---

## 📊 查看详细日志

### 后端服务器日志

当您通过 API 或前端发送请求时，后端终端会显示：

```
================================================================================
[Workflow] STARTING WORKFLOW
[Workflow] Session ID: xxx-xxx-xxx
[Workflow] User input length: 173 chars
================================================================================

================================================================================
[AGENT: InputParser] STARTED
[AGENT: InputParser] Session ID: xxx-xxx-xxx
[AGENT: InputParser] Extracted 1 resources
[AGENT: InputParser] Resources: [
  {
    "type": "aws_ec2",
    "name": "ec2_instance",
    "properties": {...}
  }
]
[AGENT: InputParser] FINISHED
================================================================================

[TerraformGenerator] Starting code generation...
[TerraformGenerator] Code generation complete. Total files: 5
```

**这些日志帮助您：**
- 🔍 了解每个 Agent 的处理状态
- 🐛 快速定位问题（如果生成失败）
- 📈 追踪整个工作流程

---

## 🧪 测试检查点

### ✅ 成功标志

1. **日志完整性**
   - [ ] 看到所有 Agent 节点的启动/结束日志
   - [ ] 每个节点都有 `===` 分隔符
   - [ ] 能看到资源提取的 JSON 数据

2. **代码生成**
   - [ ] 生成了 5 个文件（provider.tf, variables.tf, main.tf, outputs.tf, README.md）
   - [ ] main.tf 包含实际的资源定义（不是空的或TODO注释）
   - [ ] 文件大小合理（main.tf 通常 > 500 字节）

3. **错误处理**
   - [ ] 如果出错，能看到详细的错误信息和 traceback
   - [ ] 错误消息清晰说明问题所在

### ⚠️ 常见问题

**问题 1: LLM API 调用失败**
```
Error: OpenAI API key not configured
```
**解决：** 更新 `backend/.env` 中的 `OPENAI_API_KEY`

**问题 2: 数据库错误**
```
sqlalchemy.exc.OperationalError
```
**解决：** 删除 `backend/iac_generator.db` 重新启动

**问题 3: 端口被占用**
```
Address already in use
```
**解决：** 更改端口或关闭占用端口的程序

---

## 📝 测试建议

### 测试顺序（推荐）

1. **先运行单元测试** (`test_complete_flow.py`)
   - 验证核心代码生成功能
   - 不依赖 API 服务
   - 最快速的验证方式

2. **再运行 API 测试** (`test_api.py`)
   - 验证完整的 API 调用链路
   - 测试 Session 管理
   - 验证 HTTP 接口正常

3. **最后测试前端界面**
   - 验证用户界面交互
   - 测试代码预览和下载
   - 端到端用户体验

### 重点测试场景

- ✅ **简单 EC2** - 验证基本功能
- ✅ **带安全组的 EC2** - 验证复杂配置
- ✅ **S3 存储桶** - 验证不同资源类型
- ✅ **合规性检查** - 验证策略引擎（如果配置了）
- ✅ **错误场景** - 故意输入不完整信息，验证错误处理

---

## 🎯 验证改进效果

### 对比之前的系统

**改进前：**
- 日志稀少，难以追踪问题
- 代码生成失败时不知道原因
- 没有详细的中间状态信息

**改进后：**
- 每个环节都有详细日志
- 精确定位失败原因
- 可以看到完整的资源提取和转换过程

### 测试验证点

运行测试时，您应该看到：

1. ✅ **80个等号的分隔符** - 清晰划分不同阶段
2. ✅ **资源 JSON 完整输出** - 了解 LLM 提取的内容
3. ✅ **文件大小统计** - 验证代码确实生成了
4. ✅ **详细的错误信息** - 如果失败，知道为什么

---

## 🔧 调试提示

如果测试过程中遇到问题：

1. **查看完整日志** - 滚动到最开始，查找第一个 ERROR
2. **检查资源提取** - 看 InputParser 是否正确提取了资源
3. **验证模板匹配** - 看 TerraformGenerator 是否找到了对应模板
4. **检查 API 密钥** - 确认 LLM API 调用成功

---

## 📞 需要帮助？

如果测试过程中遇到问题，请：
1. 复制完整的错误日志
2. 说明您执行的测试步骤
3. 描述预期结果和实际结果

祝测试顺利！🎉
