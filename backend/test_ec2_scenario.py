import json
from unittest.mock import MagicMock, patch
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.agents.workflow import IaCAgentWorkflow
from app.agents.state import create_initial_state
from app.models import SecurityPolicy


def test_ec2_rdp_violation():
    # Mock Database Session
    mock_db = MagicMock()

    # Mock SecurityPolicy query
    # We want policies to be returned so compliance check runs
    mock_policy = MagicMock()
    mock_policy.enabled = True
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_policy]

    # Initialize workflow
    workflow = IaCAgentWorkflow(mock_db)

    # Mock LLMClient in nodes
    mock_llm_response_parser = json.dumps(
        {
            "resources": [
                {
                    "type": "aws_ec2",
                    "name": "web-server",
                    "properties": {
                        "Region": "us-east-1",
                        "InstanceType": "t2.micro",
                        "AMI": "ami-0ec0e1257462ee711",
                        "VPC_ID": "vpc-dff3rfsj9",
                        "Subnet_ID": "subnet-12345678",
                        "KeyPairName": "my-key",
                        "SecurityGroups": ["sg-custom"],
                        "IngressRules": [
                            {"to_port": 3389, "cidr_blocks": ["0.0.0.0/0"]}
                        ],
                    },
                }
            ]
        }
    )

    mock_llm_response_validation = json.dumps(
        {
            "information_complete": True,
            "missing_fields": [],
            "resources": [
                {
                    "type": "aws_ec2",
                    "name": "web-server",
                    "properties": {
                        "Region": "us-east-1",
                        "InstanceType": "t2.micro",
                        "AMI": "ami-0ec0e1257462ee711",
                        "VPC_ID": "vpc-dff3rfsj9",
                        "Subnet_ID": "subnet-12345678",
                        "KeyPairName": "my-key",
                        "SecurityGroups": ["sg-custom"],
                        "IngressRules": [
                            {"to_port": 3389, "cidr_blocks": ["0.0.0.0/0"]}
                        ],
                    },
                }
            ],
        }
    )

    # Side effect for LLM chat to return different responses based on prompt
    def llm_side_effect(messages, **kwargs):
        prompt = messages[0]["content"]
        if "Analyze the user's request" in prompt:
            return mock_llm_response_parser
        elif (
            "intelligent infrastructure assistant validating user requirements"
            in prompt
        ):
            return mock_llm_response_validation
        return "{}"

    workflow.nodes.llm_client.chat = MagicMock(side_effect=llm_side_effect)

    # Run workflow
    user_input = "创建一个aws ec2, Region: us-east-1 InstanceType: t2.micro AMI: ami-0ec0e1257462ee711 VPC_ID: vpc-dff3rfsj9 Subnet_ID: subnet-12345678 KeyPairName: my-key security group: access port 3389 from anywhere"

    # We need to manually inject a session mock behavior for _load_state
    workflow.db.query.return_value.filter.return_value.first.return_value = (
        None  # No existing session
    )

    print("Running workflow...")
    final_state = workflow.run("test-session-id", user_input)

    print("\nWorkflow State:", final_state["workflow_state"])
    print("Compliance Passed:", final_state.get("compliance_passed"))

    if final_state.get("compliance_violations"):
        print("\nViolations Found:")
        for v in final_state["compliance_violations"]:
            print(f"- {v['issue']}")

    # Verification
    if final_state["workflow_state"] == "compliance_failed":
        print("\nSUCCESS: RDP violation correctly detected and workflow stopped.")
    else:
        print("\nFAILURE: Workflow did not stop at compliance check.")


if __name__ == "__main__":
    test_ec2_rdp_violation()
