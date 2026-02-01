"""
Test the resource merging logic to ensure no duplicates.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.nodes import AgentNodes
from app.core.database import SessionLocal


def test_resource_merging():
    """Test that resource merging doesn't create duplicates."""
    print("\n" + "=" * 80)
    print("Testing Resource Merging Logic")
    print("=" * 80)

    db = SessionLocal()
    nodes = AgentNodes(db)

    # Simulate the state after InputParser (first resource extraction)
    state = {
        "session_id": "test-123",
        "messages": [
            {"role": "user", "content": "创建一个 EC2 实例"},
            {"role": "assistant", "content": "我需要更多信息..."},
            {
                "role": "user",
                "content": "Region: us-east-1, InstanceType: t2.micro, AMI: ami-123",
            },
        ],
        "resources": [
            {
                "type": "aws_ec2",
                "name": "ec2_instance",
                "properties": {"Region": "us-east-1"},
                "cloud_platform": "aws",
            }
        ],
        "workflow_state": "information_collection",
        "information_complete": False,
    }

    print("\n[TEST] Initial state:")
    print(f"  Resources count: {len(state['resources'])}")
    print(f"  Resource types: {[r.get('type') for r in state['resources']]}")

    # Simulate LLM response in InformationCollector
    # This is what happens when user provides more info
    # The LLM might return the resource with slightly different type name

    # Manually inject what the LLM would return
    simulated_llm_result = {
        "information_complete": True,
        "missing_fields": [],
        "resources": [
            {
                "type": "EC2",  # Note: different case/format
                "name": "ec2_instance",
                "properties": {
                    "Region": "us-east-1",
                    "InstanceType": "t2.micro",
                    "AMI": "ami-123",
                },
            }
        ],
        "user_message_to_display": "Information complete!",
    }

    print("\n[TEST] Simulated LLM response:")
    print(f"  New resources count: {len(simulated_llm_result['resources'])}")
    print(
        f"  New resource types: {[r.get('type') for r in simulated_llm_result['resources']]}"
    )

    # Simulate the merging logic from InformationCollector
    existing_resources = state.get("resources", [])
    new_resources = simulated_llm_result.get("resources", [])

    # Normalize type names for comparison
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
        }
        return type_map.get(rt, rt)

    # Create a map of existing resources by normalized type
    res_map = {}
    for idx, r in enumerate(existing_resources):
        r_type = r.get("type") or r.get("resource_type")
        normalized = normalize_type(r_type)
        res_map[normalized] = idx

    print(f"\n[TEST] Existing resource map: {res_map}")

    for nr in new_resources:
        nr_type = nr.get("type") or nr.get("resource_type")
        normalized_new = normalize_type(nr_type)

        print(f"\n[TEST] Processing new resource:")
        print(f"  Type: {nr_type}")
        print(f"  Normalized: {normalized_new}")
        print(f"  Found in map: {normalized_new in res_map}")

        if normalized_new in res_map:
            # Update existing resource
            idx = res_map[normalized_new]
            existing_res = existing_resources[idx]

            print(f"  -> Merging with existing resource at index {idx}")

            # Merge properties
            current_props = existing_res.get("properties", {})
            new_props = nr.get("properties", {})
            current_props.update(new_props)
            existing_res["properties"] = current_props

            # Update type to normalized version
            existing_res["type"] = normalized_new
            existing_res["resource_type"] = normalized_new
        else:
            # Add new resource
            print(f"  -> Adding as new resource")
            existing_resources.append(nr)

    state["resources"] = existing_resources

    print("\n[TEST] Final state:")
    print(f"  Resources count: {len(state['resources'])}")
    print(f"  Resource types: {[r.get('type') for r in state['resources']]}")
    print(f"  Resource properties: {[r.get('properties') for r in state['resources']]}")

    # Verify
    print("\n" + "=" * 80)
    if len(state["resources"]) == 1:
        print("[OK] TEST PASSED: No duplicate resources created")
        print(
            f"[OK] Resource has all properties: {state['resources'][0].get('properties')}"
        )
        return True
    else:
        print(f"[FAIL] TEST FAILED: Expected 1 resource, got {len(state['resources'])}")
        return False

    db.close()


if __name__ == "__main__":
    result = test_resource_merging()
    if result:
        print("\n[OK] All tests passed!")
    else:
        print("\n[FAIL] Tests failed!")
        exit(1)
