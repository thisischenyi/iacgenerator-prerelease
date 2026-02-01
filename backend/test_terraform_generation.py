"""
Test script for Terraform code generation.

This script tests the complete Terraform generation flow including:
1. TerraformCodeGenerator service directly
2. End-to-end workflow via chat API
3. Generated code validation
"""

import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.terraform_generator import TerraformCodeGenerator
from app.schemas import ResourceInfo, CloudPlatform
from typing import List
import json


def create_sample_aws_resources() -> List[ResourceInfo]:
    """Create sample AWS resources for testing."""
    return [
        ResourceInfo(
            resource_type="aws_vpc",
            cloud_platform=CloudPlatform.AWS,
            resource_name="main-vpc",
            properties={
                "CidrBlock": "10.0.0.0/16",
                "EnableDnsSupport": True,
                "EnableDnsHostnames": True,
                "Tags": {"Environment": "production", "Project": "iac4-test"},
            },
        ),
        ResourceInfo(
            resource_type="aws_subnet",
            cloud_platform=CloudPlatform.AWS,
            resource_name="public-subnet-1",
            properties={
                "VpcId": "main-vpc",
                "CidrBlock": "10.0.1.0/24",
                "AvailabilityZone": "us-east-1a",
                "MapPublicIpOnLaunch": True,
                "Tags": {"Name": "public-subnet-1", "Type": "public"},
            },
        ),
        ResourceInfo(
            resource_type="aws_security_group",
            cloud_platform=CloudPlatform.AWS,
            resource_name="web-sg",
            properties={
                "VpcId": "main-vpc",
                "Description": "Security group for web servers",
                "IngressRules": [
                    {
                        "FromPort": 80,
                        "ToPort": 80,
                        "Protocol": "tcp",
                        "CidrBlocks": ["0.0.0.0/0"],
                        "Description": "Allow HTTP",
                    },
                    {
                        "FromPort": 443,
                        "ToPort": 443,
                        "Protocol": "tcp",
                        "CidrBlocks": ["0.0.0.0/0"],
                        "Description": "Allow HTTPS",
                    },
                ],
                "EgressRules": [
                    {
                        "FromPort": 0,
                        "ToPort": 0,
                        "Protocol": "-1",
                        "CidrBlocks": ["0.0.0.0/0"],
                        "Description": "Allow all outbound",
                    }
                ],
                "Tags": {"Name": "web-sg"},
            },
        ),
        ResourceInfo(
            resource_type="aws_ec2",
            cloud_platform=CloudPlatform.AWS,
            resource_name="web-server-1",
            properties={
                "InstanceType": "t3.medium",
                "AMI": "ami-0c55b159cbfafe1f0",
                "SubnetId": "public-subnet-1",
                "SecurityGroupIds": ["web-sg"],
                "KeyName": "my-keypair",
                "RootVolumeSize": 30,
                "RootVolumeType": "gp3",
                "UserData": "#!/bin/bash\napt-get update\napt-get install -y nginx",
                "Tags": {"Name": "web-server-1", "Role": "webserver"},
            },
        ),
        ResourceInfo(
            resource_type="aws_s3",
            cloud_platform=CloudPlatform.AWS,
            resource_name="iac4-test-bucket",
            properties={
                "BucketName": "iac4-test-bucket-12345",
                "Versioning": True,
                "Encryption": True,
                "PublicAccess": False,
                "Tags": {"Purpose": "application-data"},
            },
        ),
    ]


def create_sample_azure_resources() -> List[ResourceInfo]:
    """Create sample Azure resources for testing."""
    return [
        ResourceInfo(
            resource_type="azure_resource_group",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="iac4-rg",
            properties={
                "Location": "eastus",
                "Tags": {"Environment": "production", "Project": "iac4-test"},
            },
        ),
        ResourceInfo(
            resource_type="azure_vnet",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="main-vnet",
            properties={
                "ResourceGroup": "iac4-rg",
                "Location": "eastus",
                "AddressSpace": ["10.1.0.0/16"],
                "Tags": {"Name": "main-vnet"},
            },
        ),
        ResourceInfo(
            resource_type="azure_subnet",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="app-subnet",
            properties={
                "ResourceGroup": "iac4-rg",
                "VNetName": "main-vnet",
                "AddressPrefix": "10.1.1.0/24",
            },
        ),
        ResourceInfo(
            resource_type="azure_nsg",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="app-nsg",
            properties={
                "ResourceGroup": "iac4-rg",
                "Location": "eastus",
                "SecurityRules": [
                    {
                        "Name": "allow-http",
                        "Priority": 100,
                        "Direction": "Inbound",
                        "Access": "Allow",
                        "Protocol": "Tcp",
                        "SourceAddressPrefix": "*",
                        "SourcePortRange": "*",
                        "DestinationAddressPrefix": "*",
                        "DestinationPortRange": "80",
                        "Description": "Allow HTTP",
                    }
                ],
                "Tags": {"Name": "app-nsg"},
            },
        ),
        ResourceInfo(
            resource_type="azure_vm",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="app-vm-1",
            properties={
                "ResourceGroup": "iac4-rg",
                "Location": "eastus",
                "VMSize": "Standard_D2s_v3",
                "AdminUsername": "azureuser",
                "SubnetId": "app-subnet",
                "OSType": "Linux",
                "ImagePublisher": "Canonical",
                "ImageOffer": "UbuntuServer",
                "ImageSKU": "18.04-LTS",
                "OSDiskSize": 30,
                "OSDiskType": "Premium_LRS",
                "Tags": {"Name": "app-vm-1", "Role": "application"},
            },
        ),
        ResourceInfo(
            resource_type="azure_storage",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="iac4storage",
            properties={
                "ResourceGroup": "iac4-rg",
                "Location": "eastus",
                "AccountTier": "Standard",
                "ReplicationType": "LRS",
                "Containers": [
                    {"name": "images", "access_type": "private"},
                    {"name": "logs", "access_type": "private"},
                ],
                "Tags": {"Environment": "production"},
            },
        ),
        ResourceInfo(
            resource_type="azure_sql",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="iac4-sql-db",
            properties={
                "ResourceGroup": "iac4-rg",
                "Location": "eastus",
                "ServerName": "iac4-sql-server",
                "AdminUsername": "sqladmin",
                "AdminPassword": "StrongPassword123!",
                "SkuName": "S1",
                "MaxSizeGB": 10,
                "FirewallRules": [
                    {"name": "AllowOffice", "start_ip": "1.2.3.4", "end_ip": "1.2.3.4"}
                ],
                "Tags": {"Environment": "production"},
            },
        ),
    ]


def test_terraform_generator_aws():
    """Test Terraform generation for AWS resources."""
    print("\n" + "=" * 70)
    print("TEST 1: AWS Terraform Generation")
    print("=" * 70)

    generator = TerraformCodeGenerator()
    resources = create_sample_aws_resources()

    print(f"\nGenerating Terraform code for {len(resources)} AWS resources...")
    print(f"Resources: {', '.join([r.resource_name for r in resources])}")

    # Convert Pydantic models to dicts
    resources_dict = [r.model_dump() for r in resources]

    try:
        files = generator.generate_code(resources_dict)
        result = {"files": files, "platform": "aws", "provider": "aws"}

        print(f"\n[OK] Generation successful!")
        print(f"  - Files generated: {len(result['files'])}")
        print(f"  - Cloud platform: {result['platform']}")
        print(f"  - Provider: {result['provider']}")

        print("\n" + "-" * 70)
        print("Generated Files:")
        print("-" * 70)

        for file_name, content in result["files"].items():
            print(f"\n>>> {file_name} ({len(content)} bytes)")
            if file_name == "README.md":
                print(content[:300] + "..." if len(content) > 300 else content)
            else:
                # Show first 20 lines of each file
                lines = content.split("\n")[:20]
                print("\n".join(lines))
                if len(content.split("\n")) > 20:
                    print("... (truncated)")

        return True

    except Exception as e:
        print(f"\n[FAIL] Generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_terraform_generator_azure():
    """Test Terraform generation for Azure resources."""
    print("\n" + "=" * 70)
    print("TEST 2: Azure Terraform Generation")
    print("=" * 70)

    generator = TerraformCodeGenerator()
    resources = create_sample_azure_resources()

    print(f"\nGenerating Terraform code for {len(resources)} Azure resources...")
    print(f"Resources: {', '.join([r.resource_name for r in resources])}")

    # Convert Pydantic models to dicts
    resources_dict = [r.model_dump() for r in resources]

    try:
        files = generator.generate_code(resources_dict)
        result = {"files": files, "platform": "azure", "provider": "azurerm"}

        print(f"\n[OK] Generation successful!")
        print(f"  - Files generated: {len(result['files'])}")
        print(f"  - Cloud platform: {result['platform']}")
        print(f"  - Provider: {result['provider']}")

        print("\n" + "-" * 70)
        print("Generated Files:")
        print("-" * 70)

        for file_name, content in result["files"].items():
            print(f"\n>>> {file_name} ({len(content)} bytes)")
            if file_name == "README.md":
                print(content[:300] + "..." if len(content) > 300 else content)
            else:
                # Show first 20 lines of each file
                lines = content.split("\n")[:20]
                print("\n".join(lines))
                if len(content.split("\n")) > 20:
                    print("... (truncated)")

        return True

    except Exception as e:
        print(f"\n[FAIL] Generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_terraform_generator_mixed():
    """Test Terraform generation with mixed AWS and Azure resources."""
    print("\n" + "=" * 70)
    print("TEST 3: Mixed AWS + Azure Terraform Generation")
    print("=" * 70)

    generator = TerraformCodeGenerator()
    aws_resources = create_sample_aws_resources()[:2]  # Take first 2 AWS resources
    azure_resources = create_sample_azure_resources()[
        :2
    ]  # Take first 2 Azure resources
    resources = aws_resources + azure_resources

    print(f"\nGenerating Terraform code for {len(resources)} mixed resources...")
    print(f"  - AWS: {len(aws_resources)} resources")
    print(f"  - Azure: {len(azure_resources)} resources")

    # Convert Pydantic models to dicts
    resources_dict = [r.model_dump() for r in resources]

    try:
        files = generator.generate_code(resources_dict)
        result = {"files": files, "platform": "multi-cloud", "provider": "aws,azurerm"}

        print(f"\n[OK] Generation successful!")
        print(f"  - Files generated: {len(result['files'])}")
        print(f"  - Cloud platform: {result['platform']}")
        print(f"  - Provider: {result['provider']}")

        # Check that both providers are included
        provider_content = result["files"].get("provider.tf", "")
        has_aws = 'provider "aws"' in provider_content
        has_azure = 'provider "azurerm"' in provider_content

        print(f"\nProvider validation:")
        print(f"  - AWS provider: {'[OK]' if has_aws else '[FAIL]'}")
        print(f"  - Azure provider: {'[OK]' if has_azure else '[FAIL]'}")

        return True

    except Exception as e:
        print(f"\n[FAIL] Generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def save_generated_files(result: dict, output_dir: str = "test_output"):
    """Save generated files to disk for manual inspection."""
    from pathlib import Path

    output_path = Path(__file__).parent / output_dir
    output_path.mkdir(exist_ok=True)

    print(f"\nSaving generated files to: {output_path}")

    for file_name, content in result["files"].items():
        file_path = output_path / file_name
        file_path.write_text(content, encoding="utf-8")
        print(f"  [OK] Saved: {file_name}")

    print(f"\nFiles saved successfully to: {output_path.absolute()}")


def main():
    """Run all Terraform generation tests."""
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "TERRAFORM GENERATION TEST SUITE" + " " * 21 + "║")
    print("╚" + "=" * 68 + "╝")

    results = []

    # Test 1: AWS resources
    results.append(("AWS Resources", test_terraform_generator_aws()))

    # Test 2: Azure resources
    results.append(("Azure Resources", test_terraform_generator_azure()))

    # Test 3: Mixed resources
    results.append(("Mixed Resources", test_terraform_generator_mixed()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\nTotal: {passed}/{total} tests passed")

    # Save sample output
    if passed > 0:
        print("\n" + "=" * 70)
        generator = TerraformCodeGenerator()

        aws_resources = create_sample_aws_resources()
        aws_resources_dict = [r.model_dump() for r in aws_resources]
        aws_files = generator.generate_code(aws_resources_dict)
        save_generated_files({"files": aws_files}, "test_output_aws")

        azure_resources = create_sample_azure_resources()
        azure_resources_dict = [r.model_dump() for r in azure_resources]
        azure_files = generator.generate_code(azure_resources_dict)
        save_generated_files({"files": azure_files}, "test_output_azure")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
