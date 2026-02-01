"""Test script to verify tag compliance checking."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine, Base
from app.models import SecurityPolicy
from app.schemas import CloudPlatform
from app.agents.nodes import AgentNodes

# Create tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Create test policy for required tags
try:
    # Delete ALL existing tag policies to avoid conflicts
    existing_tag_policies = (
        db.query(SecurityPolicy)
        .filter(SecurityPolicy.executable_rule.contains("required_tags"))
        .all()
    )
    for p in existing_tag_policies:
        db.delete(p)
    db.commit()

    policy = SecurityPolicy(
        name="必须打上project标签",
        description="测试标签合规",
        natural_language_rule="创建的资源必须包含project标签",
        executable_rule={"required_tags": ["project"]},
        cloud_platform=CloudPlatform.ALL,
        severity="error",
        enabled=True,
    )
    db.add(policy)
    db.commit()
    print("[OK] Created tag compliance policy")
except Exception as e:
    print(f"[ERROR] Error creating policy: {e}")
    db.rollback()


# Test Case 1: Resource WITHOUT project tag (should FAIL)
print("\n" + "=" * 80)
print("TEST CASE 1: Resource WITHOUT project tag (should FAIL)")
print("=" * 80)

state1 = {
    "session_id": "test-session-1",
    "resources": [
        {
            "resource_type": "aws_instance",
            "cloud_platform": "aws",
            "resource_name": "test-instance-1",
            "properties": {
                "InstanceType": "t2.micro",
                "Tags": {
                    "Name": "test-instance",
                    "Environment": "dev",
                    # Missing "project" tag!
                },
            },
        }
    ],
    "messages": [],
    "workflow_state": "initial",
}

nodes = AgentNodes(db)
result1 = nodes.compliance_checker(state1)

print(f"\nResult: {'PASSED' if result1['compliance_passed'] else 'FAILED'}")
print(f"Violations: {len(result1.get('compliance_violations', []))}")
if result1.get("compliance_violations"):
    for v in result1["compliance_violations"]:
        print(f"  - {v['resource']}: {v['issue']}")

assert not result1["compliance_passed"], "Test 1 should have FAILED but PASSED!"
assert len(result1["compliance_violations"]) == 1, (
    f"Expected 1 violation, got {len(result1['compliance_violations'])}"
)
print("[OK] Test 1 PASSED: Correctly detected missing tag")


# Test Case 2: Resource WITH project tag (should PASS)
print("\n" + "=" * 80)
print("TEST CASE 2: Resource WITH project tag (should PASS)")
print("=" * 80)

state2 = {
    "session_id": "test-session-2",
    "resources": [
        {
            "resource_type": "aws_instance",
            "cloud_platform": "aws",
            "resource_name": "test-instance-2",
            "properties": {
                "InstanceType": "t2.micro",
                "Tags": {
                    "Name": "test-instance",
                    "Environment": "dev",
                    "project": "iac4-test",  # Has project tag
                },
            },
        }
    ],
    "messages": [],
    "workflow_state": "initial",
}

result2 = nodes.compliance_checker(state2)

print(f"\nResult: {'PASSED' if result2['compliance_passed'] else 'FAILED'}")
print(f"Violations: {len(result2.get('compliance_violations', []))}")

assert result2["compliance_passed"], "Test 2 should have PASSED but FAILED!"
assert len(result2["compliance_violations"]) == 0, (
    f"Expected 0 violations, got {len(result2['compliance_violations'])}"
)
print("[OK] Test 2 PASSED: Correctly validated required tag")


# Test Case 3: Case-insensitive check (Project vs project) (should PASS)
print("\n" + "=" * 80)
print("TEST CASE 3: Case-insensitive check - 'Project' vs 'project' (should PASS)")
print("=" * 80)

state3 = {
    "session_id": "test-session-3",
    "resources": [
        {
            "resource_type": "aws_instance",
            "cloud_platform": "aws",
            "resource_name": "test-instance-3",
            "properties": {
                "InstanceType": "t2.micro",
                "Tags": {
                    "Name": "test-instance",
                    "Project": "iac4-test",  # Capital 'P' Project (case-insensitive match)
                },
            },
        }
    ],
    "messages": [],
    "workflow_state": "initial",
}

result3 = nodes.compliance_checker(state3)

print(f"\nResult: {'PASSED' if result3['compliance_passed'] else 'FAILED'}")
print(f"Violations: {len(result3.get('compliance_violations', []))}")

assert result3["compliance_passed"], "Test 3 should have PASSED but FAILED!"
assert len(result3["compliance_violations"]) == 0, (
    f"Expected 0 violations, got {len(result3['compliance_violations'])}"
)
print("[OK] Test 3 PASSED: Case-insensitive tag matching works")


# Test Case 4: Multiple resources, mixed compliance
print("\n" + "=" * 80)
print("TEST CASE 4: Multiple resources - mixed compliance (should FAIL)")
print("=" * 80)

state4 = {
    "session_id": "test-session-4",
    "resources": [
        {
            "resource_type": "aws_instance",
            "cloud_platform": "aws",
            "resource_name": "compliant-instance",
            "properties": {"Tags": {"project": "test"}},
        },
        {
            "resource_type": "aws_vpc",
            "cloud_platform": "aws",
            "resource_name": "non-compliant-vpc",
            "properties": {
                "Tags": {"Name": "vpc"}  # Missing project tag
            },
        },
    ],
    "messages": [],
    "workflow_state": "initial",
}

result4 = nodes.compliance_checker(state4)

print(f"\nResult: {'PASSED' if result4['compliance_passed'] else 'FAILED'}")
print(f"Violations: {len(result4.get('compliance_violations', []))}")
if result4.get("compliance_violations"):
    for v in result4["compliance_violations"]:
        print(f"  - {v['resource']}: {v['issue']}")

assert not result4["compliance_passed"], "Test 4 should have FAILED but PASSED!"
assert len(result4["compliance_violations"]) == 1, (
    f"Expected 1 violation, got {len(result4['compliance_violations'])}"
)
print("[OK] Test 4 PASSED: Correctly detected missing tag in one of multiple resources")


print("\n" + "=" * 80)
print("ALL TESTS PASSED!")
print("=" * 80)

db.close()
