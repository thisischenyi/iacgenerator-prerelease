"""Unit tests for AWS Load Balancer and Target Group resources."""

import pytest
from app.services.terraform_generator import TerraformCodeGenerator
from app.services.excel_parser import ExcelParserService
from app.services.excel_generator import ExcelGeneratorService
from app.schemas import ResourceInfo, CloudPlatform, TemplateType


class TestAWSLoadBalancer:
    """Tests for AWS Load Balancer (ALB/NLB) resource generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TerraformCodeGenerator()

    def test_load_balancer_alb_basic(self):
        """Test basic ALB generation."""
        resources = [
            {
                "resource_type": "LoadBalancer",
                "cloud_platform": "aws",
                "resource_name": "web-alb",
                "properties": {
                    "Region": "us-east-1",
                    "Type": "application",
                    "Scheme": "internet-facing",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "Subnets": '["public-subnet-1", "public-subnet-2"]',
                    "SubnetExists": "n",
                    "SecurityGroups": '["web-sg"]',
                    "SecurityGroupsExist": "n",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)

        assert "main.tf" in files
        main_tf = files["main.tf"]

        # Check that ALB resource is created
        assert 'resource "aws_lb"' in main_tf
        assert "web_alb" in main_tf
        assert 'load_balancer_type = "application"' in main_tf
        assert "security_groups" in main_tf

    def test_load_balancer_nlb_basic(self):
        """Test basic NLB generation."""
        resources = [
            {
                "resource_type": "LoadBalancer",
                "cloud_platform": "aws",
                "resource_name": "app-nlb",
                "properties": {
                    "Region": "us-east-1",
                    "Type": "network",
                    "Scheme": "internal",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "Subnets": '["private-subnet-1"]',
                    "SubnetExists": "n",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that NLB resource is created without security groups
        assert 'resource "aws_lb"' in main_tf
        assert "app_nlb" in main_tf
        assert 'load_balancer_type = "network"' in main_tf
        assert "scheme" in main_tf and "internal" in main_tf

    def test_load_balancer_with_listener(self):
        """Test ALB with listener and target group reference."""
        resources = [
            {
                "resource_type": "LoadBalancer",
                "cloud_platform": "aws",
                "resource_name": "web-alb",
                "properties": {
                    "Region": "us-east-1",
                    "Type": "application",
                    "Scheme": "internet-facing",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "Subnets": '["public-subnet-1", "public-subnet-2"]',
                    "SubnetExists": "n",
                    "SecurityGroups": '["web-sg"]',
                    "SecurityGroupsExist": "n",
                    "ListenerProtocol": "HTTP",
                    "ListenerPort": 80,
                    "ListenerTargetGroup": "web-tg",
                    "ListenerTargetGroupExists": "n",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that listener is created
        assert 'resource "aws_lb_listener"' in main_tf
        assert "web_alb_listener" in main_tf
        assert "port" in main_tf
        assert "protocol" in main_tf
        assert "target_group_arn" in main_tf

    def test_load_balancer_with_existing_vpc(self):
        """Test ALB with existing VPC reference."""
        resources = [
            {
                "resource_type": "LoadBalancer",
                "cloud_platform": "aws",
                "resource_name": "web-alb",
                "properties": {
                    "Region": "us-east-1",
                    "Type": "application",
                    "Scheme": "internet-facing",
                    "VPC": "existing-vpc",
                    "VPCExists": "y",
                    "Subnets": '["public-subnet-1"]',
                    "SubnetExists": "y",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that data sources are used
        assert 'data "aws_vpc"' in main_tf
        assert 'data "aws_subnet"' in main_tf
        assert "data.aws_vpc" in main_tf
        assert "data.aws_subnet" in main_tf

    def test_load_balancer_outputs(self):
        """Test Load Balancer outputs generation."""
        resources = [
            {
                "resource_type": "LoadBalancer",
                "cloud_platform": "aws",
                "resource_name": "web-alb",
                "properties": {
                    "Region": "us-east-1",
                    "Type": "application",
                    "Scheme": "internet-facing",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "Subnets": '["public-subnet-1"]',
                    "SubnetExists": "n",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)

        assert "outputs.tf" in files
        outputs_tf = files["outputs.tf"]

        # Check that LB outputs are created
        assert "web_alb_lb_arn" in outputs_tf
        assert "web_alb_lb_dns_name" in outputs_tf
        assert "web_alb_lb_id" in outputs_tf
        assert "web_alb_lb_zone_id" in outputs_tf

    def test_load_balancer_alias_alb(self):
        """Test 'alb' alias for Application Load Balancer."""
        resources = [
            {
                "resource_type": "alb",
                "cloud_platform": "aws",
                "resource_name": "test-alb",
                "properties": {
                    "Region": "us-east-1",
                    "Type": "application",
                    "Scheme": "internet-facing",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "Subnets": '["public-subnet-1"]',
                    "SubnetExists": "n",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        assert 'resource "aws_lb"' in main_tf

    def test_load_balancer_alias_nlb(self):
        """Test 'nlb' alias for Network Load Balancer."""
        resources = [
            {
                "resource_type": "nlb",
                "cloud_platform": "aws",
                "resource_name": "test-nlb",
                "properties": {
                    "Region": "us-east-1",
                    "Type": "network",
                    "Scheme": "internal",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "Subnets": '["private-subnet-1"]',
                    "SubnetExists": "n",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        assert 'resource "aws_lb"' in main_tf


class TestAWSTargetGroup:
    """Tests for AWS Target Group resource generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TerraformCodeGenerator()

    def test_target_group_basic(self):
        """Test basic Target Group generation."""
        resources = [
            {
                "resource_type": "TargetGroup",
                "cloud_platform": "aws",
                "resource_name": "web-tg",
                "properties": {
                    "Region": "us-east-1",
                    "Port": 80,
                    "Protocol": "HTTP",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "TargetType": "instance",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)

        assert "main.tf" in files
        main_tf = files["main.tf"]

        # Check that Target Group resource is created
        assert 'resource "aws_lb_target_group"' in main_tf
        assert "web_tg" in main_tf
        assert "port" in main_tf
        assert "protocol" in main_tf

    def test_target_group_with_health_check(self):
        """Test Target Group with health check configuration."""
        resources = [
            {
                "resource_type": "TargetGroup",
                "cloud_platform": "aws",
                "resource_name": "web-tg",
                "properties": {
                    "Region": "us-east-1",
                    "Port": 80,
                    "Protocol": "HTTP",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "TargetType": "instance",
                    "HealthCheckProtocol": "HTTP",
                    "HealthCheckPort": "traffic-port",
                    "HealthCheckPath": "/health",
                    "HealthCheckInterval": 30,
                    "HealthyThreshold": 3,
                    "UnhealthyThreshold": 3,
                    "HealthCheckTimeout": 5,
                    "SuccessCode": "200-299",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that health check is configured
        assert "health_check" in main_tf
        assert "path" in main_tf
        assert "interval" in main_tf
        assert "healthy_threshold" in main_tf

    def test_target_group_with_targets(self):
        """Test Target Group with target attachments."""
        resources = [
            {
                "resource_type": "TargetGroup",
                "cloud_platform": "aws",
                "resource_name": "web-tg",
                "properties": {
                    "Region": "us-east-1",
                    "Port": 80,
                    "Protocol": "HTTP",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "TargetType": "instance",
                    "Targets": '[{"Id": "i-1234567890abcdef0", "Port": 80}]',
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that target attachment is created
        assert 'resource "aws_lb_target_group_attachment"' in main_tf

    def test_target_group_with_stickiness(self):
        """Test Target Group with stickiness configuration."""
        resources = [
            {
                "resource_type": "TargetGroup",
                "cloud_platform": "aws",
                "resource_name": "web-tg",
                "properties": {
                    "Region": "us-east-1",
                    "Port": 80,
                    "Protocol": "HTTP",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "TargetType": "instance",
                    "StickinessEnabled": "true",
                    "StickinessType": "lb_cookie",
                    "StickinessCookieDuration": 86400,
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        # Check that stickiness is configured
        assert "stickiness" in main_tf
        assert "type" in main_tf

    def test_target_group_outputs(self):
        """Test Target Group outputs generation."""
        resources = [
            {
                "resource_type": "TargetGroup",
                "cloud_platform": "aws",
                "resource_name": "web-tg",
                "properties": {
                    "Region": "us-east-1",
                    "Port": 80,
                    "Protocol": "HTTP",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "TargetType": "instance",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)

        assert "outputs.tf" in files
        outputs_tf = files["outputs.tf"]

        # Check that Target Group outputs are created
        assert "web_tg_tg_arn" in outputs_tf
        assert "web_tg_tg_id" in outputs_tf
        assert "web_tg_tg_name" in outputs_tf

    def test_target_group_alias_tg(self):
        """Test 'tg' alias for Target Group."""
        resources = [
            {
                "resource_type": "tg",
                "cloud_platform": "aws",
                "resource_name": "test-tg",
                "properties": {
                    "Region": "us-east-1",
                    "Port": 80,
                    "Protocol": "HTTP",
                    "VPC": "main-vpc",
                    "VPCExists": "n",
                    "TargetType": "instance",
                    "Environment": "Production",
                    "Project": "MyProject",
                },
            }
        ]

        files = self.generator.generate_code(resources)
        main_tf = files["main.tf"]

        assert 'resource "aws_lb_target_group"' in main_tf


class TestExcelParserValidation:
    """Tests for Excel parser validation of LoadBalancer and TargetGroup."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ExcelParserService()

    def test_validate_aws_load_balancer(self):
        """Test validation for AWS Load Balancer."""
        resource = ResourceInfo(
            resource_type="LoadBalancer",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-alb",
            properties={
                "ResourceName": "test-alb",
                "Region": "us-east-1",
                "Type": "application",
                "Scheme": "internet-facing",
                "VPC": "main-vpc",
                "VPCExists": "n",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert is_valid, f"Validation failed with errors: {errors}"

    def test_validate_aws_load_balancer_invalid_type(self):
        """Test validation fails with invalid Type."""
        resource = ResourceInfo(
            resource_type="LoadBalancer",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-alb",
            properties={
                "ResourceName": "test-alb",
                "Region": "us-east-1",
                "Type": "invalid",
                "Scheme": "internet-facing",
                "VPC": "main-vpc",
                "VPCExists": "n",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("Type" in e for e in errors)

    def test_validate_aws_load_balancer_invalid_scheme(self):
        """Test validation fails with invalid Scheme."""
        resource = ResourceInfo(
            resource_type="LoadBalancer",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-alb",
            properties={
                "ResourceName": "test-alb",
                "Region": "us-east-1",
                "Type": "application",
                "Scheme": "invalid",
                "VPC": "main-vpc",
                "VPCExists": "n",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("Scheme" in e for e in errors)

    def test_validate_aws_target_group(self):
        """Test validation for AWS Target Group."""
        resource = ResourceInfo(
            resource_type="TargetGroup",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-tg",
            properties={
                "ResourceName": "test-tg",
                "Region": "us-east-1",
                "Port": 80,
                "Protocol": "HTTP",
                "VPC": "main-vpc",
                "VPCExists": "n",
                "TargetType": "instance",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert is_valid, f"Validation failed with errors: {errors}"

    def test_validate_aws_target_group_invalid_protocol(self):
        """Test validation fails with invalid Protocol."""
        resource = ResourceInfo(
            resource_type="TargetGroup",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-tg",
            properties={
                "ResourceName": "test-tg",
                "Region": "us-east-1",
                "Port": 80,
                "Protocol": "Invalid",
                "VPC": "main-vpc",
                "VPCExists": "n",
                "TargetType": "instance",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("Protocol" in e for e in errors)

    def test_validate_aws_target_group_invalid_target_type(self):
        """Test validation fails with invalid TargetType."""
        resource = ResourceInfo(
            resource_type="TargetGroup",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-tg",
            properties={
                "ResourceName": "test-tg",
                "Region": "us-east-1",
                "Port": 80,
                "Protocol": "HTTP",
                "VPC": "main-vpc",
                "VPCExists": "n",
                "TargetType": "invalid",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("TargetType" in e for e in errors)

    def test_validate_aws_target_group_invalid_port(self):
        """Test validation fails with invalid Port."""
        resource = ResourceInfo(
            resource_type="TargetGroup",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-tg",
            properties={
                "ResourceName": "test-tg",
                "Region": "us-east-1",
                "Port": 70000,  # Invalid port > 65535
                "Protocol": "HTTP",
                "VPC": "main-vpc",
                "VPCExists": "n",
                "TargetType": "instance",
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("Port" in e for e in errors)

    def test_validate_aws_load_balancer_idle_timeout(self):
        """Test validation for ALB IdleTimeout."""
        resource = ResourceInfo(
            resource_type="LoadBalancer",
            cloud_platform=CloudPlatform.AWS,
            resource_name="test-alb",
            properties={
                "ResourceName": "test-alb",
                "Region": "us-east-1",
                "Type": "application",
                "Scheme": "internet-facing",
                "VPC": "main-vpc",
                "VPCExists": "n",
                "IdleTimeout": 5000,  # Invalid > 4000
                "Environment": "Production",
                "Project": "MyProject",
            },
        )

        is_valid, errors = self.parser.validate_resource(resource)
        assert not is_valid
        assert any("IdleTimeout" in e for e in errors)


class TestExcelGeneratorNewResources:
    """Tests for Excel generator with LoadBalancer and TargetGroup."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ExcelGeneratorService()

    def test_aws_load_balancer_in_resources(self):
        """Test that AWS_LoadBalancer is in AWS_RESOURCES."""
        assert "AWS_LoadBalancer" in self.generator.AWS_RESOURCES
        fields = self.generator.AWS_RESOURCES["AWS_LoadBalancer"]
        assert "Region" in fields
        assert "Type" in fields
        assert "Scheme" in fields
        assert "VPC" in fields
        assert "Subnets" in fields
        assert "ListenerProtocol" in fields
        assert "ListenerTargetGroup" in fields

    def test_aws_target_group_in_resources(self):
        """Test that AWS_TargetGroup is in AWS_RESOURCES."""
        assert "AWS_TargetGroup" in self.generator.AWS_RESOURCES
        fields = self.generator.AWS_RESOURCES["AWS_TargetGroup"]
        assert "Port" in fields
        assert "Protocol" in fields
        assert "TargetType" in fields
        assert "HealthCheckProtocol" in fields
        assert "Targets" in fields

    def test_aws_load_balancer_required_fields(self):
        """Test that AWS_LoadBalancer has correct required fields."""
        assert "AWS_LoadBalancer" in self.generator.REQUIRED_FIELDS
        required = self.generator.REQUIRED_FIELDS["AWS_LoadBalancer"]
        assert "ResourceName" in required
        assert "Region" in required
        assert "Type" in required
        assert "Scheme" in required
        assert "VPC" in required

    def test_aws_target_group_required_fields(self):
        """Test that AWS_TargetGroup has correct required fields."""
        assert "AWS_TargetGroup" in self.generator.REQUIRED_FIELDS
        required = self.generator.REQUIRED_FIELDS["AWS_TargetGroup"]
        assert "ResourceName" in required
        assert "Port" in required
        assert "Protocol" in required
        assert "VPC" in required
        assert "TargetType" in required

    def test_aws_load_balancer_sample_data(self):
        """Test that AWS_LoadBalancer has sample data."""
        assert "AWS_LoadBalancer" in self.generator.SAMPLE_DATA
        sample = self.generator.SAMPLE_DATA["AWS_LoadBalancer"]
        assert sample["ResourceName"] == "web-alb"
        assert sample["Type"] == "application"
        assert sample["Scheme"] == "internet-facing"

    def test_aws_target_group_sample_data(self):
        """Test that AWS_TargetGroup has sample data."""
        assert "AWS_TargetGroup" in self.generator.SAMPLE_DATA
        sample = self.generator.SAMPLE_DATA["AWS_TargetGroup"]
        assert sample["ResourceName"] == "web-tg"
        assert sample["Port"] == "80"
        assert sample["Protocol"] == "HTTP"

    def test_generate_aws_template_includes_load_balancer(self):
        """Test that AWS template includes Load Balancer sheet."""
        template_bytes = self.generator.generate_template(TemplateType.AWS)
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

    def test_aws_load_balancer_in_resource_types(self):
        """Test that AWS_LoadBalancer is in AWS_RESOURCE_TYPES."""
        assert "AWS_LoadBalancer" in self.parser.AWS_RESOURCE_TYPES

    def test_aws_target_group_in_resource_types(self):
        """Test that AWS_TargetGroup is in AWS_RESOURCE_TYPES."""
        assert "AWS_TargetGroup" in self.parser.AWS_RESOURCE_TYPES

    def test_is_resource_sheet_load_balancer(self):
        """Test _is_resource_sheet for AWS_LoadBalancer."""
        assert self.parser._is_resource_sheet("AWS_LoadBalancer") is True

    def test_is_resource_sheet_target_group(self):
        """Test _is_resource_sheet for AWS_TargetGroup."""
        assert self.parser._is_resource_sheet("AWS_TargetGroup") is True
