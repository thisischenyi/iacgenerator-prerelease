"""
Test the complete flow with actual LLM to see what's happening.
This will show us if the LLM is extracting Tags correctly.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.agents.nodes import AgentNodes

print("=" * 80)
print("COMPLETE FLOW TEST: Natural Language Tag Addition")
print("=" * 80)

db = SessionLocal()
nodes = AgentNodes(db)

# Step 1: Initial state - VM created without Tags
print("\nSTEP 1: Initial VM Creation (no Project tag)")
print("-" * 80)

initial_state = {
    "session_id": "flow-test-001",
    "resources": [
        {
            "type": "azure_vm",
            "resource_type": "azure_vm",
            "name": "vm-1",
            "resource_name": "vm-1",
            "cloud_platform": "azure",
            "properties": {
                "ResourceName": "vm-1",
                "ResourceGroup": "my-rg",
                "Location": "China East 2",
                "VMSize": "Standard_B2s",
                "AdminUsername": "azureuser",
                "OSType": "Linux",
                "ImagePublisher": "Canonical",
                "ImageOffer": "UbuntuServer",
                "ImageSKU": "18.04-LTS",
                "AuthenticationType": "Password",
                "AdminPassword": "SecurePass123!",
                # Note: NO Tags field initially
            },
        }
    ],
    "messages": [
        {"role": "user", "content": "创建Azure VM"},
        {"role": "assistant", "content": "请提供详细信息..."},
        {
            "role": "user",
            "content": "ResourceGroup: my-rg, Location: China East 2, VMSize: Standard_B2s, ...",
        },
    ],
    "workflow_state": "information_collection",
    "information_complete": False,
}

print(
    f"Initial resource has Tags: {'Tags' in initial_state['resources'][0]['properties']}"
)

# Step 2: User adds tag
print('\nSTEP 2: User says: Tags: {{"Project": "MyProject", "Environment": "Test"}}')
print("-" * 80)

initial_state["messages"].append(
    {"role": "user", "content": 'Tags: {"Project": "MyProject", "Environment": "Test"}'}
)

print("Calling information_collector...")
result_state = nodes.information_collector(initial_state)

print("\nCHECKING RESULTS:")
print("-" * 80)

if result_state.get("resources"):
    resource = result_state["resources"][0]
    tags = resource.get("properties", {}).get("Tags", {})

    print(f"Resource has Tags field: {'Tags' in resource.get('properties', {})}")
    print(f"Tags value: {tags}")

    if "Project" in tags or "project" in tags:
        print("[OK] Project tag found!")
    else:
        print("[PROBLEM] Project tag NOT found!")

# Step 3: Compliance check
print("\nSTEP 3: Compliance Check")
print("-" * 80)

compliance_result = nodes.compliance_checker(
    {
        "session_id": "test",
        "resources": result_state.get("resources", []),
        "messages": [],
        "workflow_state": "checking_compliance",
    }
)

print(f"Result: {'PASSED' if compliance_result['compliance_passed'] else 'FAILED'}")
if not compliance_result["compliance_passed"]:
    for v in compliance_result.get("compliance_violations", []):
        print(f"  {v['resource']}: {v['issue']}")

db.close()
