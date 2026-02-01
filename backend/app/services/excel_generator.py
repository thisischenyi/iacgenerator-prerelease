"""Excel template generator service."""

import io
import xlsxwriter
from typing import List, Dict, Any, Optional
from app.schemas import TemplateType, CloudPlatform


class ExcelGeneratorService:
    """Service for generating Excel templates."""

    # Column definitions based on specification
    COMMON_COLUMNS = [
        "ResourceName",
        "Environment",
        "Project",
        "Owner",
        "CostCenter",
        "Tags",
    ]

    # Dropdown options
    ENVIRONMENTS = ["Development", "Testing", "Staging", "Production", "DR"]
    AWS_REGIONS = [
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
        "eu-west-1",
        "eu-central-1",
        "ap-southeast-1",
        "ap-northeast-1",
    ]
    AZURE_REGIONS = [
        "eastus",
        "eastus2",
        "westus",
        "westus2",
        "centralus",
        "northeurope",
        "westeurope",
        "uksouth",
        "southeastasia",
        "eastasia",
    ]
    BOOLEAN_OPTIONS = ["true", "false"]

    # Resource Definitions
    AWS_RESOURCES = {
        "AWS_EC2": [
            "Region",
            "AvailabilityZone",
            "InstanceType",
            "AMI_ID",
            "VPC",
            "VPCExists",  # y/n - whether the VPC already exists
            "Subnet",
            "SubnetExists",  # y/n - whether the Subnet already exists
            "SecurityGroups",
            "SecurityGroupsExist",  # y/n - whether the Security Groups already exist
            "KeyPairName",
            "AssociatePublicIP",
            "RootVolumeSize",
            "RootVolumeType",
            "EnableMonitoring",
            "UserData",
            "IAM_Role",
        ],
        "AWS_VPC": [
            "Region",
            "CIDR_Block",
            "EnableDNSHostnames",
            "EnableDNSSupport",
            "InstanceTenancy",
        ],
        "AWS_Subnet": [
            "VPC",
            "VPCExists",  # y/n - whether the VPC already exists
            "AvailabilityZone",
            "CIDR_Block",
            "MapPublicIP",
            "SubnetType",
        ],
        "AWS_SecurityGroup": [
            "VPC",
            "VPCExists",  # y/n - whether the VPC already exists
            "Description",
            "IngressRules",
            "EgressRules",
        ],
        "AWS_S3": [
            "Region",
            "Versioning",
            "Encryption",
            "KMS_Key_ID",
            "BlockPublicAccess",
            "BucketPolicy",
            "LifecycleRules",
        ],
        "AWS_RDS": [
            "Region",
            "Engine",
            "EngineVersion",
            "InstanceClass",
            "AllocatedStorage",
            "StorageType",
            "StorageEncrypted",
            "KMS_Key_ID",
            "DBName",
            "MasterUsername",
            "MasterPassword",
            "VPC",
            "VPCExists",  # y/n - whether the VPC already exists
            "SubnetGroup_Subnets",
            "SecurityGroups",
            "SecurityGroupsExist",  # y/n - whether the Security Groups already exist
            "MultiAZ",
            "PubliclyAccessible",
            "BackupRetentionPeriod",
            "PreferredBackupWindow",
            "PreferredMaintenanceWindow",
            "AutoMinorVersionUpgrade",
            "DeletionProtection",
        ],
    }

    AZURE_RESOURCES = {
        "Azure_VM": [
            "ResourceGroup",
            "ResourceGroupExists",  # y/n - whether the resource group already exists
            "VNet",
            "VNetExists",  # y/n - whether the VNet already exists
            "Subnet",
            "SubnetExists",  # y/n - whether the Subnet already exists
            "NSG",
            "NSGExists",  # y/n - whether the NSG already exists
            "Location",
            "VMSize",
            "OSType",
            "ImagePublisher",
            "ImageOffer",
            "ImageSKU",
            "ImageVersion",
            "AdminUsername",
            "AuthenticationType",
            "AdminPassword",
            "SSHPublicKey",
            "OSDiskType",
            "OSDiskSizeGB",
            "DataDisks",
            "AssignPublicIP",
            "AvailabilityZone",
        ],
        "Azure_VNet": [
            "ResourceGroup",
            "ResourceGroupExists",  # y/n - whether the resource group already exists
            "Location",
            "AddressSpace",
            "DNSServers",
        ],
        "Azure_Subnet": [
            "VNet",
            "VNetExists",  # y/n - whether the VNet already exists
            "AddressPrefix",
            "ServiceEndpoints",
        ],
        "Azure_NSG": [
            "ResourceGroup",
            "ResourceGroupExists",  # y/n - whether the resource group already exists
            "Location",
            "SecurityRules",
        ],
        "Azure_Storage": [
            "ResourceGroup",
            "ResourceGroupExists",  # y/n - whether the resource group already exists
            "Location",
            "AccountKind",
            "AccountTier",
            "ReplicationType",
            "AccessTier",
            "EnableHTTPSOnly",
            "MinimumTLSVersion",
            "AllowBlobPublicAccess",
            "EnableBlobEncryption",
            "EnableFileEncryption",
            "NetworkRules",
            "BlobContainers",
        ],
        "Azure_SQL": [
            "ResourceGroup",
            "ResourceGroupExists",  # y/n - whether the resource group already exists
            "Location",
            "ServerName",
            "ServerAdminLogin",
            "ServerAdminPassword",
            "SQLVersion",
            "DatabaseEdition",
            "ServiceObjective",
            "MaxSizeGB",
            "Collation",
            "ZoneRedundant",
            "ReadScaleOut",
            "PublicNetworkAccess",
            "MinimalTLSVersion",
            "VNet",
            "VNetExists",  # y/n - whether the VNet already exists
            "Subnet",
            "SubnetExists",  # y/n - whether the Subnet already exists
            "FirewallRules",
            "VirtualNetworkRules",
            "TransparentDataEncryption",
            "BackupRetentionDays",
            "LongTermRetention",
            "ThreatDetection",
            "AuditingEnabled",
        ],
    }

    # Required fields for each resource type (in addition to common required fields)
    REQUIRED_FIELDS = {
        "AWS_EC2": [
            "ResourceName",
            "Environment",
            "Project",
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
        ],
        "AWS_VPC": ["ResourceName", "Environment", "Project", "Region", "CIDR_Block"],
        "AWS_Subnet": [
            "ResourceName",
            "Environment",
            "Project",
            "VPC",
            "VPCExists",  # New required field
            "AvailabilityZone",
            "CIDR_Block",
        ],
        "AWS_SecurityGroup": [
            "ResourceName",
            "Environment",
            "Project",
            "VPC",
            "VPCExists",  # New required field
            "Description",
            "IngressRules",
        ],
        "AWS_S3": [
            "ResourceName",
            "Environment",
            "Project",
            "Region",
            "Versioning",
            "Encryption",
        ],
        "AWS_RDS": [
            "ResourceName",
            "Environment",
            "Project",
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
        ],
        "Azure_VM": [
            "ResourceName",
            "Environment",
            "Project",
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
        ],
        "Azure_VNet": [
            "ResourceName",
            "Environment",
            "Project",
            "ResourceGroup",
            "ResourceGroupExists",  # New required field
            "Location",
            "AddressSpace",
        ],
        "Azure_Subnet": [
            "ResourceName",
            "Environment",
            "Project",
            "VNet",
            "VNetExists",  # New required field
            "AddressPrefix",
        ],
        "Azure_NSG": [
            "ResourceName",
            "Environment",
            "Project",
            "ResourceGroup",
            "ResourceGroupExists",  # New required field
            "Location",
            "SecurityRules",
        ],
        "Azure_Storage": [
            "ResourceName",
            "Environment",
            "Project",
            "ResourceGroup",
            "ResourceGroupExists",  # New required field
            "Location",
            "AccountKind",
            "AccountTier",
            "ReplicationType",
        ],
        "Azure_SQL": [
            "ResourceName",
            "Environment",
            "Project",
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
        ],
    }

    # Sample data for each resource type
    SAMPLE_DATA = {
        "AWS_EC2": {
            "ResourceName": "web-server-01",
            "Environment": "Production",
            "Project": "MyProject",
            "Owner": "john.doe@example.com",
            "CostCenter": "IT-1234",
            "Tags": '{"Application": "WebServer", "Backup": "Daily"}',
            "Region": "us-east-1",
            "AvailabilityZone": "us-east-1a",
            "InstanceType": "t3.medium",
            "AMI_ID": "ami-0c55b159cbfafe1f0",
            "VPC": "main-vpc",
            "VPCExists": "n",  # Create new VPC
            "Subnet": "public-subnet-1",
            "SubnetExists": "n",  # Create new Subnet
            "SecurityGroups": "web-sg",
            "SecurityGroupsExist": "n",  # Create new Security Groups
            "KeyPairName": "my-keypair",
            "AssociatePublicIP": "true",
            "RootVolumeSize": "30",
            "RootVolumeType": "gp3",
            "EnableMonitoring": "true",
            "UserData": "#!/bin/bash\necho 'Hello World'",
            "IAM_Role": "EC2-S3-ReadOnly",
        },
        "AWS_VPC": {
            "ResourceName": "main-vpc",
            "Environment": "Production",
            "Project": "MyProject",
            "Owner": "john.doe@example.com",
            "CostCenter": "IT-1234",
            "Tags": '{"Network": "Main"}',
            "Region": "us-east-1",
            "CIDR_Block": "10.0.0.0/16",
            "EnableDNSHostnames": "true",
            "EnableDNSSupport": "true",
            "InstanceTenancy": "default",
        },
        "AWS_Subnet": {
            "ResourceName": "public-subnet-1",
            "Environment": "Production",
            "Project": "MyProject",
            "Owner": "john.doe@example.com",
            "CostCenter": "IT-1234",
            "Tags": '{"Tier": "Public"}',
            "VPC": "main-vpc",
            "VPCExists": "n",  # Create new VPC
            "AvailabilityZone": "us-east-1a",
            "CIDR_Block": "10.0.1.0/24",
            "MapPublicIP": "true",
            "SubnetType": "Public",
        },
        "AWS_SecurityGroup": {
            "ResourceName": "web-sg",
            "Environment": "Production",
            "Project": "MyProject",
            "Owner": "john.doe@example.com",
            "CostCenter": "IT-1234",
            "Tags": '{"Purpose": "WebServer"}',
            "VPC": "main-vpc",
            "VPCExists": "n",  # Create new VPC
            "Description": "Security group for web servers",
            "IngressRules": '[{"protocol": "tcp", "from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"]}]',
            "EgressRules": '[{"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]}]',
        },
        "AWS_S3": {
            "ResourceName": "my-data-bucket",
            "Environment": "Production",
            "Project": "MyProject",
            "Owner": "john.doe@example.com",
            "CostCenter": "IT-1234",
            "Tags": '{"DataClassification": "Confidential"}',
            "Region": "us-east-1",
            "Versioning": "Enabled",
            "Encryption": "AES256",
            "KMS_Key_ID": "",
            "BlockPublicAccess": "true",
            "BucketPolicy": "",
            "LifecycleRules": '[{"id": "archive", "status": "Enabled", "transitions": [{"days": 90, "storage_class": "GLACIER"}]}]',
        },
        "AWS_RDS": {
            "ResourceName": "prod-db",
            "Environment": "Production",
            "Project": "MyProject",
            "Owner": "john.doe@example.com",
            "CostCenter": "IT-1234",
            "Tags": '{"Database": "Primary"}',
            "Region": "us-east-1",
            "Engine": "postgres",
            "EngineVersion": "14.7",
            "InstanceClass": "db.t3.medium",
            "AllocatedStorage": "100",
            "StorageType": "gp3",
            "StorageEncrypted": "true",
            "KMS_Key_ID": "",
            "DBName": "mydatabase",
            "MasterUsername": "dbadmin",
            "MasterPassword": "ChangeMe123!",
            "VPC": "main-vpc",
            "VPCExists": "n",  # Create new VPC
            "SubnetGroup_Subnets": "private-subnet-1,private-subnet-2",
            "SecurityGroups": "db-sg",
            "SecurityGroupsExist": "n",  # Create new Security Groups
            "MultiAZ": "true",
            "PubliclyAccessible": "false",
            "BackupRetentionPeriod": "7",
            "PreferredBackupWindow": "03:00-04:00",
            "PreferredMaintenanceWindow": "sun:04:00-sun:05:00",
            "AutoMinorVersionUpgrade": "true",
            "DeletionProtection": "true",
        },
        "Azure_VM": {
            "ResourceName": "web-vm-01",
            "Environment": "Production",
            "Project": "MyProject",
            "Owner": "john.doe@example.com",
            "CostCenter": "IT-1234",
            "Tags": '{"Application": "WebServer"}',
            "ResourceGroup": "rg-myproject-prod",
            "ResourceGroupExists": "n",  # Create new resource group
            "VNet": "main-vnet",
            "VNetExists": "n",  # Create new VNet
            "Subnet": "web-subnet",
            "SubnetExists": "n",  # Create new Subnet
            "NSG": "web-nsg",
            "NSGExists": "n",  # Create new NSG
            "Location": "eastus",
            "VMSize": "Standard_D2s_v3",
            "OSType": "Linux",
            "ImagePublisher": "Canonical",
            "ImageOffer": "UbuntuServer",
            "ImageSKU": "18.04-LTS",
            "ImageVersion": "latest",
            "AdminUsername": "azureuser",
            "AuthenticationType": "SSH",
            "AdminPassword": "",
            "SSHPublicKey": "ssh-rsa AAAAB3NzaC1yc2E...",
            "OSDiskType": "Premium_LRS",
            "OSDiskSizeGB": "30",
            "DataDisks": '[{"size_gb": 100, "type": "Premium_LRS"}]',
            "AssignPublicIP": "true",
            "AvailabilityZone": "1",
        },
        "Azure_VNet": {
            "ResourceName": "main-vnet",
            "Environment": "Production",
            "Project": "MyProject",
            "Owner": "john.doe@example.com",
            "CostCenter": "IT-1234",
            "Tags": '{"Network": "Main"}',
            "ResourceGroup": "rg-myproject-prod",
            "ResourceGroupExists": "n",  # Create new resource group
            "Location": "eastus",
            "AddressSpace": "10.0.0.0/16",
            "DNSServers": "8.8.8.8,8.8.4.4",
        },
        "Azure_Subnet": {
            "ResourceName": "web-subnet",
            "Environment": "Production",
            "Project": "MyProject",
            "Owner": "john.doe@example.com",
            "CostCenter": "IT-1234",
            "Tags": '{"Tier": "Web"}',
            "VNet": "main-vnet",
            "VNetExists": "n",  # Create new VNet
            "AddressPrefix": "10.0.1.0/24",
            "ServiceEndpoints": "Microsoft.Storage,Microsoft.Sql",
        },
        "Azure_NSG": {
            "ResourceName": "web-nsg",
            "Environment": "Production",
            "Project": "MyProject",
            "Owner": "john.doe@example.com",
            "CostCenter": "IT-1234",
            "Tags": '{"Purpose": "WebServer"}',
            "ResourceGroup": "rg-myproject-prod",
            "ResourceGroupExists": "n",  # Create new resource group
            "Location": "eastus",
            "SecurityRules": '[{"name": "AllowHTTPS", "priority": 100, "direction": "Inbound", "access": "Allow", "protocol": "Tcp", "source_port_range": "*", "destination_port_range": "443", "source_address_prefix": "*", "destination_address_prefix": "*"}]',
        },
        "Azure_Storage": {
            "ResourceName": "mystorageaccount",
            "Environment": "Production",
            "Project": "MyProject",
            "Owner": "john.doe@example.com",
            "CostCenter": "IT-1234",
            "Tags": '{"DataType": "Application"}',
            "ResourceGroup": "rg-myproject-prod",
            "ResourceGroupExists": "n",  # Create new resource group
            "Location": "eastus",
            "AccountKind": "StorageV2",
            "AccountTier": "Standard",
            "ReplicationType": "GRS",
            "AccessTier": "Hot",
            "EnableHTTPSOnly": "true",
            "MinimumTLSVersion": "TLS1_2",
            "AllowBlobPublicAccess": "false",
            "EnableBlobEncryption": "true",
            "EnableFileEncryption": "true",
            "NetworkRules": '{"default_action": "Deny", "ip_rules": ["203.0.113.0/24"]}',
            "BlobContainers": '[{"name": "data", "access_type": "private"}]',
        },
        "Azure_SQL": {
            "ResourceName": "prod-sqldb",
            "Environment": "Production",
            "Project": "MyProject",
            "Owner": "john.doe@example.com",
            "CostCenter": "IT-1234",
            "Tags": '{"Database": "Primary"}',
            "ResourceGroup": "rg-myproject-prod",
            "ResourceGroupExists": "n",  # Create new resource group
            "Location": "eastus",
            "ServerName": "myproject-sql-server",
            "ServerAdminLogin": "sqladmin",
            "ServerAdminPassword": "ChangeMe123!",
            "SQLVersion": "12.0",
            "DatabaseEdition": "Standard",
            "ServiceObjective": "S1",
            "MaxSizeGB": "250",
            "Collation": "SQL_Latin1_General_CP1_CI_AS",
            "ZoneRedundant": "false",
            "ReadScaleOut": "Disabled",
            "PublicNetworkAccess": "Disabled",
            "MinimalTLSVersion": "1.2",
            "VNet_Reference": "main-vnet",
            "Subnet_Reference": "db-subnet",
            "FirewallRules": '[{"name": "AllowAzureServices", "start_ip": "0.0.0.0", "end_ip": "0.0.0.0"}]',
            "VirtualNetworkRules": "",
            "TransparentDataEncryption": "Enabled",
            "BackupRetentionDays": "7",
            "LongTermRetention": '{"weekly_retention": "P4W", "monthly_retention": "P12M"}',
            "ThreatDetection": "Enabled",
            "AuditingEnabled": "true",
        },
    }

    def generate_template(self, template_type: TemplateType) -> bytes:
        """
        Generate Excel template file.

        Args:
            template_type: Type of template (AWS, Azure, or FULL)

        Returns:
            Bytes content of the Excel file
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Formats
        header_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#A100FF",  # Accenture Purple
                "font_color": "#FFFFFF",
                "border": 1,
            }
        )

        # Format for required field headers (darker purple/red tint)
        required_header_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#7D00C7",  # Darker purple for required fields
                "font_color": "#FFFFFF",
                "border": 1,
            }
        )

        # Format for sample data row
        sample_data_format = workbook.add_format(
            {
                "italic": True,
                "font_color": "#666666",
                "bg_color": "#F5F5F5",  # Light gray background
                "border": 1,
            }
        )

        note_format = workbook.add_format(
            {
                "italic": True,
                "font_color": "#666666",
                "text_wrap": True,
                "valign": "top",
            }
        )

        # Create README sheet
        self._create_readme_sheet(workbook, header_format, note_format)

        # Determine which sheets to create
        sheets_to_create = {}
        if template_type in [TemplateType.AWS, TemplateType.FULL]:
            sheets_to_create.update(self.AWS_RESOURCES)

        if template_type in [TemplateType.AZURE, TemplateType.FULL]:
            sheets_to_create.update(self.AZURE_RESOURCES)

        # Create resource sheets
        for sheet_name, specific_columns in sheets_to_create.items():
            self._create_resource_sheet(
                workbook,
                sheet_name,
                self.COMMON_COLUMNS + specific_columns,
                header_format,
                required_header_format,
                sample_data_format,
            )

        workbook.close()
        return output.getvalue()

    def _create_readme_sheet(self, workbook, header_format, note_format):
        """Create the README instruction sheet."""
        sheet = workbook.add_worksheet("README")
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 100)

        sheet.write(0, 0, "Instructions", header_format)
        sheet.write(0, 1, "Details", header_format)

        instructions = [
            (
                "Purpose",
                "This template is used to define cloud resources for automatic IaC generation.",
            ),
            (
                "How to use",
                "Fill in the sheets corresponding to the resources you want to create. Leave other sheets empty. Start from row 3 (row 2 contains sample data).",
            ),
            (
                "Required Fields",
                "Required fields are marked with an asterisk (*) and have a darker purple background (#7D00C7). These fields MUST be filled in for successful code generation.",
            ),
            (
                "Sample Data",
                "Row 2 in each resource sheet contains sample data with realistic example values. Use these as a reference to understand the expected format and values.",
            ),
            (
                "ResourceGroupExists Field",
                "For Azure resources, the 'ResourceGroupExists' field indicates whether the specified resource group already exists. "
                "Enter 'y' if the resource group already exists, or 'n' if it should be created. "
                "If 'y' is specified, the Terraform code will reference the existing resource group instead of creating a new one.",
            ),
            (
                "VNetExists Field",
                "For Azure resources, the 'VNetExists' field indicates whether the specified VNet already exists. "
                "Enter 'y' if the VNet already exists, or 'n' if it should be created. "
                "If 'y' is specified, the Terraform code will reference the existing VNet instead of creating a new one.",
            ),
            (
                "SubnetExists Field",
                "For Azure resources, the 'SubnetExists' field indicates whether the specified Subnet already exists. "
                "Enter 'y' if the Subnet already exists, or 'n' if it should be created. "
                "If 'y' is specified, the Terraform code will reference the existing Subnet instead of creating a new one.",
            ),
            (
                "NSGExists Field",
                "For Azure resources, the 'NSGExists' field indicates whether the specified NSG already exists. "
                "Enter 'y' if the NSG already exists, or 'n' if it should be created. "
                "If 'y' is specified, the Terraform code will reference the existing NSG instead of creating a new one.",
            ),
            (
                "VPCExists Field",
                "For AWS resources, the 'VPCExists' field indicates whether the specified VPC already exists. "
                "Enter 'y' if the VPC already exists, or 'n' if it should be created. "
                "If 'y' is specified, the Terraform code will reference the existing VPC instead of creating a new one.",
            ),
            (
                "SubnetExists Field",
                "For AWS resources, the 'SubnetExists' field indicates whether the specified Subnet already exists. "
                "Enter 'y' if the Subnet already exists, or 'n' if it should be created. "
                "If 'y' is specified, the Terraform code will reference the existing Subnet instead of creating a new one.",
            ),
            (
                "SecurityGroupsExist Field",
                "For AWS resources, the 'SecurityGroupsExist' field indicates whether the specified Security Groups already exist. "
                "Enter 'y' if the Security Groups already exist, or 'n' if they should be created. "
                "If 'y' is specified, the Terraform code will reference the existing Security Groups instead of creating new ones.",
            ),
            (
                "JSON Fields",
                "Some fields like Tags or Rules require valid JSON format. Refer to sample data for examples.",
            ),
            (
                "References",
                "Use 'ResourceName' from other sheets to reference dependencies (e.g. VPC_Reference).",
            ),
            (
                "Accenture Color",
                "Headers are styled with Accenture Purple (#A100FF). Required fields use darker purple (#7D00C7).",
            ),
        ]

        for i, (title, detail) in enumerate(instructions, start=1):
            sheet.write(i, 0, title, workbook.add_format({"bold": True}))
            sheet.write(i, 1, detail, note_format)

    def _create_resource_sheet(
        self,
        workbook,
        sheet_name,
        columns,
        header_format,
        required_header_format,
        sample_data_format,
    ):
        """Create a specific resource sheet with validation."""
        sheet = workbook.add_worksheet(sheet_name)

        # Get required fields for this resource type
        required_fields = self.REQUIRED_FIELDS.get(sheet_name, [])

        # Write headers with appropriate formatting
        for col_idx, header in enumerate(columns):
            # Check if this field is required
            is_required = header in required_fields

            # Add asterisk to required field names
            display_header = f"{header}*" if is_required else header

            # Use appropriate format
            fmt = required_header_format if is_required else header_format

            sheet.write(0, col_idx, display_header, fmt)
            # Set approximate column width
            sheet.set_column(col_idx, col_idx, 20)

        # Write sample data row (row 2, since row 1 is header)
        sample_data = self.SAMPLE_DATA.get(sheet_name, {})
        for col_idx, header in enumerate(columns):
            sample_value = sample_data.get(header, "")
            sheet.write(1, col_idx, sample_value, sample_data_format)

        # Add Data Validations (Dropdowns)
        # Note: xlsxwriter applies validation to a range. applying to rows 2-1000 (row 1 is sample)

        # Environment
        self._add_dropdown(
            sheet, columns, "Environment", self.ENVIRONMENTS, start_row=2
        )

        # Cloud specific validations
        if "AWS" in sheet_name:
            self._add_dropdown(sheet, columns, "Region", self.AWS_REGIONS, start_row=2)
            self._add_dropdown(
                sheet, columns, "AssociatePublicIP", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "EnableDNSHostnames", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "EnableDNSSupport", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "MapPublicIP", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "Versioning", ["Enabled", "Suspended"], start_row=2
            )
            self._add_dropdown(
                sheet, columns, "BlockPublicAccess", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "MultiAZ", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "PubliclyAccessible", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "StorageEncrypted", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "DeletionProtection", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "SubnetType", ["Public", "Private"], start_row=2
            )
            # Add Exists fields dropdowns for AWS resources
            self._add_dropdown(sheet, columns, "VPCExists", ["y", "n"], start_row=2)
            self._add_dropdown(sheet, columns, "SubnetExists", ["y", "n"], start_row=2)
            self._add_dropdown(
                sheet, columns, "SecurityGroupsExist", ["y", "n"], start_row=2
            )

        elif "Azure" in sheet_name:
            self._add_dropdown(
                sheet, columns, "Location", self.AZURE_REGIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "OSType", ["Linux", "Windows"], start_row=2
            )
            self._add_dropdown(
                sheet, columns, "AuthenticationType", ["Password", "SSH"], start_row=2
            )
            self._add_dropdown(
                sheet,
                columns,
                "OSDiskType",
                ["StandardSSD_LRS", "Premium_LRS", "Standard_LRS"],
                start_row=2,
            )
            self._add_dropdown(
                sheet, columns, "AssignPublicIP", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet,
                columns,
                "AccountKind",
                ["StorageV2", "BlobStorage", "FileStorage"],
                start_row=2,
            )
            self._add_dropdown(
                sheet, columns, "AccountTier", ["Standard", "Premium"], start_row=2
            )
            self._add_dropdown(
                sheet,
                columns,
                "ReplicationType",
                ["LRS", "GRS", "RAGRS", "ZRS", "GZRS", "RAGZRS"],
                start_row=2,
            )
            self._add_dropdown(
                sheet, columns, "EnableHTTPSOnly", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet,
                columns,
                "PublicNetworkAccess",
                ["Enabled", "Disabled"],
                start_row=2,
            )
            self._add_dropdown(
                sheet,
                columns,
                "TransparentDataEncryption",
                ["Enabled", "Disabled"],
                start_row=2,
            )
            self._add_dropdown(
                sheet, columns, "ZoneRedundant", self.BOOLEAN_OPTIONS, start_row=2
            )
            # Add Exists fields dropdowns for Azure resources
            self._add_dropdown(
                sheet, columns, "ResourceGroupExists", ["y", "n"], start_row=2
            )
            # Add Exists fields dropdowns for Azure resources
            self._add_dropdown(sheet, columns, "VNetExists", ["y", "n"], start_row=2)
            self._add_dropdown(sheet, columns, "SubnetExists", ["y", "n"], start_row=2)
            self._add_dropdown(sheet, columns, "NSGExists", ["y", "n"], start_row=2)
            self._add_dropdown(
                sheet, columns, "EnableDNSHostnames", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "EnableDNSSupport", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "MapPublicIP", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "Versioning", ["Enabled", "Suspended"], start_row=2
            )
            self._add_dropdown(
                sheet, columns, "BlockPublicAccess", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "MultiAZ", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "PubliclyAccessible", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "StorageEncrypted", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "DeletionProtection", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "SubnetType", ["Public", "Private"], start_row=2
            )

        elif "Azure" in sheet_name:
            self._add_dropdown(
                sheet, columns, "Location", self.AZURE_REGIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "OSType", ["Linux", "Windows"], start_row=2
            )
            self._add_dropdown(
                sheet, columns, "AuthenticationType", ["Password", "SSH"], start_row=2
            )
            self._add_dropdown(
                sheet,
                columns,
                "OSDiskType",
                ["StandardSSD_LRS", "Premium_LRS", "Standard_LRS"],
                start_row=2,
            )
            self._add_dropdown(
                sheet, columns, "AssignPublicIP", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet,
                columns,
                "AccountKind",
                ["StorageV2", "BlobStorage", "FileStorage"],
                start_row=2,
            )
            self._add_dropdown(
                sheet, columns, "AccountTier", ["Standard", "Premium"], start_row=2
            )
            self._add_dropdown(
                sheet,
                columns,
                "ReplicationType",
                ["LRS", "GRS", "RAGRS", "ZRS", "GZRS", "RAGZRS"],
                start_row=2,
            )
            self._add_dropdown(
                sheet, columns, "EnableHTTPSOnly", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet,
                columns,
                "PublicNetworkAccess",
                ["Enabled", "Disabled"],
                start_row=2,
            )
            self._add_dropdown(
                sheet,
                columns,
                "TransparentDataEncryption",
                ["Enabled", "Disabled"],
                start_row=2,
            )
            self._add_dropdown(
                sheet, columns, "ZoneRedundant", self.BOOLEAN_OPTIONS, start_row=2
            )
            self._add_dropdown(
                sheet, columns, "ResourceGroupExists", ["y", "n"], start_row=2
            )
            # Add Exists fields dropdowns for Azure resources
            self._add_dropdown(sheet, columns, "VNetExists", ["y", "n"], start_row=2)
            self._add_dropdown(sheet, columns, "SubnetExists", ["y", "n"], start_row=2)
            self._add_dropdown(sheet, columns, "NSGExists", ["y", "n"], start_row=2)

    def _add_dropdown(self, sheet, columns, col_name, options, start_row=1):
        """Helper to add dropdown validation to a column."""
        try:
            col_idx = columns.index(col_name)
            sheet.data_validation(
                start_row,
                col_idx,
                1000,
                col_idx,
                {"validate": "list", "source": options},
            )
        except ValueError:
            # Column not found in this sheet
            pass
