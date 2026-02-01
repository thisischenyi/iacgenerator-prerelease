"""Terraform code generation service using Jinja2 templates."""

import os
from typing import Dict, List, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.schemas import CloudPlatform


class TerraformCodeGenerator:
    """Service to generate Terraform code from resource definitions."""

    def __init__(self):
        """Initialize Jinja2 environment."""
        template_dir = os.path.join(
            os.path.dirname(__file__), "..", "templates", "terraform"
        )

        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters["tojson"] = self._to_json
        self.env.filters["trim"] = str.strip
        self.env.filters["to_hcl_map"] = self._to_hcl_map

    def _to_json(self, value: Any) -> str:
        """Convert value to JSON string."""
        import json

        return json.dumps(value)

    def _to_hcl_map(self, value: Any) -> str:
        """
        Convert a dict to HCL map syntax.

        Example:
          {"Owner": "Team", "Project": "Demo"}
        becomes:
          {
            Owner   = "Team"
            Project = "Demo"
          }
        """
        if not isinstance(value, dict) or not value:
            return "{}"

        lines = ["{"]
        # Find max key length for alignment
        max_len = max(len(str(k)) for k in value.keys()) if value else 0

        for key, val in value.items():
            # Format: key = "value" with proper spacing
            key_str = str(key)
            val_str = f'"{val}"' if isinstance(val, str) else str(val)
            lines.append(f"    {key_str:<{max_len}} = {val_str}")

        lines.append("  }")
        return "\n".join(lines)

    def generate_code(self, resources: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Generate Terraform code from resource definitions.

        Args:
            resources: List of resource definitions

        Returns:
            Dictionary mapping filenames to code content
        """
        print(
            f"[TerraformGenerator] Starting code generation for {len(resources)} resources"
        )
        files = {}

        # Group resources by cloud platform
        aws_resources = [
            r
            for r in resources
            if r.get("cloud_platform") == CloudPlatform.AWS
            or r.get("cloud_platform") == "aws"
        ]
        azure_resources = [
            r
            for r in resources
            if r.get("cloud_platform") == CloudPlatform.AZURE
            or r.get("cloud_platform") == "azure"
        ]

        print(f"[TerraformGenerator] AWS resources: {len(aws_resources)}")
        print(f"[TerraformGenerator] Azure resources: {len(azure_resources)}")

        # For Azure resources, auto-generate Resource Group definitions if needed
        resource_groups_to_create = set()
        for r in azure_resources:
            props = r.get("properties", {})
            rg_name = props.get("ResourceGroup")
            rg_exists = props.get("ResourceGroupExists", "n").lower()
            if rg_name and rg_exists not in ("y", "yes"):
                resource_groups_to_create.add(
                    (rg_name, props.get("Location", "eastus"))
                )

        # Generate provider configuration
        print("[TerraformGenerator] Generating provider.tf...")
        files["provider.tf"] = self._generate_provider(aws_resources, azure_resources)
        print(
            f"[TerraformGenerator] provider.tf generated: {len(files['provider.tf'])} bytes"
        )

        # Generate variables file
        print("[TerraformGenerator] Generating variables.tf...")
        files["variables.tf"] = self._generate_variables(resources)
        print(
            f"[TerraformGenerator] variables.tf generated: {len(files['variables.tf'])} bytes"
        )

        # Generate main resources file
        print("[TerraformGenerator] Generating main.tf...")
        main_code = "# Auto-generated Terraform configuration\n\n"

        # First, generate Resource Group resources for Azure if needed
        if resource_groups_to_create:
            print(
                f"[TerraformGenerator] Auto-generating {len(resource_groups_to_create)} Resource Group(s)"
            )
            for rg_name, rg_location in resource_groups_to_create:
                rg_resource_name = rg_name.replace("-", "_")
                main_code += f'''resource "azurerm_resource_group" "{rg_resource_name}" {{
  name     = "{rg_name}"
  location = "{rg_location}"
}}

'''
                print(f"[TerraformGenerator]   Generated Resource Group: {rg_name}")

        # Generate code for each resource
        for idx, resource in enumerate(resources):
            print(
                f"[TerraformGenerator] Processing resource {idx + 1}/{len(resources)}: {resource.get('resource_name', 'unnamed')}"
            )
            resource_code = self._generate_resource_code(resource)
            if resource_code:
                print(
                    f"[TerraformGenerator]   Generated {len(resource_code)} bytes of code"
                )
                main_code += resource_code + "\n\n"
            else:
                print(
                    f"[TerraformGenerator]   WARNING: No code generated for this resource!"
                )

        files["main.tf"] = main_code
        print(f"[TerraformGenerator] main.tf generated: {len(files['main.tf'])} bytes")

        # Generate outputs file
        print("[TerraformGenerator] Generating outputs.tf...")
        files["outputs.tf"] = self._generate_outputs(resources)
        print(
            f"[TerraformGenerator] outputs.tf generated: {len(files['outputs.tf'])} bytes"
        )

        # Generate README
        print("[TerraformGenerator] Generating README.md...")
        files["README.md"] = self._generate_readme(resources)
        print(
            f"[TerraformGenerator] README.md generated: {len(files['README.md'])} bytes"
        )

        print(
            f"[TerraformGenerator] Code generation complete. Total files: {len(files)}"
        )
        for filename, content in files.items():
            print(f"[TerraformGenerator]   {filename}: {len(content)} bytes")

        return files

    def _generate_provider(self, aws_resources: List, azure_resources: List) -> str:
        """Generate provider configuration."""
        code = "# Provider Configuration\n\n"

        if aws_resources:
            # Extract regions from AWS resources
            regions = set()
            for r in aws_resources:
                if "Region" in r.get("properties", {}):
                    regions.add(r["properties"]["Region"])

            primary_region = list(regions)[0] if regions else "us-east-1"

            code += f"""terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = var.aws_region
}}

"""

        if azure_resources:
            code += """terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.azure_subscription_id
}

"""

        return code

    def _generate_variables(self, resources: List) -> str:
        """Generate variables file."""
        code = "# Variables\n\n"

        # Check if AWS resources exist (check both enum and string values)
        has_aws = any(
            r.get("cloud_platform") == CloudPlatform.AWS
            or r.get("cloud_platform") == "aws"
            for r in resources
        )
        if has_aws:
            code += """variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

"""

        # Check if Azure resources exist (check both enum and string values)
        has_azure = any(
            r.get("cloud_platform") == CloudPlatform.AZURE
            or r.get("cloud_platform") == "azure"
            for r in resources
        )
        if has_azure:
            code += """variable "azure_subscription_id" {
  description = "Azure Subscription ID"
  type        = string
}

"""

        return code

    def _generate_resource_code(self, resource: Dict[str, Any]) -> str:
        """
        Generate code for a single resource using templates.

        Args:
            resource: Resource definition

        Returns:
            Generated Terraform code
        """
        cloud_platform = resource.get("cloud_platform", "")
        resource_type = resource.get("resource_type", "").lower()
        resource_name = resource.get("resource_name", "unnamed")
        properties = resource.get("properties", {})

        print(f"[TerraformGenerator._generate_resource_code] Resource: {resource_name}")
        print(
            f"[TerraformGenerator._generate_resource_code]   Platform: {cloud_platform}"
        )
        print(f"[TerraformGenerator._generate_resource_code]   Type: {resource_type}")
        print(
            f"[TerraformGenerator._generate_resource_code]   Properties: {list(properties.keys())}"
        )

        # Map simple names to full types (aliases)
        type_aliases = {
            "s3": "aws_s3",
            "ec2": "aws_ec2",
            "vpc": "aws_vpc",
            "rds": "aws_rds",
            "subnet": "aws_subnet"
            if cloud_platform != CloudPlatform.AZURE and cloud_platform != "azure"
            else "azure_subnet",
            "security_group": "aws_security_group",
            "securitygroup": "aws_security_group",
            "vm": "azure_vm",
            "vnet": "azure_vnet",
            "resource_group": "azure_resource_group",
            "resourcegroup": "azure_resource_group",
            "nsg": "azure_nsg",
            "storage": "azure_storage",
            "sql": "azure_sql",
        }

        # Normalize resource type first
        original_type = resource_type
        if resource_type in type_aliases:
            resource_type = type_aliases[resource_type]
            print(
                f"[TerraformGenerator._generate_resource_code]   Type alias: {original_type} -> {resource_type}"
            )
        elif cloud_platform and not resource_type.startswith(f"{cloud_platform}_"):
            # Try prepending cloud platform if missing
            platform_str = str(cloud_platform).lower()
            if platform_str.startswith("cloudplatform."):
                platform_str = platform_str.split(".")[-1]
            potential_type = f"{platform_str}_{resource_type}".lower()
            # Also check aliases for the potential type
            if potential_type in type_aliases:
                resource_type = type_aliases[potential_type]
            elif potential_type in type_aliases.values():
                resource_type = potential_type
            else:
                # Check if there's a direct mapping with cloud prefix
                resource_type = potential_type
            print(
                f"[TerraformGenerator._generate_resource_code]   Type normalized: {original_type} -> {resource_type}"
            )

        # For Azure resources, check if we should skip generating resource group
        # Now we use the normalized resource_type
        if (
            cloud_platform == CloudPlatform.AZURE or cloud_platform == "azure"
        ) and resource_type in [
            "azure_vm",
            "azure_vnet",
            "azure_subnet",
            "azure_nsg",
            "azure_storage",
            "azure_sql",
        ]:
            # Check if ResourceGroupExists is 'y' (meaning resource group already exists)
            resource_group_exists = properties.get("ResourceGroupExists", "n").lower()
            if resource_group_exists == "y" or resource_group_exists == "yes":
                print(
                    f"[TerraformGenerator._generate_resource_code]   Resource group exists, skipping resource group creation for {resource_name}"
                )
                # Modify the resource to indicate that the resource group should not be created
                resource["skip_resource_group_creation"] = True

        # Map resource types to template files
        template_map = {
            # AWS resources
            "aws_vpc": "aws/vpc.tf.j2",
            "aws_subnet": "aws/subnet.tf.j2",
            "aws_security_group": "aws/security_group.tf.j2",
            "aws_securitygroup": "aws/security_group.tf.j2",
            "aws_ec2": "aws/ec2.tf.j2",
            "aws_s3": "aws/s3.tf.j2",
            "aws_rds": "aws/rds.tf.j2",
            # Azure resources
            "azure_resource_group": "azure/resource_group.tf.j2",
            "azure_resourcegroup": "azure/resource_group.tf.j2",
            "azure_vnet": "azure/vnet.tf.j2",
            "azure_subnet": "azure/subnet.tf.j2",
            "azure_nsg": "azure/nsg.tf.j2",
            "azure_vm": "azure/vm.tf.j2",
            "azure_storage": "azure/storage.tf.j2",
            "azure_sql": "azure/sql.tf.j2",
        }

        template_name = template_map.get(resource_type)

        if not template_name:
            # Fallback for unsupported resources
            print(
                f"[TerraformGenerator._generate_resource_code]   ERROR: No template found for type '{resource_type}'"
            )
            print(
                f"[TerraformGenerator._generate_resource_code]   Available templates: {list(template_map.keys())}"
            )
            return f"# TODO: Template for {cloud_platform} {resource_type} not implemented\n"

        print(
            f"[TerraformGenerator._generate_resource_code]   Using template: {template_name}"
        )

        try:
            template = self.env.get_template(template_name)
            print(
                f"[TerraformGenerator._generate_resource_code]   Template loaded successfully"
            )
            code = template.render(
                resource_name=resource_name, properties=properties, resource=resource
            )
            print(
                f"[TerraformGenerator._generate_resource_code]   Code rendered: {len(code)} bytes"
            )
            if len(code) < 50:
                print(
                    f"[TerraformGenerator._generate_resource_code]   WARNING: Generated code is suspiciously short!"
                )
                print(f"[TerraformGenerator._generate_resource_code]   Code: {code}")
            return code
        except Exception as e:
            print(f"[TerraformGenerator._generate_resource_code]   ERROR: {str(e)}")
            import traceback

            traceback.print_exc()
            return f"# Error generating code for {resource_name}: {str(e)}\n"

    def _generate_outputs(self, resources: List) -> str:
        """Generate outputs file with useful resource information."""
        code = "# Outputs\\n\\n"

        for resource in resources:
            resource_name = resource.get("resource_name", "").replace("-", "_")
            resource_type = resource.get("resource_type", "").lower()
            cloud_platform = resource.get("cloud_platform", "")
            properties = resource.get("properties", {})

            # Normalize cloud_platform for comparison
            is_aws = cloud_platform == CloudPlatform.AWS or cloud_platform == "aws"
            is_azure = (
                cloud_platform == CloudPlatform.AZURE or cloud_platform == "azure"
            )

            # AWS Resources
            if is_aws:
                if resource_type in ["vpc", "aws_vpc"]:
                    code += f'''output "{resource_name}_vpc_id" {{
  description = "ID of VPC {resource_name}"
  value       = aws_vpc.{resource_name}.id
}}

output "{resource_name}_vpc_cidr" {{
  description = "CIDR block of VPC {resource_name}"
  value       = aws_vpc.{resource_name}.cidr_block
}}

'''
                elif resource_type in ["ec2", "aws_ec2"]:
                    code += f'''output "{resource_name}_instance_id" {{
  description = "Instance ID of EC2 {resource_name}"
  value       = aws_instance.{resource_name}.id
}}

output "{resource_name}_private_ip" {{
  description = "Private IP of EC2 {resource_name}"
  value       = aws_instance.{resource_name}.private_ip
}}

output "{resource_name}_public_ip" {{
  description = "Public IP of EC2 {resource_name} (if assigned)"
  value       = aws_instance.{resource_name}.public_ip
}}

'''
                elif resource_type in ["s3", "aws_s3"]:
                    code += f'''output "{resource_name}_bucket_name" {{
  description = "Name of S3 bucket {resource_name}"
  value       = aws_s3_bucket.{resource_name}.id
}}

output "{resource_name}_bucket_arn" {{
  description = "ARN of S3 bucket {resource_name}"
  value       = aws_s3_bucket.{resource_name}.arn
}}

output "{resource_name}_bucket_domain_name" {{
  description = "Domain name of S3 bucket {resource_name}"
  value       = aws_s3_bucket.{resource_name}.bucket_domain_name
}}

'''
                elif resource_type in ["rds", "aws_rds"]:
                    code += f'''output "{resource_name}_rds_endpoint" {{
  description = "Endpoint of RDS instance {resource_name}"
  value       = aws_db_instance.{resource_name}.endpoint
}}

output "{resource_name}_rds_address" {{
  description = "Address of RDS instance {resource_name}"
  value       = aws_db_instance.{resource_name}.address
}}

output "{resource_name}_rds_port" {{
  description = "Port of RDS instance {resource_name}"
  value       = aws_db_instance.{resource_name}.port
}}

'''
                elif resource_type in ["subnet", "aws_subnet"]:
                    code += f'''output "{resource_name}_subnet_id" {{
  description = "ID of Subnet {resource_name}"
  value       = aws_subnet.{resource_name}.id
}}

'''
                elif resource_type in [
                    "security_group",
                    "aws_security_group",
                    "securitygroup",
                ]:
                    code += f'''output "{resource_name}_security_group_id" {{
  description = "ID of Security Group {resource_name}"
  value       = aws_security_group.{resource_name}.id
}}

'''

            # Azure Resources
            elif is_azure:
                if resource_type in ["vm", "azure_vm"]:
                    os_type = properties.get("OSType", "linux").lower()
                    code += f'''output "{resource_name}_vm_id" {{
  description = "ID of Azure VM {resource_name}"
  value       = azurerm_{os_type}_virtual_machine.{resource_name}.id
}}

output "{resource_name}_private_ip" {{
  description = "Private IP address of Azure VM {resource_name}"
  value       = azurerm_network_interface.{resource_name}_nic.private_ip_address
}}

'''
                    # Add public IP output if AssignPublicIP is true
                    assign_public_ip = properties.get("AssignPublicIP", "")
                    # Handle both boolean and string values
                    if isinstance(assign_public_ip, bool):
                        has_public_ip = assign_public_ip
                    else:
                        has_public_ip = str(assign_public_ip).lower() == "true"

                    if has_public_ip:
                        code += f'''output "{resource_name}_public_ip" {{
  description = "Public IP address of Azure VM {resource_name}"
  value       = azurerm_public_ip.{resource_name}_pip.ip_address
}}

'''

                elif resource_type in ["vnet", "azure_vnet"]:
                    code += f'''output "{resource_name}_vnet_id" {{
  description = "ID of Azure VNet {resource_name}"
  value       = azurerm_virtual_network.{resource_name}.id
}}

output "{resource_name}_vnet_name" {{
  description = "Name of Azure VNet {resource_name}"
  value       = azurerm_virtual_network.{resource_name}.name
}}

output "{resource_name}_address_space" {{
  description = "Address space of Azure VNet {resource_name}"
  value       = azurerm_virtual_network.{resource_name}.address_space
}}

'''

                elif resource_type in ["subnet", "azure_subnet"]:
                    code += f'''output "{resource_name}_subnet_id" {{
  description = "ID of Azure Subnet {resource_name}"
  value       = azurerm_subnet.{resource_name}.id
}}

output "{resource_name}_subnet_name" {{
  description = "Name of Azure Subnet {resource_name}"
  value       = azurerm_subnet.{resource_name}.name
}}

'''

                elif resource_type in ["nsg", "azure_nsg"]:
                    code += f'''output "{resource_name}_nsg_id" {{
  description = "ID of Azure NSG {resource_name}"
  value       = azurerm_network_security_group.{resource_name}.id
}}

output "{resource_name}_nsg_name" {{
  description = "Name of Azure NSG {resource_name}"
  value       = azurerm_network_security_group.{resource_name}.name
}}

'''

                elif resource_type in ["storage", "azure_storage"]:
                    code += f'''output "{resource_name}_storage_account_id" {{
  description = "ID of Azure Storage Account {resource_name}"
  value       = azurerm_storage_account.{resource_name}.id
}}

output "{resource_name}_storage_account_name" {{
  description = "Name of Azure Storage Account {resource_name}"
  value       = azurerm_storage_account.{resource_name}.name
}}

output "{resource_name}_primary_blob_endpoint" {{
  description = "Primary blob endpoint of Azure Storage Account {resource_name}"
  value       = azurerm_storage_account.{resource_name}.primary_blob_endpoint
}}

output "{resource_name}_primary_access_key" {{
  description = "Primary access key of Azure Storage Account {resource_name}"
  value       = azurerm_storage_account.{resource_name}.primary_access_key
  sensitive   = true
}}

'''

                elif resource_type in ["sql", "azure_sql"]:
                    code += f'''output "{resource_name}_sql_server_id" {{
  description = "ID of Azure SQL Server for {resource_name}"
  value       = azurerm_mssql_server.{resource_name}_server.id
}}

output "{resource_name}_sql_server_fqdn" {{
  description = "Fully qualified domain name of Azure SQL Server for {resource_name}"
  value       = azurerm_mssql_server.{resource_name}_server.fully_qualified_domain_name
}}

output "{resource_name}_sql_database_id" {{
  description = "ID of Azure SQL Database {resource_name}"
  value       = azurerm_mssql_database.{resource_name}.id
}}

output "{resource_name}_sql_connection_string" {{
  description = "Connection string for Azure SQL Database {resource_name}"
  value       = "Server=${{azurerm_mssql_server.{resource_name}_server.fully_qualified_domain_name}};Database={resource_name};User Id=${{azurerm_mssql_server.{resource_name}_server.administrator_login}};Password=<your_password>;"
  sensitive   = true
}}

'''

        return code if code != "# Outputs\\n\\n" else "# No outputs defined\\n"

    def _generate_readme(self, resources: List) -> str:
        """Generate README with deployment instructions."""
        resource_count = len(resources)

        # Normalize resource types to avoid duplicates (EC2 vs aws_ec2)
        def normalize_type(rtype):
            """Normalize resource type for display."""
            if not rtype:
                return "unknown"
            rt = rtype.lower().replace(" ", "_")
            # Map to display names
            type_map = {
                "ec2": "aws_ec2",
                "aws_ec2": "aws_ec2",
                "s3": "aws_s3",
                "aws_s3": "aws_s3",
                "vpc": "aws_vpc",
                "aws_vpc": "aws_vpc",
                "vm": "azure_vm",
                "azure_vm": "azure_vm",
            }
            return type_map.get(rt, rt)

        # Get normalized resource types
        normalized_types = {}
        for r in resources:
            rtype = r.get("resource_type", "")
            normalized = normalize_type(rtype)
            normalized_types[normalized] = normalized_types.get(normalized, 0) + 1

        readme = f"""# Terraform Infrastructure Configuration

This configuration was auto-generated by the IaC Code Generator.

## Resources

This configuration will create **{resource_count}** resource{"s" if resource_count != 1 else ""}:

"""

        for rtype, count in normalized_types.items():
            readme += f"- {count} x {rtype}\n"

        readme += """

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured (if using AWS resources)
- Azure CLI configured (if using Azure resources)

## Deployment Steps

1. **Initialize Terraform:**
   ```bash
   terraform init
   ```

2. **Review the plan:**
   ```bash
   terraform plan
   ```

3. **Apply the configuration:**
   ```bash
   terraform apply
   ```

4. **Confirm** when prompted.

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

## Notes

- Review all resource configurations before deploying
- Ensure you have appropriate cloud provider credentials configured
- Some resources (like databases) contain sensitive information - use Terraform variables or secrets management in production
- Costs may apply for created resources

## Generated Files

- `provider.tf` - Provider configuration
- `variables.tf` - Input variables
- `main.tf` - Main resource definitions
- `outputs.tf` - Output values
"""

        return readme
