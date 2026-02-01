"""
测试：检查是否创建了多个VM资源
"""

import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.agents.nodes import AgentNodes

db = SessionLocal()
nodes = AgentNodes(db)

# 模拟第1轮对话
state1 = {
    "session_id": "multi-vm-test",
    "messages": [{"role": "user", "content": "在中国东2区创建一台azure vm"}],
    "resources": [],
    "workflow_state": "initial",
    "information_complete": False,
}

result1 = nodes.input_parser(state1)

print(f"第1轮后资源数量: {len(result1.get('resources', []))}")
for i, res in enumerate(result1.get("resources", [])):
    print(f"  资源{i + 1}: {res.get('name')} / {res.get('resource_name')}")

# 模拟第2轮对话（提供完整信息包括Tags）
state2 = {
    "session_id": "multi-vm-test",
    "messages": result1.get("messages", [])
    + [
        {
            "role": "user",
            "content": """在中国东2区创建一台azure vm
ResourceGroup: my-rg
Location: China East 2
VMSize: Standard_B2s
AdminUsername: azureuser
OSType: Linux
ImagePublisher: Canonical
ImageOffer: UbuntuServer
ImageSKU: 18.04-LTS
AuthenticationType: Password
AdminPassword: YourSecurePassword123!
Tags: Project=MyProject, Owner=DevTeam""",
        }
    ],
    "resources": result1.get("resources", []),  # 保留第1轮的资源
    "workflow_state": "information_collection",
    "information_complete": False,
}

result2 = nodes.information_collector(state2)

print(f"\n第2轮后资源数量: {len(result2.get('resources', []))}")
for i, res in enumerate(result2.get("resources", [])):
    name = res.get("name") or res.get("resource_name")
    tags = res.get("properties", {}).get("Tags", {})
    print(f"  资源{i + 1}: {name}, Tags: {tags}")

if len(result2.get("resources", [])) > 1:
    print("\n[发现问题] 创建了多个VM资源！")
    print("这说明系统把第2轮输入当作新资源请求，而不是补充信息。")
else:
    print("\n[OK] 只有1个VM资源")

db.close()
