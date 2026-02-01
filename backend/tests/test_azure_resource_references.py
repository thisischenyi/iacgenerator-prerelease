"""Test cases for Azure resource reference handling functionality."""

import pytest
from app.services.terraform_generator import TerraformCodeGenerator
from app.schemas import CloudPlatform


def test_azure_vm_with_new_resource_references():
    """Test that Azure VM creates references to new resources when Exists=n."""
    generator = TerraformCodeGenerator()

    # Test VM with new resource references (Exists=n)
    resources = [
        {
            "cloud_platform": CloudPlatform.AZURE,
            "resource_type": "VM",
            "resource_name": "test-vm",
            "properties": {
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
            },
        }
    ]

    files = generator.generate_code(resources)

    # Should generate main.tf with template resource references
    assert "main.tf" in files
    assert "azurerm_subnet.test_subnet.id" in files["main.tf"]
    assert "azurerm_network_security_group.test_nsg.id" in files["main.tf"]


def test_azure_vm_with_existing_resource_references():
    """Test that Azure VM references existing resources when Exists=y."""
    generator = TerraformCodeGenerator()

    # Test VM with existing resource references (Exists=y)
    resources = [
        {
            "cloud_platform": CloudPlatform.AZURE,
            "resource_type": "VM",
            "resource_name": "test-vm",
            "properties": {
                "ResourceGroup": "test-rg",
                "ResourceGroupExists": "y",  # Existing resource group
                "VNet": "my-existing-vnet",
                "VNetExists": "y",  # Existing VNet
                "Subnet": "my-existing-subnet",
                "SubnetExists": "y",  # Existing Subnet
                "NSG": "my-existing-nsg",
                "NSGExists": "y",  # Existing NSG
                "Location": "eastus",
                "VMSize": "Standard_D2s_v3",
                "OSType": "Linux",
                "AdminUsername": "testuser",
            },
        }
    ]

    files = generator.generate_code(resources)

    # Should generate main.tf with direct resource references
    assert "main.tf" in files
    assert '"my-existing-subnet"' in files["main.tf"]
    assert '"my-existing-nsg"' in files["main.tf"]
    assert "azurerm_subnet." not in files["main.tf"]
    assert "azurerm_network_security_group." not in files["main.tf"]


def test_azure_subnet_with_mixed_resource_references():
    """Test that Azure Subnet can mix existing and new resource references."""
    generator = TerraformCodeGenerator()

    # Test Subnet with existing VNet reference
    resources = [
        {
            "cloud_platform": CloudPlatform.AZURE,
            "resource_type": "Subnet",
            "resource_name": "test-subnet",
            "properties": {
                "ResourceGroup": "test-rg",
                "ResourceGroupExists": "n",
                "VNet": "existing-vnet-name",
                "VNetExists": "y",  # Existing VNet
                "AddressPrefix": "10.0.1.0/24",
            },
        }
    ]

    files = generator.generate_code(resources)

    # Should generate main.tf with direct VNet reference
    assert "main.tf" in files
    assert (
        '"existing-vnet-name"' in files["main.tf"]
    )  # Direct reference to existing VNet
    assert (
        "azurerm_virtual_network." not in files["main.tf"]
    )  # Should not reference azurerm_virtual_network


def test_azure_subnet_in_existing_rg_and_existing_vnet():
    """Test that Azure Subnet can be created in existing RG and VNet."""
    generator = TerraformCodeGenerator()

    # Test Subnet in existing RG and existing VNet
    resources = [
        {
            "cloud_platform": CloudPlatform.AZURE,
            "resource_type": "Subnet",
            "resource_name": "new-subnet",
            "properties": {
                "ResourceGroup": "existing-rg",
                "ResourceGroupExists": "y",  # Existing RG
                "VNet": "existing-vnet",
                "VNetExists": "y",  # Existing VNet
                "AddressPrefix": "10.0.2.0/24",
            },
        }
    ]

    files = generator.generate_code(resources)

    # Should generate main.tf with direct references
    assert "main.tf" in files
    # Should NOT create a new Resource Group
    assert 'resource "azurerm_resource_group"' not in files["main.tf"]
    # Should reference existing RG directly as string
    assert '"existing-rg"' in files["main.tf"]
    # Should reference existing VNet directly as string
    assert '"existing-vnet"' in files["main.tf"]


def test_azure_nsg_in_existing_rg():
    """Test that Azure NSG can be created in existing Resource Group."""
    generator = TerraformCodeGenerator()

    resources = [
        {
            "cloud_platform": CloudPlatform.AZURE,
            "resource_type": "NSG",
            "resource_name": "new-nsg",
            "properties": {
                "ResourceGroup": "existing-rg",
                "ResourceGroupExists": "y",  # Existing RG
                "Location": "eastus",
                "SecurityRules": [
                    {
                        "name": "allow-https",
                        "priority": 100,
                        "direction": "Inbound",
                        "access": "Allow",
                        "protocol": "Tcp",
                        "source_port_range": "*",
                        "destination_port_range": "443",
                        "source_address_prefix": "*",
                        "destination_address_prefix": "*",
                    }
                ],
            },
        }
    ]

    files = generator.generate_code(resources)

    # Should generate main.tf with direct RG reference
    assert "main.tf" in files
    # Should NOT create a new Resource Group
    assert 'resource "azurerm_resource_group"' not in files["main.tf"]
    # Should have NSG resource
    assert 'resource "azurerm_network_security_group"' in files["main.tf"]
    # Should reference existing RG directly
    assert '"existing-rg"' in files["main.tf"]


def test_azure_vnet_in_existing_rg():
    """Test that Azure VNet can be created in existing Resource Group."""
    generator = TerraformCodeGenerator()

    resources = [
        {
            "cloud_platform": CloudPlatform.AZURE,
            "resource_type": "VNet",
            "resource_name": "new-vnet",
            "properties": {
                "ResourceGroup": "existing-rg",
                "ResourceGroupExists": "y",  # Existing RG
                "Location": "eastus",
                "AddressSpace": ["10.1.0.0/16"],
            },
        }
    ]

    files = generator.generate_code(resources)

    # Should generate main.tf with direct RG reference
    assert "main.tf" in files
    # Should NOT create a new Resource Group
    assert 'resource "azurerm_resource_group"' not in files["main.tf"]
    # Should have VNet resource
    assert 'resource "azurerm_virtual_network"' in files["main.tf"]
    # Should reference existing RG directly
    assert '"existing-rg"' in files["main.tf"]


if __name__ == "__main__":
    pytest.main([__file__])
