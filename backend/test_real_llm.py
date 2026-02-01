import sys
import os
import json
from dotenv import load_dotenv

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Load environment variables from backend/.env
load_dotenv(os.path.join(os.getcwd(), "backend", ".env"))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models import SecurityPolicy, Session as DBSession
from app.agents.workflow import IaCAgentWorkflow


def setup_db():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Enable a security policy for the test
    # We check if one exists, if not create one
    policy = db.query(SecurityPolicy).filter_by(name="Default Security").first()
    if not policy:
        print("Creating default security policy for testing...")
        policy = SecurityPolicy(
            name="Default Security",
            description="Block high risk ports",
            natural_language_rule="Block ports 22 and 3389 to 0.0.0.0/0",
            executable_rule={"block_ports": [22, 3389, 20, 21]},
            severity="error",
            enabled=True,
        )
        db.add(policy)
        db.commit()
    else:
        if not policy.enabled:
            print("Enabling existing security policy...")
            policy.enabled = True
            db.commit()

    return db


def run_real_test():
    print("--- Starting Real LLM Test ---")

    try:
        db = setup_db()
    except Exception as e:
        print(f"Database setup failed: {e}")
        return

    workflow = IaCAgentWorkflow(db)

    # Generate a unique session ID
    import uuid

    session_id = f"test-real-{str(uuid.uuid4())[:8]}"

    # The user's prompt containing the violation
    user_input = "创建一个aws ec2, Region: us-east-1 InstanceType: t2.micro AMI: ami-0ec0e1257462ee711 VPC_ID: vpc-dff3rfsj9 Subnet_ID: subnet-12345678 KeyPairName: my-key security group: access port 3389 from anywhere"

    print(f"Session ID: {session_id}")
    print(f"User Input: {user_input}")
    print("-" * 50)

    try:
        final_state = workflow.run(session_id, user_input)

        print("-" * 50)
        print("Workflow Execution Finished")
        print(f"Final State: {final_state['workflow_state']}")

        # Check resources extracted
        resources = final_state.get("resources", [])
        print(f"Resources Found: {len(resources)}")
        if resources:
            print(json.dumps(resources, indent=2))

        # Check compliance
        compliance_results = final_state.get("compliance_violations", [])
        if compliance_results:
            print("\n!!! Compliance Violations Detected !!!")
            for v in compliance_results:
                print(f"- {v}")
        else:
            print("\nNo Compliance Violations reported (Pass).")

        # Check AI Response
        print("\nAI Response:")
        try:
            print(final_state.get("ai_response", "No response"))
        except UnicodeEncodeError:
            print(
                final_state.get("ai_response", "No response")
                .encode("utf-8", errors="ignore")
                .decode("utf-8")
            )

    except Exception as e:
        print(f"Error running workflow: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    run_real_test()
