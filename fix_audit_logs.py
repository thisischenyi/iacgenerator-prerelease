import sqlite3
import json

# Connect to the database
conn = sqlite3.connect(r"C:\project\iac4\backend\iac_generator.db")
cursor = conn.cursor()

# Check if there are any audit logs with the problematic resource
cursor.execute(
    "SELECT id, session_id, details FROM audit_logs WHERE details LIKE '%blob_auditing_policy%'"
)
rows = cursor.fetchall()

print(f"Found {len(rows)} audit logs with the problematic resource")
for row in rows:
    print(f"Audit Log ID: {row[0]}, Session ID: {row[1]}")
    try:
        # Parse the JSON details
        details_dict = json.loads(row[2])
        # Update the database
        cursor.execute(
            "UPDATE audit_logs SET details = ? WHERE id = ?",
            (json.dumps(details_dict), row[0]),
        )
        print(f"  Updated audit log {row[0]}")
    except Exception as e:
        print(f"  Error updating audit log: {e}")

# Commit the changes
conn.commit()
conn.close()
print("Database updated successfully.")
