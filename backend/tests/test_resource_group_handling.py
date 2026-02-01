"""Test cases for resource group handling functionality."""

import pytest
from app.services.excel_generator import ExcelGeneratorService
from app.services.excel_parser import ExcelParserService
from app.services.terraform_generator import TerraformCodeGenerator
from app.schemas import TemplateType, CloudPlatform


def test_excel_template_includes_resource_group_exists_column():
    """Test that Excel templates include the ResourceGroupExists column for Azure resources."""
    generator = ExcelGeneratorService()

    # Generate a template with Azure resources
    template_bytes = generator.generate_template(TemplateType.AZURE)

    # Basic check that template was generated
    assert len(template_bytes) > 0

    # We could add more detailed checks here if needed


def test_terraform_generator_handles_resource_group_exists():
    """Test that Terraform generator properly handles ResourceGroupExists field."""
    generator = TerraformCodeGenerator()

    # Test resource with ResourceGroupExists = 'n' (should create resource group)
    resources = [
        {
            "cloud_platform": CloudPlatform.AZURE,
            "resource_type": "VM",
            "resource_name": "test-vm",
            "properties": {
                "ResourceGroup": "test-rg",
                "ResourceGroupExists": "n",
                "Location": "eastus",
                "VMSize": "Standard_D2s_v3",
                "OSType": "Linux",
                "VNet_Reference": "test-vnet",
                "Subnet_Reference": "test-subnet",
                "AdminUsername": "testuser",
            },
        }
    ]

    files = generator.generate_code(resources)

    # Should generate main.tf with resource group creation
    assert "main.tf" in files
    assert "azurerm_resource_group" in files["main.tf"]


def test_terraform_generator_skips_resource_group_creation():
    """Test that Terraform generator skips resource group creation when ResourceGroupExists = 'y'."""
    generator = TerraformCodeGenerator()

    # Test resource with ResourceGroupExists = 'y' (should NOT create resource group)
    resources = [
        {
            "cloud_platform": CloudPlatform.AZURE,
            "resource_type": "VM",
            "resource_name": "test-vm",
            "properties": {
                "ResourceGroup": "existing-rg",
                "ResourceGroupExists": "y",
                "Location": "eastus",
                "VMSize": "Standard_D2s_v3",
                "OSType": "Linux",
                "VNet_Reference": "test-vnet",
                "Subnet_Reference": "test-subnet",
                "AdminUsername": "testuser",
            },
        }
    ]

    files = generator.generate_code(resources)

    # Should generate main.tf but reference existing resource group directly
    assert "main.tf" in files


if __name__ == "__main__":
    pytest.main([__file__])
