"""
Test script to verify the complete agent workflow with improved logging.
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.workflow import IaCAgentWorkflow
from app.core.database import SessionLocal
from app.models import Session as DBSessionModel
import uuid
import json


def test_ec2_generation():
    """Test EC2 instance code generation with detailed logging."""
    print("\n" + "=" * 80)
    print("STARTING EC2 GENERATION TEST")
    print("=" * 80 + "\n")

    db = SessionLocal()

    try:
        # Create a new session
        session_id = str(uuid.uuid4())
        db_session = DBSessionModel(
            session_id=session_id,
            conversation_history=[],
            resource_info=[],
            compliance_results={},
            generated_code={},
            workflow_state="initialized",
        )
        db.add(db_session)
        db.commit()

        print(f"Created test session: {session_id}")

        # Initialize workflow
        workflow = IaCAgentWorkflow(db)

        # Test 1: Initial request
        print("\n" + "-" * 80)
        print("TEST 1: Initial EC2 Request")
        print("-" * 80)

        user_input_1 = """
        我需要创建一个AWS EC2实例，配置如下：
        - Region: us-east-1
        - InstanceType: t2.micro
        - AMI: ami-0c55b159cbfafe1f0
        - KeyPairName: my-key-pair
        """

        state_1 = workflow.run(
            session_id=session_id, user_input=user_input_1, excel_data=None
        )

        print("\n" + "-" * 80)
        print("TEST 1 RESULTS:")
        print(f"Workflow State: {state_1.get('workflow_state')}")
        print(f"Resources Count: {len(state_1.get('resources', []))}")
        print(f"Generated Files: {len(state_1.get('generated_code', {}))}")
        print(f"AI Response: {state_1.get('ai_response', 'N/A')[:200]}")

        if state_1.get("resources"):
            print("\nExtracted Resources:")
            print(json.dumps(state_1["resources"], indent=2))

        if state_1.get("generated_code"):
            print("\nGenerated Files:")
            for filename, content in state_1["generated_code"].items():
                print(f"\n--- {filename} ({len(content)} bytes) ---")
                print(content[:500])
                if len(content) > 500:
                    print("...")

        # Test 2: Check if we need more information
        if state_1.get("workflow_state") == "waiting_for_user":
            print("\n" + "-" * 80)
            print("TEST 2: Providing Additional Information")
            print("-" * 80)

            # Agent is asking for more info, let's provide it
            user_input_2 = state_1.get("ai_response", "")

            # The agent might have extracted some info, let's continue
            state_2 = workflow.run(
                session_id=session_id, user_input="使用默认VPC和Subnet", excel_data=None
            )

            print("\n" + "-" * 80)
            print("TEST 2 RESULTS:")
            print(f"Workflow State: {state_2.get('workflow_state')}")
            print(f"Resources Count: {len(state_2.get('resources', []))}")
            print(f"Generated Files: {len(state_2.get('generated_code', {}))}")

            if state_2.get("generated_code"):
                print("\nGenerated Files:")
                for filename in state_2["generated_code"].keys():
                    print(
                        f"  - {filename}: {len(state_2['generated_code'][filename])} bytes"
                    )

        print("\n" + "=" * 80)
        print("EC2 GENERATION TEST COMPLETED")
        print("=" * 80 + "\n")

        # Cleanup
        db.delete(db_session)
        db.commit()

        return state_1

    except Exception as e:
        print(f"\nERROR in test: {e}")
        import traceback

        traceback.print_exc()
        return None
    finally:
        db.close()


def test_direct_generation():
    """Test direct code generation from complete resource definition."""
    print("\n" + "=" * 80)
    print("STARTING DIRECT GENERATION TEST")
    print("=" * 80 + "\n")

    from app.services.terraform_generator import TerraformCodeGenerator

    # Define a complete resource
    resources = [
        {
            "cloud_platform": "aws",
            "resource_type": "aws_ec2",
            "resource_name": "test-web-server",
            "properties": {
                "Region": "us-east-1",
                "InstanceType": "t2.micro",
                "AMI": "ami-0c55b159cbfafe1f0",
                "KeyPairName": "my-key-pair",
                "IngressRules": [
                    {"to_port": 80, "cidr_blocks": ["0.0.0.0/0"]},
                    {"to_port": 443, "cidr_blocks": ["0.0.0.0/0"]},
                ],
            },
        }
    ]

    generator = TerraformCodeGenerator()

    try:
        generated_files = generator.generate_code(resources)

        print("\n" + "-" * 80)
        print("GENERATION RESULTS:")
        print(f"Total files generated: {len(generated_files)}")

        for filename, content in generated_files.items():
            print(f"\n--- {filename} ({len(content)} bytes) ---")
            print(content)

        print("\n" + "=" * 80)
        print("DIRECT GENERATION TEST COMPLETED")
        print("=" * 80 + "\n")

        return generated_files

    except Exception as e:
        print(f"\nERROR in test: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TERRAFORM CODE GENERATION TEST SUITE")
    print("=" * 80 + "\n")

    # Run direct generation test first (simpler)
    print("Running Test Suite 1: Direct Generation")
    result1 = test_direct_generation()

    # Run full workflow test
    print("\n\nRunning Test Suite 2: Full Workflow")
    result2 = test_ec2_generation()

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80 + "\n")

    if result1 and result2:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed - check logs above")
