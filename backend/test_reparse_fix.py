"""
测试修复：第2轮对话应该重新解析用户输入
"""

import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.agents.nodes import AgentNodes

db = SessionLocal()
nodes = AgentNodes(db)

print("=" * 80)
print("测试：第2轮对话是否会重新解析用户输入")
print("=" * 80)

# 模拟第1轮：创建VM（无Project标签）
print("\n第1轮：创建VM（Tags只有Owner）")
state1 = {
    "session_id": "test-reparse",
    "messages": [
        {"role": "user", "content": "在中国东2区创建一台azure vm...Tags: Owner=DevTeam"}
    ],
    "resources": [],
    "workflow_state": "initialized",
}

result1 = nodes.input_parser(state1)
print(f"第1轮后 - Resources: {len(result1.get('resources', []))}")
if result1.get("resources"):
    tags1 = result1["resources"][0].get("properties", {}).get("Tags", {})
    print(f"第1轮后 - Tags: {tags1}")

# 模拟第2轮：提供完整信息（包含Project标签）
print("\n第2轮：提供完整信息（Tags包含Project和Owner）")
state2 = {
    "session_id": "test-reparse",
    "messages": result1.get("messages", [])
    + [
        {"role": "assistant", "content": "Missing Project tag..."},
        {
            "role": "user",
            "content": "在中国东2区创建一台azure vm...Tags: Project=MyProject, Owner=DevTeam",
        },
    ],
    "resources": result1.get("resources", []),
    "workflow_state": "compliance_failed",  # 第1轮失败后的状态
    "information_complete": False,
}

print(f"第2轮前 - Messages: {len(state2['messages'])}")
print(f"第2轮前 - Resources in state: {len(state2.get('resources', []))}")

result2 = nodes.input_parser(state2)

print(f"\n第2轮后 - 是否跳过解析？检查日志...")
print(f"第2轮后 - Resources: {len(result2.get('resources', []))}")

if result2.get("resources"):
    tags2 = result2["resources"][0].get("properties", {}).get("Tags", {})
    print(f"第2轮后 - Tags: {tags2}")

    if "Project" in tags2 or "project" in tags2:
        print("\n[SUCCESS] 第2轮重新解析了用户输入，提取到了Project标签！")
    else:
        print("\n[FAILED] 第2轮没有提取到Project标签")
        print("说明InputParser仍然跳过了解析")
else:
    print("\n[ERROR] 第2轮后没有resources")

db.close()
