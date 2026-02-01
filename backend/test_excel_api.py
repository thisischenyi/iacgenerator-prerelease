"""Test Excel processing API."""

import requests
import os

BASE_URL = "http://localhost:8666/api/excel"


def test_template_download():
    """Test downloading the Excel template."""
    print("Testing template download...")
    try:
        response = requests.get(f"{BASE_URL}/template?template_type=full")
        if response.status_code == 200:
            filename = "test_template.xlsx"
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"✅ Template downloaded successfully to {filename}")
            return filename
        else:
            print(
                f"❌ Failed to download template: {response.status_code} - {response.text}"
            )
            return None
    except Exception as e:
        print(f"❌ Error downloading template: {str(e)}")
        return None


def test_excel_upload(filename):
    """Test uploading the Excel file."""
    print(f"Testing upload of {filename}...")
    try:
        with open(filename, "rb") as f:
            files = {
                "file": (
                    filename,
                    f,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            }
            response = requests.post(f"{BASE_URL}/upload", files=files)

        if response.status_code == 200:
            result = response.json()
            print("✅ Upload successful!")
            print(f"   Resource Count: {result.get('resource_count')}")
            print(f"   Resource Types: {result.get('resource_types')}")
            print(f"   Success: {result.get('success')}")
            if result.get("errors"):
                print(f"   Errors: {result.get('errors')}")
            if result.get("warnings"):
                print(f"   Warnings: {result.get('warnings')}")
        else:
            print(f"❌ Failed to upload file: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ Error uploading file: {str(e)}")


if __name__ == "__main__":
    # Fix for Windows console encoding
    import sys

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    # Ensure server is running
    try:
        health = requests.get("http://localhost:8000/health")
        if health.status_code != 200:
            print("❌ Server is not healthy. Please start the server first.")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please start the server first.")
        exit(1)

    # Run tests
    template_file = test_template_download()
    if template_file:
        test_excel_upload(template_file)
        # Clean up
        try:
            os.remove(template_file)
            print("Cleaned up test file.")
        except:
            pass
