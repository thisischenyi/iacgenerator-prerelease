"""Test cases for Azure Exists fields validation."""

import pytest
from app.services.excel_parser import ExcelParserService
from app.schemas import ResourceInfo, CloudPlatform


def test_azure_vm_validation_with_valid_exists_fields():
    """Test that Azure VM validates correctly with valid Exists fields."""
    parser = ExcelParserService()

    resource = ResourceInfo(
        resource_type="VM",
        cloud_platform=CloudPlatform.AZURE,
        resource_name="test-vm",
        properties={
            "ResourceName": "test-vm",  # This is what gets validated
            "ResourceGroup": "test-rg",
            "ResourceGroupExists": "n",
            "VNet": "test-vnet",
            "VNetExists": "n",
            "Subnet": "test-subnet",
            "SubnetExists": "n",
            "NSG": "test-nsg",
            "NSGExists": "n",
            "Location": "eastus",
            "VMSize": "Standard_D2s_v3",
            "OSType": "Linux",
            "AdminUsername": "testuser",
            "Environment": "test",
            "Project": "test-project",
        },
    )

    is_valid, errors = parser.validate_resource(resource)

    # Should be valid with no errors
    assert is_valid
    assert len(errors) == 0


def test_azure_vm_validation_with_invalid_exists_fields():
    """Test that Azure VM validation fails with invalid Exists fields."""
    parser = ExcelParserService()

    resource = ResourceInfo(
        resource_type="VM",
        cloud_platform=CloudPlatform.AZURE,
        resource_name="test-vm",
        properties={
            "ResourceName": "test-vm",  # This is what gets validated
            "ResourceGroup": "test-rg",
            "ResourceGroupExists": "invalid",  # Invalid value
            "VNet": "test-vnet",
            "VNetExists": "maybe",  # Invalid value
            "Subnet": "test-subnet",
            "SubnetExists": "n",
            "NSG": "test-nsg",
            "NSGExists": "n",
            "Location": "eastus",
            "VMSize": "Standard_D2s_v3",
            "OSType": "Linux",
            "AdminUsername": "testuser",
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
    assert "ResourceGroupExists must be 'y' or 'n'" in exists_errors
    assert "VNetExists must be 'y' or 'n'" in exists_errors


def test_azure_subnet_validation_with_valid_exists_fields():
    """Test that Azure Subnet validates correctly with valid Exists fields."""
    parser = ExcelParserService()

    resource = ResourceInfo(
        resource_type="Subnet",
        cloud_platform=CloudPlatform.AZURE,
        resource_name="test-subnet",
        properties={
            "ResourceName": "test-subnet",  # This is what gets validated
            "ResourceGroup": "test-rg",
            "ResourceGroupExists": "n",
            "VNet": "test-vnet",
            "VNetExists": "n",
            "AddressPrefix": "10.0.1.0/24",
            "Environment": "test",
            "Project": "test-project",
        },
    )

    is_valid, errors = parser.validate_resource(resource)

    # Should be valid with no errors
    assert is_valid
    assert len(errors) == 0


def test_azure_subnet_validation_with_existing_rg_and_vnet():
    """Test that Azure Subnet validates correctly when using existing RG and VNet."""
    parser = ExcelParserService()

    resource = ResourceInfo(
        resource_type="Subnet",
        cloud_platform=CloudPlatform.AZURE,
        resource_name="test-subnet",
        properties={
            "ResourceName": "test-subnet",
            "ResourceGroup": "existing-rg",
            "ResourceGroupExists": "y",  # Existing RG
            "VNet": "existing-vnet",
            "VNetExists": "y",  # Existing VNet
            "AddressPrefix": "10.0.2.0/24",
            "Environment": "test",
            "Project": "test-project",
        },
    )

    is_valid, errors = parser.validate_resource(resource)

    # Should be valid with no errors
    assert is_valid
    assert len(errors) == 0


def test_azure_subnet_validation_with_invalid_exists_fields():
    """Test that Azure Subnet validation fails with invalid Exists fields."""
    parser = ExcelParserService()

    resource = ResourceInfo(
        resource_type="Subnet",
        cloud_platform=CloudPlatform.AZURE,
        resource_name="test-subnet",
        properties={
            "ResourceName": "test-subnet",  # This is what gets validated
            "ResourceGroup": "test-rg",
            "ResourceGroupExists": "invalid",  # Invalid value
            "VNet": "test-vnet",
            "VNetExists": "sometimes",  # Invalid value
            "AddressPrefix": "10.0.1.0/24",
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
    assert "ResourceGroupExists must be 'y' or 'n'" in exists_errors
    assert "VNetExists must be 'y' or 'n'" in exists_errors


if __name__ == "__main__":
    pytest.main([__file__])
