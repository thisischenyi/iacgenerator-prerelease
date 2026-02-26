"""Tests for Azure SQL guardrail normalization in Excel parser."""

import io

from openpyxl import Workbook

from app.services.excel_parser import ExcelParserService


def _build_sql_excel_bytes(row):
    wb = Workbook()
    ws = wb.active
    ws.title = "Azure_SQL"
    ws.append(
        [
            "ResourceName",
            "Environment",
            "Project",
            "ResourceGroup",
            "ResourceGroupExists",
            "Location",
            "ServerName",
            "ServerAdminLogin",
            "DatabaseEdition",
            "VNet",
            "VNetExists",
            "Subnet",
            "SubnetExists",
            "PublicNetworkAccess",
            "VirtualNetworkRules",
            "FirewallRules",
            "AuditingEnabled",
            "AuditingStorageEndpoint",
        ]
    )
    ws.append(row)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_sql_rules_removed_when_public_network_disabled():
    parser = ExcelParserService()
    content = _build_sql_excel_bytes(
        [
            "sqldb-app",
            "Production",
            "Demo",
            "rg-demo",
            "n",
            "westus3",
            "sqlsrvdemo",
            "sqladmin",
            "Standard",
            "vnet-demo",
            "n",
            "subnet-db",
            "n",
            "Disabled",
            '[{"name":"allow-db-subnet"}]',
            '[{"name":"AllowAzureServices","start_ip":"0.0.0.0","end_ip":"0.0.0.0"}]',
            "false",
            "",
        ]
    )

    result = parser.parse_excel_file(content)
    assert result.success is True
    sql = result.resources[0]
    assert "VirtualNetworkRules" not in sql.properties
    assert "FirewallRules" not in sql.properties
    assert result.warnings is not None
    assert any("Removed VirtualNetworkRules" in w for w in result.warnings)
    assert any("Removed FirewallRules" in w for w in result.warnings)


def test_sql_auditing_disabled_without_valid_blob_endpoint():
    parser = ExcelParserService()
    content = _build_sql_excel_bytes(
        [
            "sqldb-app",
            "Production",
            "Demo",
            "rg-demo",
            "n",
            "westus3",
            "sqlsrvdemo",
            "sqladmin",
            "Standard",
            "vnet-demo",
            "n",
            "subnet-db",
            "n",
            "Enabled",
            "",
            "",
            "true",
            "not-a-blob-endpoint",
        ]
    )

    result = parser.parse_excel_file(content)
    assert result.success is True
    sql = result.resources[0]
    assert str(sql.properties.get("AuditingEnabled")).lower() == "false"
    assert result.warnings is not None
    assert any("Disabled AuditingEnabled" in w for w in result.warnings)

