import requests
import sys

BASE_URL = "http://localhost:8666"


def test_download():
    print(f"Testing template download from {BASE_URL}...")
    try:
        url = f"{BASE_URL}/api/excel/template?template_type=full"
        print(f"GET {url}")

        response = requests.get(url)

        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"Content Length: {len(response.content)} bytes")
            print(f"Content Type: {response.headers.get('content-type')}")
            print(f"Disposition: {response.headers.get('content-disposition')}")

            with open("test_download.xlsx", "wb") as f:
                f.write(response.content)
            print("Successfully saved to test_download.xlsx")
        else:
            print(f"Error Response: {response.text}")

    except Exception as e:
        print(f"Exception: {str(e)}")


if __name__ == "__main__":
    test_download()
