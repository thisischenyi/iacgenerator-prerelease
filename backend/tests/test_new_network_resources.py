"""Unit tests for new network resources: Internet Gateway, NAT Gateway, Public IP."""

import pytest
from app.services.terraform_generator import TerraformCodeGenerator
from app.services.excel_parser import ExcelParserService
from app.schemas import ResourceInfo, CloudPlatform


class TestAWSInternetGateway:
    """Tests for AWS Internet Gateway resource generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TerraformCodeGenerator()

    def test_internet_gateway_basic(self):
        """Test basic Internet Gateway generation."""
        resources = [
            {
                "resource_type": "InternetGateway",
                "cloud_platform": "aws",
                "resource_name": "main-igw",
                "properties": {
                    "Region": "us-east-1",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)

        assert "main.tf" in files
        main_tf = files["main.tf"]

        # Check that internet gateway resource is created
        assert 'resource "aws_internet_gateway"' in main_tf
        assert "main_igw" in main_tf
        assert "vpc_id" in main_tf

    def test_internet_gateway_with_existing_vpc(self):
        """Test Internet Gateway with existing VPC reference."""
        resources = [
            {
                "resource_type": "InternetGateway",
                "cloud_platform": "aws",
                "resource_name": "test-igw",
                "properties": {
                    "Region": "us-east-1",
                    "VPC": "existing-vpc",
                    "VPCExists": "y",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that data source is used for existing VPC
        assert 'data "aws_vpc"' in main_tf
        assert "data.aws_vpc" in main_tf

    def test_internet_gateway_outputs(self):
        """Test Internet Gateway outputs generation."""
        resources = [
            {
                "resource_type": "InternetGateway",
                "cloud_platform": "aws",
                "resource_name": "main-igw",
                "properties": {
                    "Region": "us-east-1",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)

        assert "outputs.tf" in files
        outputs_tf = files["outputs.tf"]

        # Check that IGW output is created
        assert "main_igw_igw_id" in outputs_tf
        assert "aws_internet_gateway" in outputs_tf


class TestAWSNATGateway:
    """Tests for AWS NAT Gateway resource generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TerraformCodeGenerator()

    def test_nat_gateway_public(self):
        """Test public NAT Gateway generation."""
        resources = [
            {
                "resource_type": "NATGateway",
                "cloud_platform": "aws",
                "resource_name": "main-nat",
                "properties": {
                    "Region": "us-east-1",
                    "Subnet": "public-subnet",
                    "SubnetExists": "n",
                    "ConnectivityType": "public",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that NAT Gateway and EIP are created
        assert 'resource "aws_nat_gateway"' in main_tf
        assert 'resource "aws_eip"' in main_tf
        assert "main_nat" in main_tf
        assert "allocation_id" in main_tf

    def test_nat_gateway_private(self):
        """Test private NAT Gateway generation (no EIP)."""
        resources = [
            {
                "resource_type": "NATGateway",
                "cloud_platform": "aws",
                "resource_name": "private-nat",
                "properties": {
                    "Region": "us-east-1",
                    "Subnet": "private-subnet",
                    "SubnetExists": "n",
                    "ConnectivityType": "private",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that NAT Gateway is created without EIP
        assert 'resource "aws_nat_gateway"' in main_tf
        assert 'connectivity_type = "private"' in main_tf

    def test_nat_gateway_outputs(self):
        """Test NAT Gateway outputs generation."""
        resources = [
            {
                "resource_type": "NATGateway",
                "cloud_platform": "aws",
                "resource_name": "main-nat",
                "properties": {
                    "Region": "us-east-1",
                    "Subnet": "public-subnet",
                    "SubnetExists": "n",
                    "ConnectivityType": "public",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        outputs_tf = files["outputs.tf"]

        # Check that NAT Gateway outputs are created
        assert "main_nat_nat_gateway_id" in outputs_tf
        assert "main_nat_nat_gateway_public_ip" in outputs_tf


class TestAzurePublicIP:
    """Tests for Azure Public IP resource generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TerraformCodeGenerator()

    def test_public_ip_basic(self):
        """Test basic Public IP generation."""
        resources = [
            {
                "resource_type": "PublicIP",
                "cloud_platform": "azure",
                "resource_name": "web-pip",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "AllocationMethod": "Static",
                    "SKU": "Standard",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that Public IP resource is created
        assert 'resource "azurerm_public_ip"' in main_tf
        assert "web_pip" in main_tf
        assert 'allocation_method   = "Static"' in main_tf
        assert 'sku                 = "Standard"' in main_tf

    def test_public_ip_with_zone(self):
        """Test Public IP with availability zone."""
        resources = [
            {
                "resource_type": "PublicIP",
                "cloud_platform": "azure",
                "resource_name": "zone-pip",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "y",
                    "Location": "eastus",
                    "AllocationMethod": "Static",
                    "SKU": "Standard",
                    "AvailabilityZone": "1",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that zones are configured
        assert "zones" in main_tf
        assert '"1"' in main_tf

    def test_public_ip_outputs(self):
        """Test Public IP outputs generation."""
        resources = [
            {
                "resource_type": "PublicIP",
                "cloud_platform": "azure",
                "resource_name": "web-pip",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "AllocationMethod": "Static",
                    "SKU": "Standard",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        outputs_tf = files["outputs.tf"]

        # Check that Public IP outputs are created
        assert "web_pip_public_ip_id" in outputs_tf
        assert "web_pip_public_ip_address" in outputs_tf


class TestAzureNATGateway:
    """Tests for Azure NAT Gateway resource generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TerraformCodeGenerator()

    def test_nat_gateway_basic(self):
        """Test basic Azure NAT Gateway generation."""
        resources = [
            {
                "resource_type": "NATGateway",
                "cloud_platform": "azure",
                "resource_name": "main-nat-gw",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "SKU": "Standard",
                    "IdleTimeoutMinutes": 10,
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that NAT Gateway resource is created
        assert 'resource "azurerm_nat_gateway"' in main_tf
        assert "main_nat_gw" in main_tf
        assert "sku_name" in main_tf

    def test_nat_gateway_with_public_ip(self):
        """Test Azure NAT Gateway with Public IP association."""
        resources = [
            {
                "resource_type": "NATGateway",
                "cloud_platform": "azure",
                "resource_name": "test-nat-gw",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "SKU": "Standard",
                    "PublicIP": "nat-pip",
                    "PublicIPExists": "n",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that Public IP association is created
        assert 'resource "azurerm_nat_gateway_public_ip_association"' in main_tf

    def test_nat_gateway_with_subnet(self):
        """Test Azure NAT Gateway with Subnet association."""
        resources = [
            {
                "resource_type": "NATGateway",
                "cloud_platform": "azure",
                "resource_name": "test-nat-gw",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "SKU": "Standard",
                    "Subnet": "private-subnet",
                    "SubnetExists": "n",
                    "VNet": "main-vnet",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that Subnet association is created
        assert 'resource "azurerm_subnet_nat_gateway_association"' in main_tf

    def test_nat_gateway_outputs(self):
        """Test Azure NAT Gateway outputs generation."""
        resources = [
            {
                "resource_type": "NATGateway",
                "cloud_platform": "azure",
                "resource_name": "main-nat-gw",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "SKU": "Standard",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        outputs_tf = files["outputs.tf"]

        # Check that NAT Gateway outputs are created
        assert "main_nat_gw_nat_gateway_id" in outputs_tf


class TestExcelParserValidation:
    """Tests for Excel parser validation of new resource types."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ExcelParserService()

    def test_validate_aws_internet_gateway(self):
        """Test validation for AWS Internet Gateway."""
        resource = ResourceInfo(
            resource_type="InternetGateway",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-igw",
            properties={
                "ResourceName": "test-igw",
                "Region": "us-east-1",
                "VPC": "main-vpc",
                "VPCExists": "n",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert is_valid, f"Validation failed with errors: {errors}"

    def test_validate_aws_internet_gateway_missing_vpc(self):
        """Test validation fails when VPC is missing."""
        resource = ResourceInfo(
            resource_type="InternetGateway",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-igw",
            properties={
                "ResourceName": "test-igw",
                "Region": "us-east-1",
                "VPCExists": "n",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("VPC" in e for e in errors)

    def test_validate_aws_nat_gateway(self):
        """Test validation for AWS NAT Gateway."""
        resource = ResourceInfo(
            resource_type="NATGateway",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-nat",
            properties={
                "ResourceName": "test-nat",
                "Region": "us-east-1",
                "Subnet": "public-subnet",
                "SubnetExists": "n",
                "ConnectivityType": "public",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert is_valid, f"Validation failed with errors: {errors}"

    def test_validate_azure_public_ip(self):
        """Test validation for Azure Public IP."""
        resource = ResourceInfo(
            resource_type="PublicIP",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="test-pip",
            properties={
                "ResourceName": "test-pip",
                "ResourceGroup": "rg-test",
                "ResourceGroupExists": "n",
                "Location": "eastus",
                "AllocationMethod": "Static",
                "SKU": "Standard",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert is_valid, f"Validation failed with errors: {errors}"

    def test_validate_azure_public_ip_invalid_sku(self):
        """Test validation fails with invalid SKU."""
        resource = ResourceInfo(
            resource_type="PublicIP",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="test-pip",
            properties={
                "ResourceName": "test-pip",
                "ResourceGroup": "rg-test",
                "ResourceGroupExists": "n",
                "Location": "eastus",
                "AllocationMethod": "Static",
                "SKU": "Invalid",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("SKU" in e for e in errors)

    def test_validate_azure_nat_gateway(self):
        """Test validation for Azure NAT Gateway."""
        resource = ResourceInfo(
            resource_type="NATGateway",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="test-nat-gw",
            properties={
                "ResourceName": "test-nat-gw",
                "ResourceGroup": "rg-test",
                "ResourceGroupExists": "n",
                "Location": "eastus",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert is_valid, f"Validation failed with errors: {errors}"


class TestTypeAliases:
    """Tests for resource type aliases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TerraformCodeGenerator()

    def test_igw_alias(self):
        """Test 'igw' alias for Internet Gateway."""
        resources = [
            {
                "resource_type": "igw",
                "cloud_platform": "aws",
                "resource_name": "test-igw",
                "properties": {
                    "Region": "us-east-1",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        assert 'resource "aws_internet_gateway"' in main_tf

    def test_pip_alias(self):
        """Test 'pip' alias for Azure Public IP."""
        resources = [
            {
                "resource_type": "pip",
                "cloud_platform": "azure",
                "resource_name": "test-pip",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "AllocationMethod": "Static",
                    "SKU": "Standard",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        assert 'resource "azurerm_public_ip"' in main_tf

    def test_nat_gateway_alias_aws(self):
        """Test 'nat_gateway' alias resolves to AWS for AWS platform."""
        resources = [
            {
                "resource_type": "nat_gateway",
                "cloud_platform": "aws",
                "resource_name": "test-nat",
                "properties": {
                    "Region": "us-east-1",
                    "Subnet": "public-subnet",
                    "SubnetExists": "n",
                    "ConnectivityType": "public",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        assert 'resource "aws_nat_gateway"' in main_tf

    def test_nat_gateway_alias_azure(self):
        """Test 'nat_gateway' alias resolves to Azure for Azure platform."""
        resources = [
            {
                "resource_type": "nat_gateway",
                "cloud_platform": "azure",
                "resource_name": "test-nat",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "SKU": "Standard",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        assert 'resource "azurerm_nat_gateway"' in main_tf
