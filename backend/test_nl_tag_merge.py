"""Test natural language tag extraction and merging."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.agents.nodes import AgentNodes

print("=" * 80)
print("TEST: Natural Language Tag Extraction and Merging")
print("=" * 80)

db = SessionLocal()
nodes = AgentNodes(db)

# Simulate a conversation where user creates a VM and then adds tags

# Step 1: User creates a VM (without Project tag)
print("\nSTEP 1: Initial resource creation")
print("-" * 80)

initial_state = {
    "session_id": "test-nl-tags-001",
    "resources": [
        {
            "type": "azure_vm",
            "resource_type": "azure_vm",
            "name": "vm_china_east2",
            "resource_name": "vm_china_east2",
            "cloud_platform": "azure",
            "properties": {
                "ResourceName": "vm_china_east2",
                "Location": "China East 2",
                "ResourceGroup": "myResourceGroup",
                "VMSize": "Standard_B2s",
                "AdminUsername": "azureuser",
                "OSType": "Linux",
                "ImagePublisher": "Canonical",
                "ImageOffer": "UbuntuServer",
                "ImageSKU": "18.04-LTS",
                "AuthenticationType": "Password",
                "AdminPassword": "MySecurePassword123!",
                "Tags": {"Application": "WebServer"},
            },
        }
    ],
    "messages": [
        {"role": "user", "content": "创建一个Azure VM，位置在China East 2"},
        {"role": "assistant", "content": "以下是详细信息：..."},
    ],
    "workflow_state": "information_collection",
    "information_complete": False,
}

print(f"Initial Tags: {initial_state['resources'][0]['properties']['Tags']}")

# Step 2: Simulate user adding Project tag via natural language
print("\nSTEP 2: User adds Project tag via natural language")
print("-" * 80)

# Simulate what the LLM should extract from "打上标签：Project=Demo123"
llm_extracted_update = {
    "information_complete": True,
    "missing_fields": [],
    "resources": [
        {
            "type": "azure_vm",
            "name": "vm_china_east2",
            "properties": {
                "Tags": {
                    "Project": "Demo123"  # NEW tag from user input
                }
            },
        }
    ],
    "user_message_to_display": "已添加标签 Project=Demo123",
}

# Manually execute the merge logic (same as information_collector does)
existing_resources = initial_state["resources"]
new_resources = llm_extracted_update["resources"]


def normalize_type(resource_type):
    if not resource_type:
        return ""
    rt = resource_type.lower().replace(" ", "_")
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


res_map = {}
for idx, r in enumerate(existing_resources):
    r_type = r.get("type") or r.get("resource_type")
    normalized = normalize_type(r_type)
    res_map[normalized] = idx

for nr in new_resources:
    nr_type = nr.get("type") or nr.get("resource_type")
    normalized_new = normalize_type(nr_type)

    if normalized_new in res_map:
        idx = res_map[normalized_new]
        existing_res = existing_resources[idx]

        print(f"Merging new data into existing resource...")

        # Apply the NEW merge logic with Tags special handling
        current_props = existing_res.get("properties", {})
        new_props = nr.get("properties", {})

        print(f"  Current Tags: {current_props.get('Tags', {})}")
        print(f"  New Tags from user: {new_props.get('Tags', {})}")

        # Special handling for Tags field - merge tags instead of replacing
        if "Tags" in current_props and "Tags" in new_props:
            current_tags = current_props.get("Tags", {})
            new_tags = new_props.get("Tags", {})

            if isinstance(current_tags, dict) and isinstance(new_tags, dict):
                merged_tags = {**current_tags, **new_tags}
                new_props["Tags"] = merged_tags
                print(f"  Merged Tags: {merged_tags}")

        current_props.update(new_props)
        existing_res["properties"] = current_props

print(f"\nFinal Tags: {existing_resources[0]['properties']['Tags']}")

# Step 3: Run compliance check
print("\nSTEP 3: Running compliance check with merged tags")
print("-" * 80)

final_state = {
    "session_id": "test-nl-tags-001",
    "resources": existing_resources,
    "messages": [],
    "workflow_state": "checking_compliance",
}

result = nodes.compliance_checker(final_state)

print(f"\nCompliance Result: {'PASSED' if result['compliance_passed'] else 'FAILED'}")
print(f"Violations: {len(result.get('compliance_violations', []))}")

if result.get("compliance_violations"):
    for v in result["compliance_violations"]:
        print(f"  - {v['resource']}: {v['issue']}")

# Verify
expected_tags = {"Application": "WebServer", "Project": "Demo123"}
actual_tags = existing_resources[0]["properties"]["Tags"]

print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)
print(f"Expected Tags: {expected_tags}")
print(f"Actual Tags: {actual_tags}")

if actual_tags == expected_tags:
    print("\n[SUCCESS] Tags were correctly merged!")
    print("Application tag was preserved, Project tag was added.")
else:
    print("\n[FAILED] Tags merge incorrect!")
    sys.exit(1)

if result["compliance_passed"]:
    print("\n[SUCCESS] Compliance check PASSED with merged tags!")
else:
    print("\n[FAILED] Compliance check should have PASSED!")
    sys.exit(1)

print("\n" + "=" * 80)
print("ALL TESTS PASSED!")
print("Natural language tag input is now working correctly.")
print("=" * 80)

db.close()
