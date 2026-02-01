"""Verify compliant resources pass the check."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.agents.nodes import AgentNodes

db = SessionLocal()

print("=" * 80)
print("SCENARIO: User creating infrastructure WITH required tags")
print("=" * 80)

state = {
    "session_id": "compliant-test-001",
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
                    "project": "iac4",  # Has project tag!
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
                    "Project": "iac4",  # Has Project tag (case-insensitive)!
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
print(f"Workflow State: {result['workflow_state']}")

if result["compliance_passed"]:
    print("\n[SUCCESS] Compliant resources correctly pass the check!")
    print("The system is now ready to generate Terraform code.")
else:
    print("\n[ERROR] Something is wrong - compliance check should have passed!")
    for v in result.get("compliance_violations", []):
        print(f"  - {v['resource']}: {v['issue']}")
    sys.exit(1)

db.close()
