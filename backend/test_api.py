"""
Quick API test script to verify the improved logging system.
"""

import requests
import json
import uuid

# API base URL
BASE_URL = "http://localhost:8666/api/v1"


def test_create_session():
    """Test creating a new session."""
    print("\n" + "=" * 80)
    print("TEST 1: Create Session")
    print("=" * 80)

    response = requests.post(f"{BASE_URL}/sessions")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        session_id = data.get("session_id")
        print(f"✓ Session created: {session_id}")
        return session_id
    else:
        print(f"✗ Failed: {response.text}")
        return None


def test_chat_ec2_request(session_id):
    """Test EC2 creation request through chat API."""
    print("\n" + "=" * 80)
    print("TEST 2: EC2 Creation Request")
    print("=" * 80)

    payload = {
        "session_id": session_id,
        "message": """
我需要创建一个AWS EC2实例：
- Region: us-east-1
- InstanceType: t2.micro
- AMI: ami-0c55b159cbfafe1f0
- KeyPairName: my-test-key
        """,
    }

    print(f"Sending request to: {BASE_URL}/chat")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    response = requests.post(
        f"{BASE_URL}/chat", json=payload, headers={"Content-Type": "application/json"}
    )

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Response received")
        print(f"Message: {data.get('message', 'N/A')[:200]}")
        print(f"Workflow State: {data.get('metadata', {}).get('workflow_state')}")
        print(f"Resources: {data.get('metadata', {}).get('resource_count')}")

        if data.get("code_blocks"):
            print(f"\n✓ Generated {len(data['code_blocks'])} files:")
            for block in data["code_blocks"]:
                print(f"  - {block['filename']}: {len(block['content'])} bytes")

        return data
    else:
        print(f"✗ Failed: {response.text}")
        return None


def test_health_check():
    """Test health endpoint."""
    print("\n" + "=" * 80)
    print("TEST 0: Health Check")
    print("=" * 80)

    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ API is healthy")
            print(f"Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"✗ Health check failed")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to API: {e}")
        print(f"\n⚠️  Please start the backend server first:")
        print(
            f"   cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8666 --reload"
        )
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("IaC4 API Test Suite")
    print("=" * 80)

    # Test 0: Health check
    if not test_health_check():
        exit(1)

    # Test 1: Create session
    session_id = test_create_session()
    if not session_id:
        print("\n✗ Session creation failed, aborting tests")
        exit(1)

    # Test 2: Chat request
    result = test_chat_ec2_request(session_id)

    print("\n" + "=" * 80)
    if result and result.get("code_blocks"):
        print("✓ ALL TESTS PASSED")
    else:
        print("⚠️  Tests completed with warnings (check logs above)")
    print("=" * 80 + "\n")
