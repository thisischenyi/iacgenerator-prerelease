"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CloudPlatform(str, Enum):
    """Cloud platform enum."""

    AWS = "aws"
    AZURE = "azure"
    ALL = "all"


class SeverityLevel(str, Enum):
    """Severity level enum."""

    ERROR = "error"
    WARNING = "warning"


class TemplateType(str, Enum):
    """Excel template type."""

    AWS = "aws"
    AZURE = "azure"
    FULL = "full"


# Security Policy Schemas
class SecurityPolicyCreate(BaseModel):
    """Schema for creating a security policy."""

    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    natural_language_rule: str
    cloud_platform: CloudPlatform = CloudPlatform.ALL
    severity: SeverityLevel = SeverityLevel.ERROR
    enabled: bool = True


class SecurityPolicyUpdate(BaseModel):
    """Schema for updating a security policy."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    natural_language_rule: Optional[str] = None
    executable_rule: Optional[Dict[str, Any]] = None
    cloud_platform: Optional[CloudPlatform] = None
    severity: Optional[SeverityLevel] = None
    enabled: Optional[bool] = None


class SecurityPolicyResponse(BaseModel):
    """Schema for security policy response."""

    id: int
    name: str
    description: Optional[str]
    natural_language_rule: str
    executable_rule: Optional[Dict[str, Any]]
    cloud_platform: CloudPlatform
    severity: SeverityLevel
    enabled: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# LLM Config Schemas
class LLMConfigCreate(BaseModel):
    """Schema for creating LLM configuration."""

    config_name: str = Field(..., max_length=255)
    api_endpoint: str = Field(..., max_length=500)
    api_key: str
    model_name: str = Field(..., max_length=100)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(4000, gt=0)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    timeout: int = Field(60, gt=0)


class LLMConfigResponse(BaseModel):
    """Schema for LLM configuration response."""

    id: int
    config_name: str
    api_endpoint: str
    model_name: str
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    timeout: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Chat Schemas
class ChatMessage(BaseModel):
    """Schema for a chat message."""

    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Schema for chat request."""

    session_id: Optional[str] = None
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Schema for chat response."""

    session_id: str
    message: str
    code_blocks: Optional[List[Dict[str, str]]] = None
    metadata: Optional[Dict[str, Any]] = None


# Resource Schemas
class ResourceInfo(BaseModel):
    """Schema for resource information."""

    resource_type: str
    cloud_platform: CloudPlatform
    resource_name: str
    properties: Dict[str, Any]


class ResourceCollection(BaseModel):
    """Schema for a collection of resources."""

    resources: List[ResourceInfo]
    metadata: Optional[Dict[str, Any]] = None


# Excel Upload Schemas
class ExcelParseResult(BaseModel):
    """Schema for Excel parse result."""

    success: bool
    resource_count: int
    resource_types: List[str]
    resources: List[ResourceInfo]
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None


# Compliance Schemas
class ComplianceViolation(BaseModel):
    """Schema for a compliance violation."""

    policy_name: str
    policy_description: str
    severity: SeverityLevel
    resource_name: str
    resource_type: str
    violation_details: str
    suggestion: Optional[str] = None


class ComplianceCheckResult(BaseModel):
    """Schema for compliance check result."""

    passed: bool
    violations: List[ComplianceViolation]
    warnings: List[ComplianceViolation]
    checked_policies_count: int


# Code Generation Schemas
class GeneratedCode(BaseModel):
    """Schema for generated code."""

    filename: str
    content: str
    language: str = "hcl"


class CodeGenerationResult(BaseModel):
    """Schema for code generation result."""

    success: bool
    files: List[GeneratedCode]
    summary: str
    download_url: Optional[str] = None


# Session Schemas
class SessionCreate(BaseModel):
    """Schema for creating a session."""

    user_id: Optional[str] = None


class SessionResponse(BaseModel):
    """Schema for session response."""

    session_id: str
    created_at: datetime
    conversation_history: Optional[List[Dict[str, str]]] = None
    resource_info: Optional[List[Dict[str, Any]]] = None
    compliance_results: Optional[Dict[str, Any]] = None
    generated_code: Optional[Dict[str, str]] = None
    workflow_state: Optional[str] = None

    class Config:
        from_attributes = True


# General Responses
class ErrorResponse(BaseModel):
    """Schema for error response."""

    error: str
    details: Optional[str] = None
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Schema for success response."""

    success: bool
    message: str
    data: Optional[Any] = None


# Deployment Environment Schemas
class DeploymentStatus(str, Enum):
    """Deployment status enum."""

    PENDING = "pending"
    PLANNING = "planning"
    PLAN_READY = "plan_ready"
    PLAN_FAILED = "plan_failed"
    APPLYING = "applying"
    APPLY_SUCCESS = "apply_success"
    APPLY_FAILED = "apply_failed"
    DESTROYED = "destroyed"


class DeploymentEnvironmentCreate(BaseModel):
    """Schema for creating a deployment environment."""

    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    cloud_platform: CloudPlatform

    # AWS Credentials
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: Optional[str] = Field(None, max_length=50)

    # Azure Credentials
    azure_subscription_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None

    is_default: bool = False


class DeploymentEnvironmentUpdate(BaseModel):
    """Schema for updating a deployment environment."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    cloud_platform: Optional[CloudPlatform] = None

    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: Optional[str] = None

    azure_subscription_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None

    is_default: Optional[bool] = None


class DeploymentEnvironmentResponse(BaseModel):
    """Schema for deployment environment response.

    Note: Credentials are masked in response for security.
    """

    id: int
    name: str
    description: Optional[str]
    cloud_platform: CloudPlatform

    # Masked credentials (only show if configured)
    has_aws_credentials: bool = False
    aws_region: Optional[str] = None

    has_azure_credentials: bool = False

    is_default: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Deployment Schemas
class DeploymentCreate(BaseModel):
    """Schema for creating a deployment."""

    session_id: str
    environment_id: int
    terraform_code: Dict[str, str]  # filename -> content


class PlanSummary(BaseModel):
    """Schema for terraform plan summary."""

    add: int = 0
    change: int = 0
    destroy: int = 0


class DeploymentResponse(BaseModel):
    """Schema for deployment response."""

    id: int
    deployment_id: str
    session_id: str
    environment_id: int
    status: DeploymentStatus

    plan_output: Optional[str] = None
    plan_summary: Optional[PlanSummary] = None

    apply_output: Optional[str] = None
    terraform_outputs: Optional[Dict[str, Any]] = None

    error_message: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class DeploymentPlanRequest(BaseModel):
    """Schema for requesting a terraform plan."""

    session_id: str
    environment_id: int
    terraform_code: Dict[str, str]


class DeploymentApplyRequest(BaseModel):
    """Schema for applying a terraform deployment."""

    deployment_id: str


class DeploymentPlanResponse(BaseModel):
    """Schema for plan response."""

    deployment_id: str
    status: DeploymentStatus
    plan_output: str
    plan_summary: PlanSummary


class DeploymentApplyResponse(BaseModel):
    """Schema for apply response."""

    deployment_id: str
    status: DeploymentStatus
    apply_output: Optional[str] = None
    terraform_outputs: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
