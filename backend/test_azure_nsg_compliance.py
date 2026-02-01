"""
Test Azure NSG compliance checking.

This test verifies that Azure NSG SecurityRules are properly validated
against security policies (e.g., blocked ports).
"""

from app.agents.state import create_initial_state
from app.agents.nodes import AgentNodes
from app.core.database import SessionLocal
from app.models import SecurityPolicy


def test_azure_nsg_compliance():
    """Test Azure NSG compliance checking with blocked ports."""

    print("=" * 80)
    print("TESTING AZURE NSG COMPLIANCE CHECKING")
    print("=" * 80)

    db = SessionLocal()
    nodes = AgentNodes(db)

    try:
        # Step 1: Create a security policy to block port 22 (SSH)
        print("\n[1] Creating security policy to block port 22...")

        # Delete existing policies for clean test
        db.query(SecurityPolicy).delete()
        db.commit()

        policy = SecurityPolicy(
            name="Block SSH",
            description="SSH (port 22) should not be open to the internet",
            rule_type="port_restriction",
            executable_rule={"block_ports": [22, 3389]},  # Block SSH and RDP
            enabled=True,
        )
        db.add(policy)
        db.commit()
        print("    ✓ Policy created: Block ports 22, 3389")

        # Step 2: Create test state with Azure NSG resource that violates the policy
        print("\n[2] Creating test state with Azure NSG resources...")

        state = create_initial_state(
            session_id="test-session-azure-nsg", user_input="Test Azure NSG compliance"
        )

        # Create Azure NSG with violating rules
        state["resources"] = [
            {
                "resource_type": "NSG",
                "cloud_platform": "azure",
                "resource_name": "web-nsg",
                "properties": {
                    "ResourceName": "web-nsg",
                    "ResourceGroup": "rg-test",
                    "Location": "eastus",
                    "SecurityRules": [
                        {
                            "name": "AllowSSH",
                            "priority": 100,
                            "direction": "Inbound",
                            "access": "Allow",
                            "protocol": "Tcp",
                            "source_port_range": "*",
                            "destination_port_range": "22",  # SSH - should be blocked
                            "source_address_prefix": "*",  # Open to internet - VIOLATION
                            "destination_address_prefix": "*",
                        },
                        {
                            "name": "AllowHTTPS",
                            "priority": 200,
                            "direction": "Inbound",
                            "access": "Allow",
                            "protocol": "Tcp",
                            "source_port_range": "*",
                            "destination_port_range": "443",  # HTTPS - OK
                            "source_address_prefix": "*",
                            "destination_address_prefix": "*",
                        },
                        {
                            "name": "AllowRDP",
                            "priority": 300,
                            "direction": "Inbound",
                            "access": "Allow",
                            "protocol": "Tcp",
                            "source_port_range": "*",
                            "destination_port_range": "3389",  # RDP - should be blocked
                            "source_address_prefix": "Internet",  # Open to internet - VIOLATION
                            "destination_address_prefix": "*",
                        },
                        {
                            "name": "DenyAll",
                            "priority": 1000,
                            "direction": "Inbound",
                            "access": "Deny",
                            "protocol": "*",
                            "source_port_range": "*",
                            "destination_port_range": "*",
                            "source_address_prefix": "*",
                            "destination_address_prefix": "*",
                        },
                    ],
                },
            }
        ]

        print(f"    ✓ Created 1 Azure NSG resource with 4 security rules")
        print(f"      - AllowSSH (port 22, source: *) - SHOULD VIOLATE")
        print(f"      - AllowHTTPS (port 443, source: *) - OK")
        print(f"      - AllowRDP (port 3389, source: Internet) - SHOULD VIOLATE")
        print(f"      - DenyAll (deny rule) - OK")

        # Step 3: Run compliance checker
        print("\n[3] Running compliance checker...")
        result_state = nodes.compliance_checker(state)

        # Step 4: Verify results
        print("\n[4] Verifying compliance check results...")

        compliance_checked = result_state.get("compliance_checked", False)
        compliance_passed = result_state.get("compliance_passed", True)
        violations = result_state.get("compliance_violations", [])

        print(f"    Compliance checked: {compliance_checked}")
        print(f"    Compliance passed: {compliance_passed}")
        print(f"    Violations found: {len(violations)}")

        # Assertions
        assert compliance_checked, "Compliance should be checked"
        assert not compliance_passed, "Compliance should FAIL due to blocked ports"
        assert len(violations) == 2, (
            f"Expected 2 violations (SSH + RDP), got {len(violations)}"
        )

        # Check violation details
        print("\n[5] Violation details:")
        for i, violation in enumerate(violations, 1):
            print(f"    Violation {i}:")
            print(f"      - Policy: {violation['policy']}")
            print(f"      - Resource: {violation['resource']}")
            print(f"      - Issue: {violation['issue']}")

            # Verify violation contains port 22 or 3389
            assert "22" in violation["issue"] or "3389" in violation["issue"], (
                f"Violation should mention port 22 or 3389: {violation['issue']}"
            )

        # Verify workflow state
        assert result_state.get("workflow_state") == "compliance_failed", (
            "Workflow should be in 'compliance_failed' state"
        )

        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED!")
        print("=" * 80)
        print("\nSUMMARY:")
        print("  - Azure NSG SecurityRules are now properly validated")
        print("  - Port 22 (SSH) violation detected: ✓")
        print("  - Port 3389 (RDP) violation detected: ✓")
        print("  - Compliance check correctly failed workflow: ✓")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        # Cleanup
        db.query(SecurityPolicy).delete()
        db.commit()
        db.close()
        print("\nCleanup: Removed test policies")


def test_azure_nsg_compliance_pass():
    """Test Azure NSG compliance checking - passing case."""

    print("\n\n" + "=" * 80)
    print("TESTING AZURE NSG COMPLIANCE - PASSING CASE")
    print("=" * 80)

    db = SessionLocal()
    nodes = AgentNodes(db)

    try:
        # Step 1: Create policy
        print("\n[1] Creating security policy to block port 22...")
        db.query(SecurityPolicy).delete()
        db.commit()

        policy = SecurityPolicy(
            name="Block SSH",
            description="SSH should not be open to internet",
            rule_type="port_restriction",
            executable_rule={"block_ports": [22]},
            enabled=True,
        )
        db.add(policy)
        db.commit()
        print("    ✓ Policy created")

        # Step 2: Create NSG that complies with policy
        print("\n[2] Creating compliant Azure NSG resource...")

        state = create_initial_state(
            session_id="test-session-azure-nsg-pass", user_input="Test"
        )

        state["resources"] = [
            {
                "resource_type": "NSG",
                "cloud_platform": "azure",
                "resource_name": "compliant-nsg",
                "properties": {
                    "ResourceName": "compliant-nsg",
                    "SecurityRules": [
                        {
                            "name": "AllowHTTPS",
                            "direction": "Inbound",
                            "access": "Allow",
                            "protocol": "Tcp",
                            "destination_port_range": "443",
                            "source_address_prefix": "*",  # Only HTTPS open - OK
                        },
                        {
                            "name": "AllowSSHFromOffice",
                            "direction": "Inbound",
                            "access": "Allow",
                            "protocol": "Tcp",
                            "destination_port_range": "22",
                            "source_address_prefix": "203.0.113.0/24",  # Restricted IP - OK
                        },
                    ],
                },
            }
        ]

        print("    ✓ Created compliant NSG (SSH only from specific IP)")

        # Step 3: Run compliance
        print("\n[3] Running compliance checker...")
        result_state = nodes.compliance_checker(state)

        # Step 4: Verify
        print("\n[4] Verifying results...")
        compliance_passed = result_state.get("compliance_passed", False)
        violations = result_state.get("compliance_violations", [])

        print(f"    Compliance passed: {compliance_passed}")
        print(f"    Violations: {len(violations)}")

        assert compliance_passed, "Compliance should PASS"
        assert len(violations) == 0, f"Expected 0 violations, got {len(violations)}"
        assert result_state.get("workflow_state") == "generating_code", (
            "Workflow should proceed to code generation"
        )

        print("\n✓ TEST PASSED: Compliant NSG correctly validated")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    finally:
        db.query(SecurityPolicy).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    try:
        test_azure_nsg_compliance()
        test_azure_nsg_compliance_pass()
        print("\n\n" + "=" * 80)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 80)
    except Exception:
        import sys

        sys.exit(1)
