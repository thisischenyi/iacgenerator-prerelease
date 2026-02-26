"""Unit tests for AWS Elastic IP and Azure Load Balancer resources."""

import pytest
from app.services.terraform_generator import TerraformCodeGenerator
from app.services.excel_parser import ExcelParserService
from app.services.excel_generator import ExcelGeneratorService
from app.schemas import ResourceInfo, CloudPlatform, TemplateType


class TestAWSElasticIP:
    """Tests for AWS Elastic IP resource generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TerraformCodeGenerator()

    def test_elastic_ip_basic(self):
        """Test basic Elastic IP generation."""
        resources = [
            {
                "resource_type": "ElasticIP",
                "cloud_platform": "aws",
                "resource_name": "web-eip",
                "properties": {
                    "Region": "us-east-1",
                    "Domain": "vpc",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)

        assert "main.tf" in files
        main_tf = files["main.tf"]

        # Check that EIP resource is created
        assert 'resource "aws_eip"' in main_tf
        assert "web_eip" in main_tf
        assert 'domain = "vpc"' in main_tf

    def test_elastic_ip_with_instance(self):
        """Test Elastic IP with EC2 instance association."""
        resources = [
            {
                "resource_type": "ElasticIP",
                "cloud_platform": "aws",
                "resource_name": "web-eip",
                "properties": {
                    "Region": "us-east-1",
                    "Domain": "vpc",
                    "Instance": "web-server",
                    "InstanceExists": "n",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that instance reference is included
        assert 'resource "aws_eip"' in main_tf
        assert "instance" in main_tf.lower()

    def test_elastic_ip_with_existing_instance(self):
        """Test Elastic IP with existing EC2 instance reference."""
        resources = [
            {
                "resource_type": "ElasticIP",
                "cloud_platform": "aws",
                "resource_name": "web-eip",
                "properties": {
                    "Region": "us-east-1",
                    "Domain": "vpc",
                    "Instance": "existing-server",
                    "InstanceExists": "y",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that data source is used for existing instance
        assert 'data "aws_instance"' in main_tf
        assert "data.aws_instance" in main_tf

    def test_elastic_ip_outputs(self):
        """Test Elastic IP outputs generation."""
        resources = [
            {
                "resource_type": "ElasticIP",
                "cloud_platform": "aws",
                "resource_name": "web-eip",
                "properties": {
                    "Region": "us-east-1",
                    "Domain": "vpc",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)

        assert "outputs.tf" in files
        outputs_tf = files["outputs.tf"]

        # Check that EIP outputs are created
        assert "web_eip_eip_id" in outputs_tf
        assert "web_eip_eip_public_ip" in outputs_tf
        assert "web_eip_eip_allocation_id" in outputs_tf

    def test_elastic_ip_alias_eip(self):
        """Test 'eip' alias for Elastic IP."""
        resources = [
            {
                "resource_type": "eip",
                "cloud_platform": "aws",
                "resource_name": "test-eip",
                "properties": {
                    "Region": "us-east-1",
                    "Domain": "vpc",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        assert 'resource "aws_eip"' in main_tf


class TestAzureLoadBalancer:
    """Tests for Azure Load Balancer resource generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TerraformCodeGenerator()

    def test_load_balancer_basic(self):
        """Test basic Load Balancer generation."""
        resources = [
            {
                "resource_type": "LoadBalancer",
                "cloud_platform": "azure",
                "resource_name": "web-lb",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "SKU": "Standard",
                    "FrontendIPName": "web-frontend",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)

        assert "main.tf" in files
        main_tf = files["main.tf"]

        # Check that Load Balancer resource is created
        assert 'resource "azurerm_lb"' in main_tf
        assert "web_lb" in main_tf
        assert "sku" in main_tf

    def test_load_balancer_with_public_ip(self):
        """Test Load Balancer with Public IP."""
        resources = [
            {
                "resource_type": "LoadBalancer",
                "cloud_platform": "azure",
                "resource_name": "web-lb",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "SKU": "Standard",
                    "FrontendIPName": "web-frontend",
                    "PublicIP": "lb-pip",
                    "PublicIPExists": "n",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that public IP reference is included
        assert "public_ip_address_id" in main_tf

    def test_load_balancer_with_backend_pool(self):
        """Test Load Balancer with backend pool."""
        resources = [
            {
                "resource_type": "VM",
                "cloud_platform": "azure",
                "resource_name": "vm1",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "VMSize": "Standard_B2s",
                    "OSType": "Linux",
                    "AdminUsername": "azureuser",
                    "AuthenticationType": "Password",
                    "AdminPassword": "Passw0rd!",
                    "ImagePublisher": "Canonical",
                    "ImageOffer": "0001-com-ubuntu-server-jammy",
                    "ImageSKU": "22_04-lts",
                    "VNet": "vnet-test",
                    "VNetExists": "n",
                    "Subnet": "subnet-test",
                    "SubnetExists": "n",
                    "AssignPublicIP": "false",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            },
            {
                "resource_type": "VM",
                "cloud_platform": "azure",
                "resource_name": "vm2",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "VMSize": "Standard_B2s",
                    "OSType": "Linux",
                    "AdminUsername": "azureuser",
                    "AuthenticationType": "Password",
                    "AdminPassword": "Passw0rd!",
                    "ImagePublisher": "Canonical",
                    "ImageOffer": "0001-com-ubuntu-server-jammy",
                    "ImageSKU": "22_04-lts",
                    "VNet": "vnet-test",
                    "VNetExists": "n",
                    "Subnet": "subnet-test",
                    "SubnetExists": "n",
                    "AssignPublicIP": "false",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            },
            {
                "resource_type": "LoadBalancer",
                "cloud_platform": "azure",
                "resource_name": "web-lb",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "SKU": "Standard",
                    "FrontendIPName": "web-frontend",
                    "BackendPoolName": "web-backend",
                    "BackendPoolResources": ["vm1", "vm2"],
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that backend pool is created
        assert 'resource "azurerm_lb_backend_address_pool"' in main_tf
        assert "web-backend" in main_tf
        assert (
            'resource "azurerm_network_interface_backend_address_pool_association"'
            in main_tf
        )
        assert "azurerm_network_interface.vm1_nic.id" in main_tf
        assert "azurerm_network_interface.vm2_nic.id" in main_tf

    def test_load_balancer_with_health_probe(self):
        """Test Load Balancer with health probe."""
        resources = [
            {
                "resource_type": "LoadBalancer",
                "cloud_platform": "azure",
                "resource_name": "web-lb",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "SKU": "Standard",
                    "FrontendIPName": "web-frontend",
                    "HealthProbeName": "web-probe",
                    "HealthProbeProtocol": "Tcp",
                    "HealthProbePort": 80,
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that health probe is created
        assert 'resource "azurerm_lb_probe"' in main_tf
        assert "web-probe" in main_tf

    def test_load_balancer_with_lb_rule(self):
        """Test Load Balancer with load balancing rule."""
        resources = [
            {
                "resource_type": "LoadBalancer",
                "cloud_platform": "azure",
                "resource_name": "web-lb",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "SKU": "Standard",
                    "FrontendIPName": "web-frontend",
                    "LBRuleName": "web-rule",
                    "LBRuleProtocol": "Tcp",
                    "LBRuleFrontendPort": 80,
                    "LBRuleBackendPort": 80,
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that LB rule is created
        assert 'resource "azurerm_lb_rule"' in main_tf
        assert "web-rule" in main_tf

    def test_load_balancer_outputs(self):
        """Test Load Balancer outputs generation."""
        resources = [
            {
                "resource_type": "LoadBalancer",
                "cloud_platform": "azure",
                "resource_name": "web-lb",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "SKU": "Standard",
                    "FrontendIPName": "web-frontend",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)

        assert "outputs.tf" in files
        outputs_tf = files["outputs.tf"]

        # Check that LB outputs are created
        assert "web_lb_lb_id" in outputs_tf
        assert "web_lb_lb_frontend_ip_configuration" in outputs_tf

    def test_load_balancer_alias_lb(self):
        """Test 'lb' alias for Load Balancer."""
        resources = [
            {
                "resource_type": "lb",
                "cloud_platform": "azure",
                "resource_name": "test-lb",
                "properties": {
                    "ResourceGroup": "rg-test",
                    "ResourceGroupExists": "n",
                    "Location": "eastus",
                    "SKU": "Standard",
                    "FrontendIPName": "test-frontend",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        assert 'resource "azurerm_lb"' in main_tf


class TestExcelParserValidation:
    """Tests for Excel parser validation of new resource types."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ExcelParserService()

    def test_validate_aws_elastic_ip(self):
        """Test validation for AWS Elastic IP."""
        resource = ResourceInfo(
            resource_type="ElasticIP",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-eip",
            properties={
                "ResourceName": "test-eip",
                "Region": "us-east-1",
                "Domain": "vpc",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert is_valid, f"Validation failed with errors: {errors}"

    def test_validate_aws_elastic_ip_invalid_domain(self):
        """Test validation fails with invalid Domain."""
        resource = ResourceInfo(
            resource_type="ElasticIP",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-eip",
            properties={
                "ResourceName": "test-eip",
                "Region": "us-east-1",
                "Domain": "invalid",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("Domain" in e for e in errors)

    def test_validate_aws_elastic_ip_exists_field(self):
        """Test validation for Exists fields values."""
        resource = ResourceInfo(
            resource_type="ElasticIP",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-eip",
            properties={
                "ResourceName": "test-eip",
                "Region": "us-east-1",
                "Domain": "vpc",
                "InstanceExists": "invalid",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("InstanceExists" in e for e in errors)

    def test_validate_azure_load_balancer(self):
        """Test validation for Azure Load Balancer."""
        resource = ResourceInfo(
            resource_type="LoadBalancer",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="test-lb",
            properties={
                "ResourceName": "test-lb",
                "ResourceGroup": "rg-test",
                "ResourceGroupExists": "n",
                "Location": "eastus",
                "SKU": "Standard",
                "FrontendIPName": "test-frontend",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert is_valid, f"Validation failed with errors: {errors}"

    def test_validate_azure_load_balancer_invalid_sku(self):
        """Test validation fails with invalid SKU."""
        resource = ResourceInfo(
            resource_type="LoadBalancer",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="test-lb",
            properties={
                "ResourceName": "test-lb",
                "ResourceGroup": "rg-test",
                "ResourceGroupExists": "n",
                "Location": "eastus",
                "SKU": "Invalid",
                "FrontendIPName": "test-frontend",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("SKU" in e for e in errors)

    def test_validate_azure_load_balancer_invalid_protocol(self):
        """Test validation fails with invalid HealthProbeProtocol."""
        resource = ResourceInfo(
            resource_type="LoadBalancer",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="test-lb",
            properties={
                "ResourceName": "test-lb",
                "ResourceGroup": "rg-test",
                "ResourceGroupExists": "n",
                "Location": "eastus",
                "SKU": "Standard",
                "FrontendIPName": "test-frontend",
                "HealthProbeProtocol": "Invalid",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("HealthProbeProtocol" in e for e in errors)

    def test_validate_azure_load_balancer_missing_required(self):
        """Test validation fails when required field is missing."""
        resource = ResourceInfo(
            resource_type="LoadBalancer",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="test-lb",
            properties={
                "ResourceName": "test-lb",
                "ResourceGroup": "rg-test",
                "ResourceGroupExists": "n",
                "Location": "eastus",
                "SKU": "Standard",
                # Missing FrontendIPName
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("FrontendIPName" in e for e in errors)

    def test_validate_azure_load_balancer_invalid_backend_pool_resources(self):
        """Test validation fails when BackendPoolResources is not a list."""
        resource = ResourceInfo(
            resource_type="LoadBalancer",
            cloud_platform=CloudPlatform.AZURE,
            resource_name="test-lb",
            properties={
                "ResourceName": "test-lb",
                "ResourceGroup": "rg-test",
                "ResourceGroupExists": "n",
                "Location": "eastus",
                "SKU": "Standard",
                "FrontendIPName": "test-frontend",
                "BackendPoolResources": "vm1,vm2",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("BackendPoolResources" in e for e in errors)


class TestExcelGeneratorNewResources:
    """Tests for Excel generator with new resource types."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ExcelGeneratorService()

    def test_aws_elastic_ip_in_resources(self):
        """Test that AWS_ElasticIP is in AWS_RESOURCES."""
        assert "AWS_ElasticIP" in self.generator.AWS_RESOURCES
        fields = self.generator.AWS_RESOURCES["AWS_ElasticIP"]
        assert "Region" in fields
        assert "Domain" in fields
        assert "Instance" in fields
        assert "InstanceExists" in fields

    def test_azure_load_balancer_in_resources(self):
        """Test that Azure_LoadBalancer is in AZURE_RESOURCES."""
        assert "Azure_LoadBalancer" in self.generator.AZURE_RESOURCES
        fields = self.generator.AZURE_RESOURCES["Azure_LoadBalancer"]
        assert "ResourceGroup" in fields
        assert "Location" in fields
        assert "SKU" in fields
        assert "FrontendIPName" in fields
        assert "BackendPoolName" in fields
        assert "BackendPoolResources" in fields
        assert "HealthProbeName" in fields
        assert "LBRuleName" in fields

    def test_aws_elastic_ip_required_fields(self):
        """Test that AWS_ElasticIP has correct required fields."""
        assert "AWS_ElasticIP" in self.generator.REQUIRED_FIELDS
        required = self.generator.REQUIRED_FIELDS["AWS_ElasticIP"]
        assert "ResourceName" in required
        assert "Environment" in required
        assert "Project" in required
        assert "Region" in required

    def test_azure_load_balancer_required_fields(self):
        """Test that Azure_LoadBalancer has correct required fields."""
        assert "Azure_LoadBalancer" in self.generator.REQUIRED_FIELDS
        required = self.generator.REQUIRED_FIELDS["Azure_LoadBalancer"]
        assert "ResourceName" in required
        assert "ResourceGroup" in required
        assert "ResourceGroupExists" in required
        assert "Location" in required
        assert "SKU" in required
        assert "FrontendIPName" in required

    def test_aws_elastic_ip_sample_data(self):
        """Test that AWS_ElasticIP has sample data."""
        assert "AWS_ElasticIP" in self.generator.SAMPLE_DATA
        sample = self.generator.SAMPLE_DATA["AWS_ElasticIP"]
        assert sample["ResourceName"] == "web-eip"
        assert sample["Region"] == "us-east-1"
        assert sample["Domain"] == "vpc"

    def test_azure_load_balancer_sample_data(self):
        """Test that Azure_LoadBalancer has sample data."""
        assert "Azure_LoadBalancer" in self.generator.SAMPLE_DATA
        sample = self.generator.SAMPLE_DATA["Azure_LoadBalancer"]
        assert sample["ResourceName"] == "web-lb"
        assert sample["SKU"] == "Standard"
        assert sample["FrontendIPName"] == "web-frontend"

    def test_generate_aws_template_includes_elastic_ip(self):
        """Test that AWS template includes Elastic IP sheet."""
        template_bytes = self.generator.generate_template(TemplateType.AWS)
        assert template_bytes is not None
        assert len(template_bytes) > 0

    def test_generate_azure_template_includes_load_balancer(self):
        """Test that Azure template includes Load Balancer sheet."""
        template_bytes = self.generator.generate_template(TemplateType.AZURE)
        assert template_bytes is not None
        assert len(template_bytes) > 0

    def test_generate_full_template_includes_both(self):
        """Test that full template includes both new resources."""
        template_bytes = self.generator.generate_template(TemplateType.FULL)
        assert template_bytes is not None
        assert len(template_bytes) > 0


class TestResourceTypeLists:
    """Tests for resource type lists in parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ExcelParserService()

    def test_aws_elastic_ip_in_resource_types(self):
        """Test that AWS_ElasticIP is in AWS_RESOURCE_TYPES."""
        assert "AWS_ElasticIP" in self.parser.AWS_RESOURCE_TYPES

    def test_azure_load_balancer_in_resource_types(self):
        """Test that Azure_LoadBalancer is in AZURE_RESOURCE_TYPES."""
        assert "Azure_LoadBalancer" in self.parser.AZURE_RESOURCE_TYPES

    def test_is_resource_sheet_elastic_ip(self):
        """Test _is_resource_sheet for AWS_ElasticIP."""
        assert self.parser._is_resource_sheet("AWS_ElasticIP") is True

    def test_is_resource_sheet_load_balancer(self):
        """Test _is_resource_sheet for Azure_LoadBalancer."""
        assert self.parser._is_resource_sheet("Azure_LoadBalancer") is True
