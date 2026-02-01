"""
Fix database schema - Update resource_info default value from {} to []
"""

import sqlite3
import json

# Path to the database
DB_PATH = "iac_generator.db"


def fix_database():
    """Fix existing sessions with incorrect resource_info format."""
    print("=" * 80)
    print("Fixing Database Schema")
    print("=" * 80)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check current sessions
        cursor.execute("SELECT session_id, resource_info FROM sessions")
        sessions = cursor.fetchall()

        print(f"\nFound {len(sessions)} sessions")

        fixed_count = 0
        for session_id, resource_info in sessions:
            # Parse the JSON
            try:
                data = json.loads(resource_info) if resource_info else None

                # If it's a dict (incorrect), change to list
                if isinstance(data, dict) and not isinstance(data, list):
                    print(f"  Fixing session {session_id}: dict -> list")
                    cursor.execute(
                        "UPDATE sessions SET resource_info = ? WHERE session_id = ?",
                        (json.dumps([]), session_id),
                    )
                    fixed_count += 1
            except:
                # If parsing fails, set to empty list
                print(f"  Resetting session {session_id} to []")
                cursor.execute(
                    "UPDATE sessions SET resource_info = ? WHERE session_id = ?",
                    (json.dumps([]), session_id),
                )
                fixed_count += 1

        conn.commit()
        print(f"\n[OK] Fixed {fixed_count} sessions")
        print("[OK] Database schema corrected")

        conn.close()

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    fix_database()
    print("\n" + "=" * 80)
    print("Done! Please restart the backend server.")
    print("=" * 80)
