"""Test Azure Terraform validator functionality."""

import pytest
from app.services.azure_validator import AzureTerraformValidator


def test_sanitize_subnet_with_tags():
    """Test that tags are removed from azurerm_subnet."""
    code_with_tags = """resource "azurerm_subnet" "web_subnet" {
  name                 = "web-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]

  tags = {
    Name        = "web-subnet"
    Environment = "prod"
  }
}"""

    sanitized, issues = AzureTerraformValidator.validate_and_fix_main_tf(code_with_tags)

    # Tags should be removed
    assert "tags" not in sanitized
    assert "Name" not in sanitized
    assert "web-subnet" in sanitized  # Resource name should remain
    assert "address_prefixes" in sanitized  # Other properties should remain
    assert len(issues) == 1  # One issue fixed


def test_sanitize_vnet_keeps_tags():
    """Test that tags are preserved for resources that support them."""
    code_with_tags = """resource "azurerm_virtual_network" "main" {
  name                = "main-vnet"
  location            = "eastus"
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = ["10.0.0.0/16"]

  tags = {
    Environment = "prod"
  }
}"""

    sanitized, issues = AzureTerraformValidator.validate_and_fix_main_tf(code_with_tags)

    # Tags should be preserved for VNet (no issues fixed)
    assert "tags" in sanitized
    assert "Environment" in sanitized
    assert len(issues) == 0  # No issues - vnet supports tags


def test_validate_and_fix_main_tf():
    """Test validation and fixing of main.tf with multiple resources."""
    main_tf = """# Terraform configuration

resource "azurerm_resource_group" "rg" {
  name     = "my-rg"
  location = "eastus"

  tags = {
    Environment = "prod"
  }
}

resource "azurerm_virtual_network" "vnet" {
  name                = "main-vnet"
  location            = "eastus"
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = ["10.0.0.0/16"]

  tags = {
    Environment = "prod"
  }
}

resource "azurerm_subnet" "web" {
  name                 = "web-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]

  tags = {
    Name = "web-subnet"
  }
}

resource "azurerm_network_security_group" "nsg" {
  name                = "web-nsg"
  location            = "eastus"
  resource_group_name = azurerm_resource_group.rg.name

  tags = {
    Purpose = "WebServer"
  }
}
"""

    fixed_content, issues = AzureTerraformValidator.validate_and_fix_main_tf(main_tf)

    # Should fix exactly 1 issue (subnet tags)
    assert len(issues) == 1
    assert "azurerm_subnet.web" in issues[0]

    # Resource group tags should be preserved
    assert 'resource "azurerm_resource_group"' in fixed_content
    # VNet tags should be preserved
    assert 'resource "azurerm_virtual_network"' in fixed_content
    # NSG tags should be preserved
    assert 'resource "azurerm_network_security_group"' in fixed_content

    # Subnet should NOT have tags
    subnet_start = fixed_content.find('resource "azurerm_subnet"')
    subnet_end = fixed_content.find('resource "azurerm_network_security_group"')
    subnet_block = fixed_content[subnet_start:subnet_end]
    assert "tags" not in subnet_block


def test_validate_generated_files():
    """Test validation of a complete file set."""
    files = {
        "provider.tf": 'provider "azurerm" { features {} }',
        "variables.tf": 'variable "location" { type = string }',
        "main.tf": """
resource "azurerm_subnet" "test" {
  name = "test-subnet"
  
  tags = {
    Name = "test"
  }
}
""",
    }

    fixed_files = AzureTerraformValidator.validate_generated_files(files)

    # main.tf should be fixed
    assert "tags" not in fixed_files["main.tf"]
    # Other files should be unchanged
    assert fixed_files["provider.tf"] == files["provider.tf"]
    assert fixed_files["variables.tf"] == files["variables.tf"]


def test_no_tags_resources_list():
    """Verify the list of resources that don't support tags."""
    assert "azurerm_subnet" in AzureTerraformValidator.NO_TAGS_RESOURCES
    assert (
        "azurerm_subnet_network_security_group_association"
        in AzureTerraformValidator.NO_TAGS_RESOURCES
    )


def test_tags_supported_resources_list():
    """Verify the list of resources that support tags."""
    assert "azurerm_virtual_network" in AzureTerraformValidator.TAGS_SUPPORTED_RESOURCES
    assert (
        "azurerm_network_security_group"
        in AzureTerraformValidator.TAGS_SUPPORTED_RESOURCES
    )
    assert "azurerm_resource_group" in AzureTerraformValidator.TAGS_SUPPORTED_RESOURCES


def test_remove_unsupported_backend_address_ip_configurations_from_lb_pool():
    """Validator should strip unsupported backend_address_ip_configurations blocks."""
    main_tf = """
resource "azurerm_lb_backend_address_pool" "lb_web_backend" {
  loadbalancer_id = azurerm_lb.lb_web.id
  name            = "web-backend-pool"

  backend_address_ip_configurations {
    name      = "web01"
    ip_address = "10.0.1.4"
  }

  backend_address_ip_configurations {
    name      = "web02"
    ip_address = "10.0.1.5"
  }
}
"""
    fixed_content, issues = AzureTerraformValidator.validate_and_fix_main_tf(main_tf)

    assert "backend_address_ip_configurations" not in fixed_content
    assert 'resource "azurerm_lb_backend_address_pool" "lb_web_backend"' in fixed_content
    assert any("backend_address_ip_configurations" in issue for issue in issues)


def test_remove_sql_vnet_rule_when_public_network_access_disabled():
    """Validator should remove SQL VNet rules if SQL server public access is disabled."""
    main_tf = """
resource "azurerm_mssql_server" "sqldb_app_server" {
  name                         = "sqlsrvdemo3tier"
  resource_group_name          = azurerm_resource_group.rg_demo.name
  location                     = "westus3"
  version                      = "12.0"
  administrator_login          = "sqladminuser"
  administrator_login_password = "Password123!"
  minimum_tls_version          = "1.2"
  public_network_access_enabled = false
}

resource "azurerm_mssql_virtual_network_rule" "sqldb_app_vnet_rule_1" {
  name      = "sql-vnet-rule"
  server_id = azurerm_mssql_server.sqldb_app_server.id
  subnet_id = azurerm_subnet.subnet_db.id
}
"""
    fixed_content, issues = AzureTerraformValidator.validate_and_fix_main_tf(main_tf)

    assert 'resource "azurerm_mssql_server" "sqldb_app_server"' in fixed_content
    assert 'resource "azurerm_mssql_virtual_network_rule" "sqldb_app_vnet_rule_1"' not in fixed_content
    assert any("Removed azurerm_mssql_virtual_network_rule.sqldb_app_vnet_rule_1" in issue for issue in issues)


def test_remove_sql_vulnerability_assessment_when_storage_fields_empty():
    """Validator should remove SQL vulnerability assessment with empty required fields."""
    main_tf = """
resource "azurerm_mssql_server_vulnerability_assessment" "sqldb_app_stg_vulnerability" {
  server_security_alert_policy_id = azurerm_mssql_server_security_alert_policy.sqldb_app_stg_security_alert.id
  storage_container_path          = ""
  storage_account_access_key      = ""
  recurring_scans {
    enabled = true
  }
}
"""
    fixed_content, issues = AzureTerraformValidator.validate_and_fix_main_tf(main_tf)

    assert 'resource "azurerm_mssql_server_vulnerability_assessment" "sqldb_app_stg_vulnerability"' not in fixed_content
    assert any(
        "Removed azurerm_mssql_server_vulnerability_assessment.sqldb_app_stg_vulnerability"
        in issue
        for issue in issues
    )
