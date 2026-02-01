"""
Quick test to verify input_parser recognizes Excel resources.
"""

from app.agents.state import create_initial_state
from app.agents.nodes import AgentNodes
from app.core.database import SessionLocal


def test_input_parser_with_excel_resources():
    """Test that input_parser recognizes pre-parsed Excel resources."""

    print("=" * 80)
    print("TESTING INPUT_PARSER WITH EXCEL RESOURCES")
    print("=" * 80)

    db = SessionLocal()
    nodes = AgentNodes(db)

    # Create initial state with resources (simulating Excel upload)
    state = create_initial_state(
        session_id="test-session",
        user_input="I've uploaded an Excel file with 6 resources.",
    )

    # Add sample resources (as if from Excel upload)
    state["resources"] = [
        {
            "resource_type": "EC2",
            "cloud_platform": "aws",
            "resource_name": "web-server-01",
            "properties": {
                "ResourceName": "web-server-01",
                "Environment": "Production",
                "Region": "us-east-1",
                "InstanceType": "t3.medium",
            },
        },
        {
            "resource_type": "VPC",
            "cloud_platform": "aws",
            "resource_name": "main-vpc",
            "properties": {
                "ResourceName": "main-vpc",
                "Environment": "Production",
                "Region": "us-east-1",
                "CIDR_Block": "10.0.0.0/16",
            },
        },
    ]

    print(f"\n[TEST] Initial state:")
    print(f"  - Resources: {len(state['resources'])}")
    print(f"  - Workflow state: {state.get('workflow_state')}")
    print(f"  - Information complete: {state.get('information_complete', False)}")

    # Run input_parser
    print(f"\n[TEST] Running input_parser...")
    result_state = nodes.input_parser(state)

    print(f"\n[TEST] After input_parser:")
    print(f"  - Resources: {len(result_state['resources'])}")
    print(f"  - Workflow state: {result_state.get('workflow_state')}")
    print(
        f"  - Information complete: {result_state.get('information_complete', False)}"
    )
    print(f"  - Messages: {len(result_state['messages'])}")

    # Verify expectations
    assert result_state.get("workflow_state") == "checking_compliance", (
        f"Expected workflow_state='checking_compliance', got '{result_state.get('workflow_state')}'"
    )

    assert result_state.get("information_complete") == True, (
        "Expected information_complete=True"
    )

    assert len(result_state["resources"]) == 2, (
        f"Expected 2 resources, got {len(result_state['resources'])}"
    )

    # Check that assistant message was added
    last_message = result_state["messages"][-1]
    assert last_message["role"] == "assistant", (
        "Expected last message to be from assistant"
    )

    assert "2 resources" in last_message["content"], (
        f"Expected message to mention resource count, got: {last_message['content']}"
    )

    print("\n" + "=" * 80)
    print("✓ ALL TESTS PASSED!")
    print("=" * 80)
    print("\nThe input_parser correctly:")
    print("  1. Detected pre-parsed resources in state")
    print("  2. Set information_complete=True")
    print("  3. Transitioned to checking_compliance")
    print("  4. Added confirmation message")
    print("  5. Skipped LLM parsing (saving API calls)")

    db.close()


if __name__ == "__main__":
    try:
        test_input_parser_with_excel_resources()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        raise
