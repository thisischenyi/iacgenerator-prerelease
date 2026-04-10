"""Tests for deterministic static checks in code review."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.nodes import AgentNodes


def test_static_review_flags_unsupported_azurerm_resource_type():
    """Static reviewer should catch AzureRM resource types unsupported in v4.x."""
    files = {
        "main.tf": """
resource "azurerm_private_endpoint_private_dns_zone_group" "sql_private_dns_group" {
  private_endpoint_id = azurerm_private_endpoint.sql_pe.id
}
"""
    }

    issues = AgentNodes._run_static_terraform_review(files)

    assert len(issues) == 1
    issue = issues[0]
    assert issue["severity"] == "critical"
    assert issue["file"] == "main.tf"
    assert "azurerm_private_endpoint_private_dns_zone_group" in issue["description"]
    assert "private_dns_zone_group" in issue["suggestion"]


def test_static_review_allows_supported_resource_type():
    """Static reviewer should not report issues for supported resource types."""
    files = {
        "main.tf": """
resource "azurerm_resource_group" "rg_demo" {
  name     = "rg-demo"
  location = "eastus"
}
"""
    }

    issues = AgentNodes._run_static_terraform_review(files)

    assert issues == []


def test_static_review_flags_invalid_sql_subnet_delegation_name():
    """Static reviewer should flag Microsoft.Sql used in subnet delegation."""
    files = {
        "main.tf": """
resource "azurerm_subnet" "subnet_db_stg" {
  name                 = "subnet-db-stg"
  resource_group_name  = azurerm_resource_group.rg_demo.name
  virtual_network_name = azurerm_virtual_network.vnet_demo.name
  address_prefixes     = ["10.20.3.0/24"]

  delegation {
    name = "sql"
    service_delegation {
      name = "Microsoft.Sql"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}
"""
    }

    issues = AgentNodes._run_static_terraform_review(files)

    assert len(issues) == 1
    issue = issues[0]
    assert issue["severity"] == "critical"
    assert "Invalid SQL subnet delegation" in issue["description"]
    assert "service_endpoints = [\"Microsoft.Sql\"]" in issue["suggestion"]


def test_static_review_allows_managed_instance_sql_delegation():
    """Static reviewer should allow SQL Managed Instance delegation values."""
    files = {
        "main.tf": """
resource "azurerm_subnet" "subnet_mi" {
  name                 = "subnet-mi"
  resource_group_name  = azurerm_resource_group.rg_demo.name
  virtual_network_name = azurerm_virtual_network.vnet_demo.name
  address_prefixes     = ["10.20.3.0/24"]

  delegation {
    name = "managed-instance"
    service_delegation {
      name = "Microsoft.Sql/managedInstances"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}
"""
    }

    issues = AgentNodes._run_static_terraform_review(files)

    assert issues == []
