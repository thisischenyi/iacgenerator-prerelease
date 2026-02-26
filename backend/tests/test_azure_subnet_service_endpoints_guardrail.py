"""Tests for Azure subnet ServiceEndpoints SQL guardrail."""

import io

from openpyxl import Workbook

from app.services.excel_parser import ExcelParserService


def _build_excel_bytes(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Azure_Subnet"
    ws.append(
        [
            "ResourceName",
            "Environment",
            "Project",
            "ResourceGroup",
            "ResourceGroupExists",
            "VNet",
            "VNetExists",
            "AddressPrefix",
            "ServiceEndpoints",
        ]
    )
    for row in rows:
        ws.append(row)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_sql_service_endpoints_are_normalized_with_warning():
    parser = ExcelParserService()
    content = _build_excel_bytes(
        [
            [
                "subnet-db",
                "Production",
                "Demo",
                "rg-demo",
                "n",
                "vnet-demo",
                "n",
                "10.20.3.0/24",
                "Microsoft.Storage,Microsoft.Sql/servers,Microsoft.Sql",
            ]
        ]
    )

    result = parser.parse_excel_file(content)
    assert result.success is True
    assert result.resource_count == 1
    assert result.warnings is not None
    assert any("Removed unsupported SQL ServiceEndpoints values" in w for w in result.warnings)
    assert not any(
        "Mapped invalid SQL ServiceEndpoints values to 'Microsoft.Sql'" in w
        for w in result.warnings
    )

    subnet = result.resources[0]
    assert subnet.properties.get("ServiceEndpoints") == [
        "Microsoft.Storage",
        "Microsoft.Sql",
    ]


def test_service_endpoints_mapped_to_sql_if_only_invalid_sql_values():
    parser = ExcelParserService()
    content = _build_excel_bytes(
        [
            [
                "subnet-db",
                "Production",
                "Demo",
                "rg-demo",
                "n",
                "vnet-demo",
                "n",
                "10.20.3.0/24",
                "Microsoft.Sql/servers,Microsoft.Sql",
            ]
        ]
    )

    result = parser.parse_excel_file(content)
    assert result.success is True
    subnet = result.resources[0]
    assert subnet.properties.get("ServiceEndpoints") == ["Microsoft.Sql"]
