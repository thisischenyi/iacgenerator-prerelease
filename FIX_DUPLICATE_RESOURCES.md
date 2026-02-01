# 修复资源重复问题

## 🐛 问题描述

**现象：**
用户在两次对话中创建 EC2（第一次信息不完整，第二次补全信息），最终生成了 2 个资源：
- 1 x EC2  
- 1 x aws_ec2

**根本原因：**
在 `InformationCollector` 节点的资源合并逻辑中，当 LLM 返回新资源时，会尝试与现有资源合并。但由于类型名称不一致（`EC2` vs `aws_ec2`），导致被识别为不同资源，从而追加到列表中。

## ✅ 修复方案

### 1. 改进资源合并逻辑 (`backend/app/agents/nodes.py`)

**位置：** `information_collector` 方法，第270-340行

**修复内容：**

#### 添加类型规范化函数
```python
def normalize_type(resource_type):
    """Normalize resource type to a common format."""
    if not resource_type:
        return ""
    rt = resource_type.lower()
    type_map = {
        "ec2": "aws_ec2",
        "aws_ec2": "aws_ec2",
        "s3": "aws_s3",
        "aws_s3": "aws_s3",
        "vpc": "aws_vpc",
        "aws_vpc": "aws_vpc",
        "vm": "azure_vm",
        "azure_vm": "azure_vm",
    }
    return type_map.get(rt, rt)
```

#### 使用规范化类型进行匹配
- 之前：直接用字符串匹配 `r.get("type")` 
- 现在：规范化后再匹配，`EC2` 和 `aws_ec2` 都映射到 `aws_ec2`

#### 智能合并策略
1. 如果规范化后的类型匹配，**合并属性**（而不是添加新资源）
2. 更新 `type` 和 `resource_type` 字段为规范化版本
3. 新属性覆盖旧属性

#### 详细日志
添加了详细的日志输出：
- 现有资源数量和类型
- 新资源数量和类型
- 每个资源的处理过程（合并 vs 添加）
- 最终资源数量

### 2. 修复 README 生成 (`backend/app/services/terraform_generator.py`)

**位置：** `_generate_readme` 方法，第344-378行

**修复内容：**

#### 规范化资源类型统计
```python
def normalize_type(rtype):
    """Normalize resource type for display."""
    # Same mapping as in nodes.py
    type_map = {
        "ec2": "aws_ec2",
        "aws_ec2": "aws_ec2",
        # ...
    }
    return type_map.get(rt, rt)

# Count by normalized type
normalized_types = {}
for r in resources:
    rtype = r.get("resource_type", "")
    normalized = normalize_type(rtype)
    normalized_types[normalized] = normalized_types.get(normalized, 0) + 1
```

现在即使有 `EC2` 和 `aws_ec2`，也会统计为同一种类型。

## 🧪 测试验证

创建了 `test_resource_merge.py` 测试脚本，模拟两次对话的场景：

**测试场景：**
1. 第一次：InputParser 提取资源，类型为 `aws_ec2`
2. 第二次：InformationCollector 接收用户补充信息，LLM 返回类型为 `EC2`
3. 验证：最终只有 1 个资源，属性已合并

**测试结果：**
```
[TEST] Initial state:
  Resources count: 1
  Resource types: ['aws_ec2']

[TEST] Simulated LLM response:
  New resources count: 1
  New resource types: ['EC2']

[TEST] Processing new resource:
  Type: EC2
  Normalized: aws_ec2
  Found in map: True
  -> Merging with existing resource at index 0

[TEST] Final state:
  Resources count: 1
  Resource types: ['aws_ec2']
  Resource properties: [{'Region': 'us-east-1', 'InstanceType': 't2.micro', 'AMI': 'ami-123'}]

[OK] TEST PASSED: No duplicate resources created
```

## 📊 修复效果对比

### 修复前
```
第一次：用户说"创建 EC2"
  -> resources: [{"type": "aws_ec2", "properties": {"Region": "us-east-1"}}]

第二次：用户补充信息
  -> LLM 返回: [{"type": "EC2", "properties": {...}}]
  -> 类型不匹配，添加新资源
  -> resources: [
       {"type": "aws_ec2", "properties": {"Region": "us-east-1"}},
       {"type": "EC2", "properties": {...}}
     ]

生成的 README:
  - 1 x EC2
  - 1 x aws_ec2  ❌ 重复！
```

### 修复后
```
第一次：用户说"创建 EC2"
  -> resources: [{"type": "aws_ec2", "properties": {"Region": "us-east-1"}}]

第二次：用户补充信息
  -> LLM 返回: [{"type": "EC2", "properties": {...}}]
  -> 规范化: EC2 -> aws_ec2
  -> 类型匹配，合并属性
  -> resources: [{"type": "aws_ec2", "properties": {...完整属性...}}]

生成的 README:
  - 1 x aws_ec2  ✅ 正确！
```

## 🔍 支持的资源类型映射

当前规范化映射：
- `ec2`, `EC2`, `aws_ec2` → `aws_ec2`
- `s3`, `S3`, `aws_s3` → `aws_s3`
- `vpc`, `VPC`, `aws_vpc` → `aws_vpc`
- `vm`, `VM`, `azure_vm` → `azure_vm`

**扩展性：** 可以轻松添加更多类型映射

## 📝 日志示例

修复后的详细日志输出：

```
[AGENT: InformationCollector] Existing resources: 1
[AGENT: InformationCollector] New resources from LLM: 1
[AGENT: InformationCollector] Existing resource types: ['aws_ec2']
[AGENT: InformationCollector] Processing new resource type: EC2 (normalized: aws_ec2)
[AGENT: InformationCollector]   Merging with existing resource at index 0
[AGENT: InformationCollector] Final resource count: 1
```

## 🚀 如何测试

**重启后端服务器：**
```bash
cd backend
# 按 Ctrl+C 停止服务器
uvicorn app.main:app --host 0.0.0.0 --port 8666 --reload
```

**测试步骤：**
1. 刷新网页
2. 创建新会话
3. 发送消息："创建一个 EC2 实例"
4. AI 会询问更多信息
5. 补充信息："Region: us-east-1, InstanceType: t2.micro, AMI: ami-123"
6. 查看生成的代码和 README

**预期结果：**
- ✅ 只生成 1 个 EC2 资源
- ✅ README 显示 "1 x aws_ec2"
- ✅ 所有属性都包含在一个资源定义中

## 📞 验证方式

1. **查看后端日志** - 应该看到合并日志，而不是添加日志
2. **检查生成的代码** - `main.tf` 只有一个 `resource "aws_instance"`
3. **检查 README.md** - 资源统计只显示 `1 x aws_ec2`

---

**修复完成！** 请重启后端服务器并测试。
