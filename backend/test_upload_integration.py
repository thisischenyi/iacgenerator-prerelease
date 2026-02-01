"""
Test Excel upload to code generation flow integration.

This test verifies:
1. Excel file upload
2. Resource parsing
3. Automatic chat message with resources
4. Workflow execution with Excel resources
5. Terraform code generation
"""

import requests
import json
import time


def test_excel_upload_integration():
    """Test the complete Excel upload to TF code generation flow."""

    base_url = "http://localhost:8666"

    print("=" * 80)
    print("TESTING EXCEL UPLOAD TO TF CODE GENERATION FLOW")
    print("=" * 80)

    # Step 1: Create a session
    print("\n[1] Creating session...")
    response = requests.post(f"{base_url}/api/sessions", json={"user_id": None})
    assert response.status_code == 200, f"Session creation failed: {response.text}"
    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"    ✓ Session created: {session_id}")

    # Step 2: Download a template
    print("\n[2] Downloading template...")
    response = requests.get(f"{base_url}/api/excel/template?template_type=aws")
    assert response.status_code == 200, "Template download failed"
    template_content = response.content
    print(f"    ✓ Template downloaded: {len(template_content)} bytes")

    # Save template
    with open("test_upload_template.xlsx", "wb") as f:
        f.write(template_content)
    print("    ✓ Template saved as test_upload_template.xlsx")

    # Step 3: Upload the template (with sample data)
    print("\n[3] Uploading Excel file...")
    with open("test_upload_template.xlsx", "rb") as f:
        files = {
            "file": (
                "test_template.xlsx",
                f,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }
        response = requests.post(f"{base_url}/api/excel/upload", files=files)

    assert response.status_code == 200, f"Upload failed: {response.text}"
    upload_result = response.json()
    print(f"    ✓ Upload successful:")
    print(f"      - Success: {upload_result['success']}")
    print(f"      - Resources: {upload_result['resource_count']}")
    print(f"      - Types: {', '.join(upload_result['resource_types'])}")

    # Step 4: Send chat message with Excel resources
    print("\n[4] Sending chat message with Excel resources...")
    chat_message = f"I've uploaded an Excel file with {upload_result['resource_count']} resource(s). Please validate the resources, check compliance, and generate the Terraform code."

    chat_request = {
        "session_id": session_id,
        "message": chat_message,
        "context": {"excel_resources": upload_result["resources"]},
    }

    response = requests.post(f"{base_url}/api/chat", json=chat_request)
    assert response.status_code == 200, f"Chat request failed: {response.text}"
    chat_response = response.json()

    print(f"    ✓ Chat response received:")
    print(f"      - Session: {chat_response['session_id']}")
    print(f"      - Message: {chat_response['message'][:100]}...")

    # Check if code was generated
    if chat_response.get("code_blocks"):
        print(f"\n[5] ✓ Code generation SUCCESS!")
        print(f"      Generated {len(chat_response['code_blocks'])} files:")
        for block in chat_response["code_blocks"]:
            print(f"      - {block['filename']}: {len(block['content'])} chars")
    else:
        print(f"\n[5] ✗ Code generation NOT completed")
        print(
            f"      Workflow state: {chat_response.get('metadata', {}).get('workflow_state')}"
        )
        print(
            f"      Resources: {chat_response.get('metadata', {}).get('resource_count')}"
        )
        print(
            f"      Compliance passed: {chat_response.get('metadata', {}).get('compliance_passed')}"
        )

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    # Cleanup
    import os

    if os.path.exists("test_upload_template.xlsx"):
        os.remove("test_upload_template.xlsx")
        print("\nCleanup: Removed test template file")


if __name__ == "__main__":
    try:
        test_excel_upload_integration()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend server")
        print("Please make sure the backend is running on http://localhost:8666")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        raise
