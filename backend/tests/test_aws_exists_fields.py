"""Test cases for AWS Exists fields validation."""

import pytest
from app.services.excel_parser import ExcelParserService
from app.schemas import ResourceInfo, CloudPlatform


def test_aws_ec2_validation_with_valid_exists_fields():
    """Test that AWS EC2 validates correctly with valid Exists fields."""
    parser = ExcelParserService()

    resource = ResourceInfo(
        resource_type="EC2",
        cloud_platform=CloudPlatform.AWS,
        resource_name="web-server-01",
        properties={
            "ResourceName": "web-server-01",  # This is what gets validated
            "Region": "us-east-1",
            "InstanceType": "t3.medium",
            "AMI_ID": "ami-0c55b159cbfafe1f0",
            "VPC": "main-vpc",
            "VPCExists": "n",
            "Subnet": "public-subnet-1",
            "SubnetExists": "n",
            "SecurityGroups": "web-sg",
            "SecurityGroupsExist": "n",
            "KeyPairName": "my-keypair",
            "Environment": "test",
            "Project": "test-project",
        },
    )

    is_valid, errors = parser.validate_resource(resource)

    # Should be valid with no errors
    assert is_valid
    assert len(errors) == 0


def test_aws_ec2_validation_with_invalid_exists_fields():
    """Test that AWS EC2 validation fails with invalid Exists fields."""
    parser = ExcelParserService()

    resource = ResourceInfo(
        resource_type="EC2",
        cloud_platform=CloudPlatform.AWS,
        resource_name="web-server-01",
        properties={
            "ResourceName": "web-server-01",  # This is what gets validated
            "Region": "us-east-1",
            "InstanceType": "t3.medium",
            "AMI_ID": "ami-0c55b159cbfafe1f0",
            "VPC": "main-vpc",
            "VPCExists": "invalid",  # Invalid value
            "Subnet": "public-subnet-1",
            "SubnetExists": "no",  # Invalid value
            "SecurityGroups": "web-sg",
            "SecurityGroupsExist": "n",
            "KeyPairName": "my-keypair",
            "Environment": "test",
            "Project": "test-project",
        },
    )

    is_valid, errors = parser.validate_resource(resource)

    # Should be invalid with errors
    assert not is_valid
    # Check for Exists field errors specifically
    exists_errors = [error for error in errors if "Exists" in error]
    assert len(exists_errors) == 2
    assert "VPCExists must be 'y' or 'n'" in exists_errors
    assert "SubnetExists must be 'y' or 'n'" in exists_errors


def test_aws_subnet_validation_with_valid_exists_fields():
    """Test that AWS Subnet validates correctly with valid Exists fields."""
    parser = ExcelParserService()

    resource = ResourceInfo(
        resource_type="Subnet",
        cloud_platform=CloudPlatform.AWS,
        resource_name="public-subnet-1",
        properties={
            "ResourceName": "public-subnet-1",  # This is what gets validated
            "VPC": "main-vpc",
            "VPCExists": "n",
            "AvailabilityZone": "us-east-1a",
            "CIDR_Block": "10.0.1.0/24",
            "Environment": "test",
            "Project": "test-project",
        },
    )

    is_valid, errors = parser.validate_resource(resource)

    # Should be valid with no errors
    assert is_valid
    assert len(errors) == 0


def test_aws_security_group_validation_with_invalid_exists_fields():
    """Test that AWS Security Group validation fails with invalid Exists fields."""
    parser = ExcelParserService()

    resource = ResourceInfo(
        resource_type="SecurityGroup",
        cloud_platform=CloudPlatform.AWS,
        resource_name="web-sg",
        properties={
            "ResourceName": "web-sg",  # This is what gets validated
            "VPC": "main-vpc",
            "VPCExists": "sometimes",  # Invalid value
            "Description": "Test security group",
            "IngressRules": "[]",
            "Environment": "test",
            "Project": "test-project",
        },
    )

    is_valid, errors = parser.validate_resource(resource)

    # Should be invalid with errors
    assert not is_valid
    # Check for Exists field errors specifically
    exists_errors = [error for error in errors if "Exists" in error]
    assert len(exists_errors) == 1
    assert "VPCExists must be 'y' or 'n'" in exists_errors


if __name__ == "__main__":
    pytest.main([__file__])
