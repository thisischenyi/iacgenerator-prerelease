#!/usr/bin/env python3
"""Quick test to generate EC2 and check result."""

import requests
import json

BASE_URL = "http://localhost:8666"

# Create session
response = requests.post(f"{BASE_URL}/api/sessions", json={"user_id": "test"})
session = response.json()
session_id = session["session_id"]
print(f"Session: {session_id}")

# Send EC2 request
message = "create a aws ec2, Region: us-east-1 InstanceType: t2.micro AMI: ami-0ec0e1257462ee711 VPC_ID: vpc-dff3rfsj9 Subnet_ID: subnet-12345678 KeyPairName: my-key security group: access port 1235 from anywhere"
response = requests.post(
    f"{BASE_URL}/api/chat", json={"session_id": session_id, "message": message}
)
result = response.json()
ai_msg = result.get("message", "No message")
# Remove special characters that might cause encoding issues
ai_msg = ai_msg.replace("✓", "[OK]").replace("✗", "[X]")
print(f"\nAI Response: {ai_msg[:200]}...\n")

# Wait and get session
import time

time.sleep(3)  # Increase wait time
response = requests.get(f"{BASE_URL}/api/sessions/{session_id}")
session_state = response.json()

print(f"Session state keys: {list(session_state.keys())}")
print(f"Workflow state: {session_state.get('workflow_state')}")

generated_code = session_state.get("generated_code", {})
if generated_code and "main.tf" in generated_code:
    print("=== main.tf ===")
    print(generated_code["main.tf"])

    # Check for required fields
    main_tf = generated_code["main.tf"]
    checks = {
        "subnet_id": "subnet_id" in main_tf and "subnet-12345678" in main_tf,
        "key_name": "key_name" in main_tf and "my-key" in main_tf,
        "security_group": "aws_security_group" in main_tf,
        "port_1235": "1235" in main_tf,
    }

    print("\n=== Validation ===")
    for check, passed in checks.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {check}")
else:
    print("[ERROR] No code generated!")
