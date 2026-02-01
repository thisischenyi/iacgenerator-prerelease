"""Azure Terraform code validator and sanitizer.

This module provides validation and auto-correction for Azure-specific
Terraform code to ensure compatibility with Azure provider constraints.
"""

import re
from typing import Dict, List, Tuple


class AzureTerraformValidator:
    """Validator for Azure Terraform code."""

    # Azure resources that DO NOT support tags
    NO_TAGS_RESOURCES = {
        "azurerm_subnet",
        "azurerm_subnet_network_security_group_association",
        "azurerm_subnet_route_table_association",
        "azurerm_network_interface_security_group_association",
        "azurerm_virtual_network_peering",
    }

    # Azure resources that DO support tags
    TAGS_SUPPORTED_RESOURCES = {
        "azurerm_resource_group",
        "azurerm_virtual_network",
        "azurerm_network_security_group",
        "azurerm_network_interface",
        "azurerm_public_ip",
        "azurerm_virtual_machine",
        "azurerm_linux_virtual_machine",
        "azurerm_windows_virtual_machine",
        "azurerm_storage_account",
        "azurerm_mssql_server",
        "azurerm_mssql_database",
        "azurerm_sql_server",
        "azurerm_sql_database",
    }

    # VM resources that do NOT support inline data_disk blocks
    # (data disks must be separate azurerm_managed_disk resources)
    NO_DATA_DISK_INLINE = {
        "azurerm_linux_virtual_machine",
        "azurerm_windows_virtual_machine",
    }

    @classmethod
    def _find_matching_brace(cls, content: str, start: int) -> int:
        """Find the index of the matching closing brace."""
        depth = 0
        i = start
        while i < len(content):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1

    @classmethod
    def _remove_block_from_resource(cls, block: str, block_name: str) -> str:
        """Remove a named block (like 'tags' or 'data_disk') from a resource block."""
        # Pattern to match block_name = { ... } or block_name { ... }
        patterns = [
            rf"\n\s*{block_name}\s*=\s*\{{",  # block_name = {
            rf"\n\s*{block_name}\s*\{{",  # block_name {
        ]

        for pattern in patterns:
            while True:  # Remove all occurrences
                match = re.search(pattern, block)
                if not match:
                    break

                block_start = match.start()
                brace_start = match.end() - 1  # Position of opening {

                # Find matching closing brace
                brace_end = cls._find_matching_brace(block, brace_start)
                if brace_end == -1:
                    break

                # Remove the entire block
                block = block[:block_start] + block[brace_end + 1 :]

        return block

    @classmethod
    def _remove_tags_from_block(cls, block: str) -> str:
        """Remove tags = { ... } from a resource block."""
        return cls._remove_block_from_resource(block, "tags")

    @classmethod
    def _remove_data_disk_from_block(cls, block: str) -> str:
        """Remove data_disk { ... } blocks from a resource block."""
        return cls._remove_block_from_resource(block, "data_disk")

    @classmethod
    def validate_and_fix_main_tf(cls, main_tf_content: str) -> Tuple[str, List[str]]:
        """
        Validate and auto-fix main.tf for Azure resources.

        Args:
            main_tf_content: Content of main.tf file

        Returns:
            Tuple of (fixed_content, list_of_issues_fixed)
        """
        issues_fixed = []
        result = main_tf_content

        # Fix 1: Remove tags from resources that don't support them
        for resource_type in cls.NO_TAGS_RESOURCES:
            pattern = rf'resource\s+"{resource_type}"\s+"(\w+)"\s*\{{'
            matches = list(re.finditer(pattern, result))

            for match in reversed(matches):
                resource_name = match.group(1)
                block_start = match.start()
                brace_start = match.end() - 1

                brace_end = cls._find_matching_brace(result, brace_start)
                if brace_end == -1:
                    continue

                full_block = result[block_start : brace_end + 1]

                if re.search(r"\btags\s*=", full_block):
                    fixed_block = cls._remove_tags_from_block(full_block)

                    if fixed_block != full_block:
                        result = (
                            result[:block_start] + fixed_block + result[brace_end + 1 :]
                        )
                        issues_fixed.append(
                            f"Removed unsupported 'tags' from {resource_type}.{resource_name}"
                        )
                        print(
                            f"[AzureValidator] Removed tags from {resource_type}.{resource_name}"
                        )

        # Fix 2: Remove data_disk blocks from VM resources (must use separate resources)
        for resource_type in cls.NO_DATA_DISK_INLINE:
            pattern = rf'resource\s+"{resource_type}"\s+"(\w+)"\s*\{{'
            matches = list(re.finditer(pattern, result))

            for match in reversed(matches):
                resource_name = match.group(1)
                block_start = match.start()
                brace_start = match.end() - 1

                brace_end = cls._find_matching_brace(result, brace_start)
                if brace_end == -1:
                    continue

                full_block = result[block_start : brace_end + 1]

                if re.search(r"\bdata_disk\s*\{", full_block):
                    fixed_block = cls._remove_data_disk_from_block(full_block)

                    if fixed_block != full_block:
                        result = (
                            result[:block_start] + fixed_block + result[brace_end + 1 :]
                        )
                        issues_fixed.append(
                            f"Removed unsupported inline 'data_disk' from {resource_type}.{resource_name}"
                        )
                        print(
                            f"[AzureValidator] Removed data_disk from {resource_type}.{resource_name}"
                        )

        # Fix 3: Convert 'zones = ["1"]' to 'zone = "1"' for resources that only support single zone (string)
        # Affected resources: azurerm_linux_virtual_machine, azurerm_windows_virtual_machine, azurerm_managed_disk
        single_zone_resources = {
            "azurerm_linux_virtual_machine",
            "azurerm_windows_virtual_machine",
            "azurerm_managed_disk",
        }

        for resource_type in single_zone_resources:
            # Pattern to find zones = ["1"] inside the resource block
            # We use a non-greedy approach within the resource block
            pattern = rf'resource\s+"{resource_type}"\s+"(\w+)"\s*\{{'
            matches = list(re.finditer(pattern, result))

            for match in reversed(matches):
                resource_name = match.group(1)
                block_start = match.start()
                brace_start = match.end() - 1
                brace_end = cls._find_matching_brace(result, brace_start)

                if brace_end == -1:
                    continue

                full_block = result[block_start : brace_end + 1]

                # Look for zones = ["..."]
                zones_match = re.search(r'\bzones\s*=\s*\[\s*"(\d+)"\s*\]', full_block)
                if zones_match:
                    zone_val = zones_match.group(1)
                    # Replace with zone = "..."
                    fixed_block = (
                        full_block[: zones_match.start()]
                        + f'zone = "{zone_val}"'
                        + full_block[zones_match.end() :]
                    )

                    result = (
                        result[:block_start] + fixed_block + result[brace_end + 1 :]
                    )
                    issues_fixed.append(
                        f"Converted 'zones' list to 'zone' string for {resource_type}.{resource_name}"
                    )
                    print(
                        f"[AzureValidator] Fixed zones attribute for {resource_type}.{resource_name}"
                    )

        return result, issues_fixed

    @classmethod
    def validate_generated_files(cls, files: Dict[str, str]) -> Dict[str, str]:
        """
        Validate and auto-fix all generated Terraform files.

        Args:
            files: Dictionary of filename -> content

        Returns:
            Dictionary of filename -> fixed content
        """
        fixed_files = {}
        all_issues = []

        for filename, content in files.items():
            if filename == "main.tf":
                fixed_content, issues = cls.validate_and_fix_main_tf(content)
                fixed_files[filename] = fixed_content
                all_issues.extend(issues)
            else:
                fixed_files[filename] = content

        # Fix undeclared variables - scan main.tf for var.xxx references
        # and ensure they are declared in variables.tf
        if "main.tf" in fixed_files:
            variables_tf = fixed_files.get("variables.tf", "# Variables\n\n")
            fixed_variables_tf, var_issues = cls._fix_undeclared_variables(
                fixed_files["main.tf"], variables_tf
            )
            fixed_files["variables.tf"] = fixed_variables_tf
            all_issues.extend(var_issues)

        if all_issues:
            print(
                f"[AzureValidator] Fixed {len(all_issues)} Azure compatibility issues:"
            )
            for issue in all_issues:
                print(f"[AzureValidator]   - {issue}")

        return fixed_files

    @classmethod
    def _fix_undeclared_variables(
        cls, main_tf: str, variables_tf: str
    ) -> Tuple[str, List[str]]:
        """
        Find variables used in main.tf but not declared in variables.tf,
        and add declarations for them.

        Args:
            main_tf: Content of main.tf
            variables_tf: Content of variables.tf

        Returns:
            Tuple of (fixed_variables_tf, list_of_issues_fixed)
        """
        issues_fixed = []

        # Find all var.xxx references in main.tf
        var_pattern = r"\bvar\.(\w+)\b"
        used_vars = set(re.findall(var_pattern, main_tf))

        # Find all declared variables in variables.tf
        declared_pattern = r'variable\s+"(\w+)"'
        declared_vars = set(re.findall(declared_pattern, variables_tf))

        # Find undeclared variables
        undeclared = used_vars - declared_vars

        if not undeclared:
            return variables_tf, issues_fixed

        # Add declarations for undeclared variables
        new_declarations = []
        for var_name in sorted(undeclared):
            # Determine variable type and add appropriate declaration
            var_config = cls._get_variable_config(var_name)
            new_declarations.append(var_config)
            issues_fixed.append(f"Added missing variable declaration: {var_name}")
            print(f"[AzureValidator] Added missing variable: {var_name}")

        # Append new declarations to variables.tf
        if new_declarations:
            variables_tf = (
                variables_tf.rstrip() + "\n\n" + "\n\n".join(new_declarations) + "\n"
            )

        return variables_tf, issues_fixed

    @classmethod
    def _get_variable_config(cls, var_name: str) -> str:
        """
        Get the variable declaration for a given variable name.
        Uses sensible defaults based on common variable naming patterns.

        Args:
            var_name: Name of the variable

        Returns:
            Variable declaration block as string
        """
        # Common variable patterns and their configurations
        sensitive_vars = {"password", "secret", "key", "token", "credential"}

        # Check if variable should be marked as sensitive
        is_sensitive = any(s in var_name.lower() for s in sensitive_vars)

        # Determine description based on variable name
        description = var_name.replace("_", " ").title()

        if is_sensitive:
            return f'''variable "{var_name}" {{
  description = "{description}"
  type        = string
  sensitive   = true
}}'''
        else:
            return f'''variable "{var_name}" {{
  description = "{description}"
  type        = string
}}'''
