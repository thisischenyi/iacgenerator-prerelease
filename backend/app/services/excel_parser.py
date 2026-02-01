"""Excel parsing service for resource definitions."""

import io
import re
from typing import List, Dict, Any, Optional, Tuple
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.schemas import (
    ResourceInfo,
    ExcelParseResult,
    CloudPlatform,
)


class ExcelParserService:
    """Service for parsing Excel files containing resource definitions."""

    # Supported resource types for each cloud platform
    AWS_RESOURCE_TYPES = [
        "AWS_EC2",
        "AWS_VPC",
        "AWS_Subnet",
        "AWS_SecurityGroup",
        "AWS_S3",
        "AWS_RDS",
    ]

    AZURE_RESOURCE_TYPES = [
        "Azure_VM",
        "Azure_VNet",
        "Azure_Subnet",
        "Azure_NSG",
        "Azure_Storage",
        "Azure_SQL",
    ]

    # Common fields for all resources
    COMMON_FIELDS = [
        "ResourceName",
        "Environment",
        "Project",
        "Owner",
        "CostCenter",
        "Tags",
    ]

    def __init__(self):
        """Initialize Excel parser service."""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse_excel_file(self, file_content: bytes) -> ExcelParseResult:
        """
        Parse Excel file and extract resource definitions.

        Args:
            file_content: Excel file content as bytes

        Returns:
            ExcelParseResult with parsed resources and any errors/warnings
        """
        self.errors = []
        self.warnings = []

        try:
            # Load workbook from bytes
            workbook = load_workbook(io.BytesIO(file_content), data_only=True)

            # Parse all resource sheets
            resources: List[ResourceInfo] = []
            resource_types: List[str] = []

            for sheet_name in workbook.sheetnames:
                # Skip README and other non-resource sheets
                if sheet_name.upper() == "README" or not self._is_resource_sheet(
                    sheet_name
                ):
                    continue

                sheet = workbook[sheet_name]
                cloud_platform = self._get_cloud_platform(sheet_name)

                if not cloud_platform:
                    self.warnings.append(f"Skipping unknown sheet: {sheet_name}")
                    continue

                # Parse resources from this sheet
                sheet_resources = self._parse_resource_sheet(
                    sheet, sheet_name, cloud_platform
                )

                if sheet_resources:
                    resources.extend(sheet_resources)
                    if sheet_name not in resource_types:
                        resource_types.append(sheet_name)

            return ExcelParseResult(
                success=len(self.errors) == 0,
                resource_count=len(resources),
                resource_types=resource_types,
                resources=resources,
                errors=self.errors if self.errors else None,
                warnings=self.warnings if self.warnings else None,
            )

        except Exception as e:
            self.errors.append(f"Failed to parse Excel file: {str(e)}")
            return ExcelParseResult(
                success=False,
                resource_count=0,
                resource_types=[],
                resources=[],
                errors=self.errors,
                warnings=None,
            )

    def _is_resource_sheet(self, sheet_name: str) -> bool:
        """
        Check if sheet name represents a resource type.

        Args:
            sheet_name: Name of the sheet

        Returns:
            True if sheet is a resource sheet
        """
        return (
            sheet_name in self.AWS_RESOURCE_TYPES
            or sheet_name in self.AZURE_RESOURCE_TYPES
        )

    def _get_cloud_platform(self, sheet_name: str) -> Optional[CloudPlatform]:
        """
        Determine cloud platform from sheet name.

        Args:
            sheet_name: Name of the sheet

        Returns:
            CloudPlatform enum or None
        """
        if sheet_name.startswith("AWS_"):
            return CloudPlatform.AWS
        elif sheet_name.startswith("Azure_"):
            return CloudPlatform.AZURE
        return None

    def _parse_resource_sheet(
        self,
        sheet: Worksheet,
        sheet_name: str,
        cloud_platform: CloudPlatform,
    ) -> List[ResourceInfo]:
        """
        Parse a single resource sheet.

        Args:
            sheet: Excel worksheet
            sheet_name: Name of the sheet
            cloud_platform: Cloud platform (AWS or Azure)

        Returns:
            List of parsed resources
        """
        resources: List[ResourceInfo] = []

        # Get header row (first row)
        headers = []
        for cell in sheet[1]:
            if cell.value:
                # Strip asterisks from required field markers
                header = str(cell.value).strip().rstrip("*")
                headers.append(header)
            else:
                headers.append("")

        if not headers:
            self.errors.append(f"Sheet {sheet_name}: No headers found")
            return resources

        # Parse data rows (starting from row 2)
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            # Skip empty rows
            if all(cell.value is None for cell in row):
                continue

            # Build resource properties from row
            properties: Dict[str, Any] = {}
            resource_name: Optional[str] = None

            for col_idx, cell in enumerate(row):
                if col_idx >= len(headers):
                    break

                header = headers[col_idx]
                if not header:
                    continue

                value = cell.value

                # Store ResourceName separately
                if header == "ResourceName":
                    resource_name = str(value) if value else None

                # Store all properties
                if value is not None:
                    properties[header] = self._convert_cell_value(value, header)

            # Validate and create resource
            if resource_name:
                # Extract resource type from sheet name
                resource_type = (
                    sheet_name.split("_", 1)[1] if "_" in sheet_name else sheet_name
                )

                # Merge metadata columns (Environment, Project, Owner, CostCenter) into Tags
                # This ensures compliance checks can validate these as tags
                self._merge_metadata_to_tags(properties)

                resource = ResourceInfo(
                    resource_type=resource_type,
                    cloud_platform=cloud_platform,
                    resource_name=resource_name,
                    properties=properties,
                )
                resources.append(resource)
            else:
                self.warnings.append(
                    f"Sheet {sheet_name}, Row {row_idx}: Missing ResourceName, skipping row"
                )

        return resources

    def _convert_cell_value(self, value: Any, header: str) -> Any:
        """
        Convert cell value to appropriate Python type.

        Args:
            value: Cell value
            header: Column header name

        Returns:
            Converted value
        """
        # Handle None
        if value is None:
            return None

        # Convert to string first
        str_value = str(value).strip()

        # Handle JSON fields (Tags, IngressRules, etc.)
        if header in [
            "Tags",
            "IngressRules",
            "EgressRules",
            "SecurityRules",
            "DataDisks",
            "LifecycleRules",
            "BlobContainers",
            "NetworkRules",
            "FirewallRules",
            "VirtualNetworkRules",
            "LongTermRetention",
        ]:
            # Try to parse as JSON
            import json

            try:
                return json.loads(str_value)
            except json.JSONDecodeError:
                self.warnings.append(
                    f"Invalid JSON in field {header}: {str_value[:50]}..."
                )
                return str_value

        # Handle boolean fields
        if isinstance(value, bool):
            return value
        if str_value.lower() in ["true", "yes", "1"]:
            return True
        if str_value.lower() in ["false", "no", "0"]:
            return False

        # Handle numeric fields
        if isinstance(value, (int, float)):
            return value

        # Try to convert to number
        try:
            if "." in str_value:
                return float(str_value)
            else:
                return int(str_value)
        except ValueError:
            pass

        # Return as string
        return str_value

    def validate_resource(self, resource: ResourceInfo) -> Tuple[bool, List[str]]:
        """
        Validate a single resource definition.

        Args:
            resource: Resource to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors: List[str] = []

        # Check required common fields
        required_common = ["ResourceName", "Environment", "Project"]
        for field in required_common:
            if field not in resource.properties or not resource.properties[field]:
                errors.append(f"Missing required field: {field}")

        # Validate based on resource type and cloud platform
        if resource.cloud_platform == CloudPlatform.AWS:
            errors.extend(self._validate_aws_resource(resource))
        elif resource.cloud_platform == CloudPlatform.AZURE:
            errors.extend(self._validate_azure_resource(resource))

        return len(errors) == 0, errors

    def _validate_aws_resource(self, resource: ResourceInfo) -> List[str]:
        """Validate AWS-specific resource fields."""
        errors: List[str] = []
        props = resource.properties

        if resource.resource_type == "EC2":
            required = [
                "Region",
                "InstanceType",
                "AMI_ID",
                "VPC",
                "VPCExists",  # New required field
                "Subnet",
                "SubnetExists",  # New required field
                "SecurityGroups",
                "SecurityGroupsExist",  # New required field
                "KeyPairName",
            ]
            for field in required:
                if field not in props or not props[field]:
                    errors.append(f"Missing required field for EC2: {field}")
            # Validate Exists fields values
            exists_fields = ["VPCExists", "SubnetExists", "SecurityGroupsExist"]
            for field in exists_fields:
                if field in props and props[field] not in ["y", "n"]:
                    errors.append(f"{field} must be 'y' or 'n'")

        elif resource.resource_type == "VPC":
            required = ["Region", "CIDR_Block"]
            for field in required:
                if field not in props or not props[field]:
                    errors.append(f"Missing required field for VPC: {field}")

            # Validate CIDR format
            if "CIDR_Block" in props:
                if not self._is_valid_cidr(props["CIDR_Block"]):
                    errors.append(f"Invalid CIDR format: {props['CIDR_Block']}")

        elif resource.resource_type == "Subnet":
            required = [
                "VPC",
                "VPCExists",
                "AvailabilityZone",
                "CIDR_Block",
            ]  # Updated required fields
            for field in required:
                if field not in props or not props[field]:
                    errors.append(f"Missing required field for Subnet: {field}")
            # Validate VPCExists value
            if "VPCExists" in props and props["VPCExists"] not in ["y", "n"]:
                errors.append("VPCExists must be 'y' or 'n'")

        elif resource.resource_type == "SecurityGroup":
            required = [
                "VPC",
                "VPCExists",
                "Description",
                "IngressRules",
            ]  # Updated required fields
            for field in required:
                if field not in props or not props[field]:
                    errors.append(f"Missing required field for SecurityGroup: {field}")
            # Validate VPCExists value
            if "VPCExists" in props and props["VPCExists"] not in ["y", "n"]:
                errors.append("VPCExists must be 'y' or 'n'")

        elif resource.resource_type == "S3":
            required = ["Region", "Versioning", "Encryption"]
            for field in required:
                if field not in props or not props[field]:
                    errors.append(f"Missing required field for S3: {field}")

        elif resource.resource_type == "RDS":
            required = [
                "Region",
                "Engine",
                "InstanceClass",
                "AllocatedStorage",
                "DBName",
                "MasterUsername",
                "VPC",
                "VPCExists",  # New required field
                "SecurityGroups",
                "SecurityGroupsExist",  # New required field
            ]
            for field in required:
                if field not in props or not props[field]:
                    errors.append(f"Missing required field for RDS: {field}")
            # Validate Exists fields values
            exists_fields = ["VPCExists", "SecurityGroupsExist"]
            for field in exists_fields:
                if field in props and props[field] not in ["y", "n"]:
                    errors.append(f"{field} must be 'y' or 'n'")

        return errors

    def _validate_azure_resource(self, resource: ResourceInfo) -> List[str]:
        """Validate Azure-specific resource fields."""
        errors: List[str] = []
        props = resource.properties

        if resource.resource_type == "VM":
            required = [
                "ResourceGroup",
                "ResourceGroupExists",  # New required field
                "VNet",
                "VNetExists",  # New required field
                "Subnet",
                "SubnetExists",  # New required field
                "NSG",
                "NSGExists",  # New required field
                "Location",
                "VMSize",
                "OSType",
                "AdminUsername",
            ]
            for field in required:
                if field not in props or not props[field]:
                    errors.append(f"Missing required field for VM: {field}")
            # Validate Exists fields values
            exists_fields = [
                "ResourceGroupExists",
                "VNetExists",
                "SubnetExists",
                "NSGExists",
            ]
            for field in exists_fields:
                if field in props and props[field] not in ["y", "n"]:
                    errors.append(f"{field} must be 'y' or 'n'")

        elif resource.resource_type == "VNet":
            required = [
                "ResourceGroup",
                "ResourceGroupExists",
                "Location",
                "AddressSpace",
            ]  # Updated required fields
            for field in required:
                if field not in props or not props[field]:
                    errors.append(f"Missing required field for VNet: {field}")
            # Validate ResourceGroupExists value
            if "ResourceGroupExists" in props and props["ResourceGroupExists"] not in [
                "y",
                "n",
            ]:
                errors.append("ResourceGroupExists must be 'y' or 'n'")

        elif resource.resource_type == "Subnet":
            required = [
                "ResourceGroup",
                "ResourceGroupExists",
                "VNet",
                "VNetExists",
                "AddressPrefix",
            ]
            for field in required:
                if field not in props or not props[field]:
                    errors.append(f"Missing required field for Subnet: {field}")
            # Validate Exists field values
            exists_fields = ["ResourceGroupExists", "VNetExists"]
            for field in exists_fields:
                if field in props and props[field] not in ["y", "n"]:
                    errors.append(f"{field} must be 'y' or 'n'")

        elif resource.resource_type == "NSG":
            required = [
                "ResourceGroup",
                "ResourceGroupExists",
                "Location",
                "SecurityRules",
            ]  # Updated required fields
            for field in required:
                if field not in props or not props[field]:
                    errors.append(f"Missing required field for NSG: {field}")
            # Validate ResourceGroupExists value
            if "ResourceGroupExists" in props and props["ResourceGroupExists"] not in [
                "y",
                "n",
            ]:
                errors.append("ResourceGroupExists must be 'y' or 'n'")

        elif resource.resource_type == "Storage":
            required = [
                "ResourceGroup",
                "ResourceGroupExists",  # New required field
                "Location",
                "AccountKind",
                "AccountTier",
                "ReplicationType",
            ]
            for field in required:
                if field not in props or not props[field]:
                    errors.append(f"Missing required field for Storage: {field}")
            # Validate ResourceGroupExists value
            if "ResourceGroupExists" in props and props["ResourceGroupExists"] not in [
                "y",
                "n",
            ]:
                errors.append("ResourceGroupExists must be 'y' or 'n'")

        elif resource.resource_type == "SQL":
            required = [
                "ResourceGroup",
                "ResourceGroupExists",  # New required field
                "Location",
                "ServerName",
                "ServerAdminLogin",
                "DatabaseEdition",
                "VNet",
                "VNetExists",  # New required field
                "Subnet",
                "SubnetExists",  # New required field
            ]
            for field in required:
                if field not in props or not props[field]:
                    errors.append(f"Missing required field for SQL: {field}")
            # Validate Exists fields values
            exists_fields = ["ResourceGroupExists", "VNetExists", "SubnetExists"]
            for field in exists_fields:
                if field in props and props[field] not in ["y", "n"]:
                    errors.append(f"{field} must be 'y' or 'n'")

        return errors

    def _is_valid_cidr(self, cidr: str) -> bool:
        """
        Validate CIDR notation.

        Args:
            cidr: CIDR string to validate

        Returns:
            True if valid CIDR
        """
        pattern = r"^([0-9]{1,3}\.){3}[0-9]{1,3}/([0-9]|[1-2][0-9]|3[0-2])$"
        return bool(re.match(pattern, str(cidr)))

    def _merge_metadata_to_tags(self, properties: Dict[str, Any]) -> None:
        """
        Merge metadata columns (Environment, Project, Owner, CostCenter) into Tags dict.

        This ensures that these common metadata fields are available as tags
        for compliance checking and Terraform resource tagging.

        Args:
            properties: Resource properties dict (modified in-place)
        """
        # Get existing Tags dict or create new one
        tags = properties.get("Tags", {})
        if not isinstance(tags, dict):
            # If Tags is not a dict (e.g., parsing failed), create empty dict
            tags = {}

        # Metadata fields to merge into tags
        metadata_fields = ["Environment", "Project", "Owner", "CostCenter"]

        for field in metadata_fields:
            if field in properties and properties[field]:
                # Only add to tags if not already present (case-insensitive check)
                tag_keys_lower = {k.lower(): k for k in tags.keys()}
                if field.lower() not in tag_keys_lower:
                    tags[field] = properties[field]

        # Update Tags in properties
        properties["Tags"] = tags
