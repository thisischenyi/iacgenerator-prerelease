"""Verify the fix with a realistic scenario."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine, Base
from app.models import SecurityPolicy
from app.schemas import CloudPlatform
from app.agents.nodes import AgentNodes

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Scenario: User creating AWS infrastructure without project tag
print("=" * 80)
print("REALISTIC SCENARIO: User creating infrastructure without required tags")
print("=" * 80)

state = {
    "session_id": "realistic-test-001",
    "resources": [
        {
            "resource_type": "aws_vpc",
            "cloud_platform": "aws",
            "resource_name": "production-vpc",
            "properties": {
                "CidrBlock": "10.0.0.0/16",
                "Tags": {
                    "Name": "production-vpc",
                    "Environment": "production",
                    # Missing "project" tag - should fail compliance!
                },
            },
        },
        {
            "resource_type": "aws_instance",
            "cloud_platform": "aws",
            "resource_name": "web-server",
            "properties": {
                "InstanceType": "t3.medium",
                "Tags": {
                    "Name": "web-server",
                    "Role": "web",
                    # Missing "project" tag - should fail compliance!
                },
            },
        },
    ],
    "messages": [],
    "workflow_state": "initial",
}

nodes = AgentNodes(db)
result = nodes.compliance_checker(state)

print("\n" + "=" * 80)
print("COMPLIANCE CHECK RESULTS")
print("=" * 80)
print(f"Status: {'PASSED' if result['compliance_passed'] else 'FAILED'}")
print(f"Violations: {len(result.get('compliance_violations', []))}")
print(f"\nViolation Details:")
for v in result.get("compliance_violations", []):
    print(f"  - Policy: {v['policy']}")
    print(f"    Resource: {v['resource']}")
    print(f"    Issue: {v['issue']}")
    print()

print(f"Workflow State: {result['workflow_state']}")
print(f"Should Continue: {result.get('should_continue', 'Not set')}")

if not result["compliance_passed"]:
    print("\n[SUCCESS] The fix is working correctly!")
    print("Resources without 'project' tag are now properly blocked.")
else:
    print("\n[ERROR] Something is wrong - compliance check should have failed!")
    sys.exit(1)

db.close()
