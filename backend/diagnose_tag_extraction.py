"""
诊断工具：检查为什么标签提取不工作

请在重启后端后运行此脚本，它会告诉你问题所在。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("标签提取诊断工具")
print("=" * 80)

# 检查1：系统提示词是否包含Tags说明
print("\n[检查1] 系统提示词是否包含Tags说明")
print("-" * 80)

with open("app/agents/nodes.py", "r", encoding="utf-8") as f:
    content = f.read()

if "### TAGS (CRITICAL - APPLIES TO ALL RESOURCES)" in content:
    print("[OK] 系统提示词已包含Tags说明")
else:
    print("[ERROR] 系统提示词缺少Tags说明！")
    print("修复未应用，请检查文件是否保存。")
    sys.exit(1)

if '**CRITICAL**: ALWAYS include the "resources" field' in content:
    print("[OK] 系统提示词包含强制输出resources的指示")
else:
    print("[ERROR] 系统提示词缺少强制输出resources的指示！")
    print("修复未应用，请检查文件是否保存。")
    sys.exit(1)

# 检查2：Tags合并逻辑是否正确
print("\n[检查2] Tags合并逻辑是否正确")
print("-" * 80)

if 'if "Tags" in new_props:' in content:
    print("[OK] Tags合并逻辑已更新（只检查new_props）")
else:
    print("[WARNING] Tags合并逻辑可能仍使用旧版本")

# 检查3：测试实际的LLM提取能力
print("\n[检查3] 测试LLM是否能提取Tags")
print("-" * 80)

from app.core.database import SessionLocal
from app.agents.llm_client import LLMClient
import json

db = SessionLocal()
llm_client = LLMClient(db)

# 简化的测试提示词
test_prompt = """
You must extract Tags from user input and output JSON.

User conversation:
user: 创建Azure VM
assistant: ✗ Compliance check failed! Missing required tag(s): Project
user: 标签： Project=123

Output JSON format:
{
  "information_complete": false,
  "resources": [{
    "type": "azure_vm",
    "name": "vm-1",
    "properties": {
      "Tags": {"Project": "123"}
    }
  }]
}

Now extract the Tags from the last user message and output JSON:
"""

print("调用LLM测试标签提取...")

try:
    response = llm_client.chat(
        [
            {
                "role": "system",
                "content": "You extract Tags from user input into JSON format.",
            },
            {"role": "user", "content": test_prompt},
        ]
    )

    print(f"\nLLM响应 ({len(response)} 字符):")
    print(response[:500])
    print()

    # 尝试解析
    json_start = response.find("{")
    json_end = response.rfind("}") + 1

    if json_start >= 0 and json_end > json_start:
        json_str = response[json_start:json_end]
        result = json.loads(json_str)

        # 检查是否有resources
        if result.get("resources"):
            resources = result["resources"]
            if len(resources) > 0:
                tags = resources[0].get("properties", {}).get("Tags", {})

                if "Project" in tags or "project" in tags:
                    print("[OK] LLM成功提取了Project标签！")
                    print(f"提取的值: {tags.get('Project') or tags.get('project')}")
                else:
                    print("[ERROR] LLM返回了resources但没有Project标签")
                    print(f"实际Tags: {tags}")
                    print("\n可能原因：")
                    print("1. LLM模型能力不足（尝试换用gpt-4）")
                    print("2. 系统提示词太长，LLM没有遵循")
            else:
                print("[ERROR] resources数组为空")
        else:
            print("[ERROR] LLM响应中没有resources字段")
            print("这是主要问题！LLM没有遵循输出格式。")
            print("\n建议解决方案：")
            print("1. 检查LLM配置（是否使用足够强大的模型）")
            print("2. 简化系统提示词")
    else:
        print("[ERROR] LLM响应中找不到JSON")
        print("LLM可能没有按格式输出")

except Exception as e:
    print(f"[ERROR] LLM调用失败: {e}")
    import traceback

    traceback.print_exc()

# 检查4：后端服务是否真的重启了
print("\n[检查4] 如何确认后端已重启")
print("-" * 80)
print("如果前面的检查都通过，但真实对话还是失败，说明：")
print("1. 后端服务可能没有真正重启")
print("2. 或者缓存了旧的Python模块")
print()
print("解决方案：")
print("1. 完全停止后端进程（Ctrl+C 并确认进程已停止）")
print("2. 删除Python缓存：")
print("   rm -rf app/__pycache__")
print("   rm -rf app/*/__pycache__")
print("3. 重新启动：")
print("   uvicorn app.main:app --host 0.0.0.0 --port 8666 --reload")

print("\n" + "=" * 80)
print("诊断完成")
print("=" * 80)

db.close()
