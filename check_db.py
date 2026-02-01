import sqlite3
import json

conn = sqlite3.connect(r"C:\project\iac4\backend\iac_generator.db")
cursor = conn.cursor()
cursor.execute(
    "SELECT session_id, workflow_state, resource_info FROM sessions ORDER BY created_at DESC LIMIT 5"
)

print("Recent sessions:")
print("-" * 80)
for row in cursor.fetchall():
    session_id, workflow_state, resource_info = row
    print(f"Session: {session_id}")
    print(f"  Workflow State: {workflow_state}")
    if resource_info:
        try:
            resources = json.loads(resource_info)
            print(f"  Resources: {json.dumps(resources, indent=4)}")
        except:
            print(f"  Resources (raw): {resource_info}")
    else:
        print(f"  Resources: None")
    print()

conn.close()
