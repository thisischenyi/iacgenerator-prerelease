import sqlite3
import os

db_path = r"backend\iac_generator.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== Last Deployment Error ===\n")

cursor.execute("SELECT * FROM deployments ORDER BY created_at DESC LIMIT 1")
row = cursor.fetchone()

if row:
    print(f"Deployment ID: {row['deployment_id']}")
    print(f"Status: {row['status']}")
    print(f"Created: {row['created_at']}")
    print(f"\n--- Error Message ---")
    print(row["error_message"] if row["error_message"] else "No error message")

    print(f"\n--- Plan Output (first 1000 chars) ---")
    if row["plan_output"]:
        print(row["plan_output"][:1000])
    else:
        print("No plan output")

    # Check environment
    env_id = row["environment_id"]
    cursor.execute("SELECT * FROM deployment_environments WHERE id=?", (env_id,))
    env = cursor.fetchone()
    if env:
        print(f"\n--- Environment Info ---")
        print(f"Name: {env['name']}")
        print(f"Platform: {env['cloud_platform']}")
        print(
            f"AWS Credentials: {'Configured' if env['aws_access_key_id'] else 'Missing'}"
        )
        print(
            f"Azure Credentials: {'Configured' if env['azure_subscription_id'] else 'Missing'}"
        )
else:
    print("No deployments found in database")

conn.close()
