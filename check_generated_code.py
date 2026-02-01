import sqlite3
import json

conn = sqlite3.connect(r"C:\project\iac4\backend\iac_generator.db")
cursor = conn.cursor()
cursor.execute(
    'SELECT session_id, workflow_state, generated_code FROM sessions WHERE workflow_state IN ("completed", "reviewing_code") ORDER BY created_at DESC LIMIT 3'
)

print("Sessions with generated code:")
print("-" * 80)
for row in cursor.fetchall():
    session_id, workflow_state, generated_code = row
    print(f"Session: {session_id}")
    print(f"  Workflow State: {workflow_state}")
    if generated_code:
        try:
            code = json.loads(generated_code)
            print(f"  Generated Files: {list(code.keys())}")
            for filename, content in code.items():
                print(f"\n  === {filename} ===")
                print(content[:500])  # First 500 chars
        except:
            print(f"  Generated Code (raw): {generated_code[:200]}")
    else:
        print(f"  Generated Code: None/Empty")
    print()

conn.close()
