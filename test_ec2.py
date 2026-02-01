#!/usr/bin/env python3
"""Test script to verify EC2 resource data preservation through the agent workflow."""

import requests
import json
import time

BASE_URL = "http://localhost:8666"


def test_ec2_generation():
    """Test EC2 instance generation with all details."""

    # Step 1: Create a new session
    print("Step 1: Creating new session...")
    response = requests.post(f"{BASE_URL}/api/sessions", json={"user_id": "test-user"})
    response.raise_for_status()
    session = response.json()
    session_id = session["session_id"]
    print(f"  Success: Session created: {session_id}\n")

    # Step 2: Send EC2 creation request with full details
    print("Step 2: Sending EC2 creation request...")
    user_message = "create a aws ec2, Region: us-east-1 InstanceType: t2.micro AMI: ami-0ec0e1257462ee711 VPC_ID: vpc-dff3rfsj9 Subnet_ID: subnet-12345678 KeyPairName: my-key security group: access port 1235 from anywhere"

    payload = {"session_id": session_id, "message": user_message}

    print(f"  Sending: {user_message}")
    response = requests.post(f"{BASE_URL}/api/chat", json=payload)
    response.raise_for_status()
    result = response.json()

    print(f"\n  AI Response: {result.get('ai_response', 'No response')}\n")

    # Step 3: Wait a bit for workflow to complete
    print("Step 3: Waiting for workflow completion...")
    time.sleep(2)

    # Step 4: Get session state to check generated code
    print("Step 4: Fetching session state...")
    response = requests.get(f"{BASE_URL}/api/sessions/{session_id}")
    response.raise_for_status()
    conversation_state = response.json()

    generated_code = conversation_state.get("generated_code", {})

    if generated_code:
        print(f"  [OK] Generated {len(generated_code)} files:\n")
        for filename, content in generated_code.items():
            print(f"  File: {filename}")
            print(f"  {'=' * 60}")
            print(content)
            print(f"  {'=' * 60}\n")

            # Check for missing data in EC2 instance
            if "ec2.tf" in filename:
                issues = []
                if (
                    "subnet_id" not in content
                    or 'subnet_id = ""' in content
                    or "subnet_id.." in content
                ):
                    issues.append("[X] subnet_id is missing or empty")
                else:
                    print("  [OK] subnet_id is present")

                if "key_name" not in content or 'key_name = ""' in content:
                    issues.append("[X] key_name is missing or empty")
                else:
                    print("  [OK] key_name is present")

                if "vpc_security_group_ids = []" in content:
                    issues.append("[X] vpc_security_group_ids is empty")
                else:
                    print("  [OK] vpc_security_group_ids has values")

                if "ami-0ec0e1257462ee711" in content:
                    print("  [OK] AMI ID is correct")
                else:
                    issues.append("[X] AMI ID is missing or incorrect")

                if "t2.micro" in content:
                    print("  [OK] Instance type is correct")
                else:
                    issues.append("[X] Instance type is missing or incorrect")

                if issues:
                    print("\n  Issues found:")
                    for issue in issues:
                        print(f"    {issue}")
                else:
                    print("\n  [SUCCESS] All EC2 details are correctly populated!")

    else:
        print("  [ERROR] No code was generated!")

    return conversation_state


if __name__ == "__main__":
    print("=" * 60)
    print("Testing EC2 Resource Data Preservation")
    print("=" * 60 + "\n")

    try:
        result = test_ec2_generation()
        print("\nTest completed!")
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback

        traceback.print_exc()
