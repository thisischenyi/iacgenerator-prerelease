import httpx
import pandas as pd
import io
import os
import zipfile
import sys
import json
import time

BASE_URL = "http://localhost:8666"
TEST_OUTPUT_DIR = "test_e2e_output"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def print_pass(msg):
    print(f"{GREEN}[PASS] {msg}{RESET}")


def print_fail(msg):
    print(f"{RED}[FAIL] {msg}{RESET}")


def create_sample_excel():
    """Create a sample Excel file with AWS resources."""
    output = io.BytesIO()

    # AWS VPC Data
    vpc_data = [
        {
            "Region": "us-east-1",
            "ResourceName": "e2e-test-vpc",
            "CidrBlock": "10.0.0.0/16",
            "EnableDnsHostnames": True,
            "EnableDnsSupport": True,
            "Environment": "Test",
            "Project": "E2E",
        }
    ]

    # AWS Subnet Data
    subnet_data = [
        {
            "Region": "us-east-1",
            "ResourceName": "e2e-test-subnet",
            "VpcId": "e2e-test-vpc",
            "CidrBlock": "10.0.1.0/24",
            "AvailabilityZone": "us-east-1a",
            "MapPublicIpOnLaunch": True,
            "SubnetType": "Public",
            "Environment": "Test",
            "Project": "E2E",
        }
    ]

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        pd.DataFrame(vpc_data).to_excel(writer, sheet_name="AWS_VPC", index=False)
        pd.DataFrame(subnet_data).to_excel(writer, sheet_name="AWS_Subnet", index=False)

    output.seek(0)
    return output.getvalue()


def run_test():
    print(f"Starting End-to-End Test against {BASE_URL}...\n")

    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    try:
        # 1. Health Check
        print("1. Testing Health Endpoint...")
        resp = client.get("/health")
        if resp.status_code == 200:
            print_pass("Backend is healthy")
        else:
            print_fail(f"Backend unhealthy: {resp.text}")
            return

        # 2. Check Policies
        print("\n2. Checking Policies...")
        resp = client.get("/api/policies")
        if resp.status_code == 200:
            policies = resp.json()
            print_pass(f"Found {len(policies)} policies")
        else:
            print_fail("Failed to fetch policies")

        # 3. Create Session
        print("\n3. Creating Chat Session...")
        resp = client.post("/api/sessions", json={"user_id": "e2e_bot"})
        if resp.status_code == 201:
            session_id = resp.json()["session_id"]
            print_pass(f"Session created: {session_id}")
        else:
            print_fail(f"Failed to create session: {resp.status_code} {resp.text}")
            return

        # 4. Text Chat Simulation (Skipped to avoid timeout on missing LLM key)
        # print("\n4. Sending Text Message...")
        # ... skipped ...

        # 5. Excel Upload and Generation Flow
        print("\n5. Testing Excel Upload Flow...")
        excel_bytes = create_sample_excel()

        # Upload
        files = {
            "file": (
                "test_infra.xlsx",
                excel_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }
        resp = client.post("/api/excel/upload", files=files)

        if resp.status_code != 200:
            print_fail(f"Upload failed: {resp.text}")
            return

        upload_data = resp.json()
        print_pass("Excel uploaded successfully")
        resources = upload_data.get("resources", [])
        print(f"   Found {len(resources)} resources")

        if not resources:
            print_fail("No resources parsed from Excel")
            return

        # Generate Code
        print("\n6. Generating Terraform Code...")
        gen_payload = {"resources": resources, "metadata": {"source": "e2e_test"}}
        resp = client.post("/api/generate", json=gen_payload)

        if resp.status_code != 200:
            print_fail(f"Generation failed: {resp.text}")
            return

        gen_data = resp.json()
        if gen_data.get("success"):
            print_pass("Code generated successfully")
            print(f"   Summary: {gen_data['summary']}")
        else:
            print_fail(f"Generation reported failure: {json.dumps(gen_data, indent=2)}")
            return

        # Download ZIP
        download_url = gen_data.get("download_url")
        if not download_url:
            print_fail("No download URL in response")
            return

        print(f"\n7. Downloading ZIP from {download_url}...")
        # Remove /api prefix if present in URL because base_url has it?
        # The API returns relative URL like /api/generate/download/...
        # client.base_url is http://localhost:8000
        # If download_url starts with /api, we should use it relative to host

        if download_url.startswith("/api/"):
            # strip /api/ prefix if base_url includes it, but base_url is root here
            # so just use the url as is
            pass

        resp = client.get(download_url)

        if resp.status_code == 200:
            zip_path = os.path.join(TEST_OUTPUT_DIR, "generated.zip")
            with open(zip_path, "wb") as f:
                f.write(resp.content)
            print_pass(f"ZIP saved to {zip_path}")

            # Verify ZIP content
            with zipfile.ZipFile(zip_path, "r") as z:
                files = z.namelist()
                print(f"   Zip contents: {', '.join(files)}")
                if "main.tf" in files and "provider.tf" in files:
                    print_pass("Zip contains expected Terraform files")
                else:
                    print_fail("Zip missing core Terraform files")
        else:
            print_fail(f"Download failed: {resp.status_code}")

    except Exception as e:
        print_fail(f"Test exception: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    run_test()
