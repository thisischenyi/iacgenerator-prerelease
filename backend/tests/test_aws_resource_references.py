"""Test cases for AWS resource reference handling functionality."""

import pytest
from app.services.terraform_generator import TerraformCodeGenerator
from app.schemas import CloudPlatform


def test_aws_ec2_with_new_resource_references():
    """Test that AWS EC2 creates references to new resources when Exists=n."""
    generator = TerraformCodeGenerator()

    # Test EC2 with new resource references (Exists=n)
    resources = [
        {
            "cloud_platform": CloudPlatform.AWS,
            "resource_type": "EC2",
            "resource_name": "web-server-01",
            "properties": {
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
            },
        }
    ]

    files = generator.generate_code(resources)

    # Should generate main.tf with template resource references
    assert "main.tf" in files
    assert "aws_subnet.public_subnet_1.id" in files["main.tf"]
    assert "aws_security_group.web_sg.id" in files["main.tf"]


def test_aws_ec2_with_existing_resource_references():
    """Test that AWS EC2 references existing resources when Exists=y."""
    generator = TerraformCodeGenerator()

    # Test EC2 with existing resource references (Exists=y)
    resources = [
        {
            "cloud_platform": CloudPlatform.AWS,
            "resource_type": "EC2",
            "resource_name": "web-server-01",
            "properties": {
                "Region": "us-east-1",
                "InstanceType": "t3.medium",
                "AMI_ID": "ami-0c55b159cbfafe1f0",
                "VPC": "vpc-12345678",
                "VPCExists": "y",  # Existing VPC
                "Subnet": "subnet-87654321",
                "SubnetExists": "y",  # Existing Subnet
                "SecurityGroups": "sg-11111111",
                "SecurityGroupsExist": "y",  # Existing Security Group
                "KeyPairName": "my-keypair",
            },
        }
    ]

    files = generator.generate_code(resources)

    # Should generate main.tf with direct resource references
    assert "main.tf" in files
    assert '"subnet-87654321"' in files["main.tf"]
    assert '"sg-11111111"' in files["main.tf"]
    assert "aws_subnet." not in files["main.tf"]
    assert "aws_security_group." not in files["main.tf"]


def test_aws_subnet_with_mixed_resource_references():
    """Test that AWS Subnet can mix existing and new resource references."""
    generator = TerraformCodeGenerator()

    # Test Subnet with existing VPC reference
    resources = [
        {
            "cloud_platform": CloudPlatform.AWS,
            "resource_type": "Subnet",
            "resource_name": "public-subnet-1",
            "properties": {
                "VPC": "vpc-12345678",
                "VPCExists": "y",  # Existing VPC
                "CIDR_Block": "10.0.1.0/24",
                "AvailabilityZone": "us-east-1a",
                "MapPublicIP": "true",
            },
        }
    ]

    files = generator.generate_code(resources)

    # Should generate main.tf with direct VPC reference
    assert "main.tf" in files
    assert '"vpc-12345678"' in files["main.tf"]  # Direct reference to existing VPC
    assert "aws_vpc." not in files["main.tf"]  # Should not reference aws_vpc


if __name__ == "__main__":
    pytest.main([__file__])
