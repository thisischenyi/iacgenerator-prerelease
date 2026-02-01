import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.database import SessionLocal
from app.models import SecurityPolicy


def list_policies():
    db = SessionLocal()
    try:
        policies = db.query(SecurityPolicy).all()

        with open("policies_dump.txt", "w", encoding="utf-8") as f:
            f.write(f"Total Policies found: {len(policies)}\n")
            f.write("-" * 50 + "\n")
            for p in policies:
                f.write(f"ID: {p.id}\n")
                f.write(f"Name: {p.name}\n")
                f.write(f"Description: {p.description}\n")
                f.write(f"Enabled: {p.enabled}\n")
                f.write(f"Natural Language Rule: {p.natural_language_rule}\n")
                f.write(f"Executable Rule: {p.executable_rule}\n")
                f.write("-" * 50 + "\n")
        print("Policies dumped to policies_dump.txt")
    finally:
        db.close()


if __name__ == "__main__":
    list_policies()
