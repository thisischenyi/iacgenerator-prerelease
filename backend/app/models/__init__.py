"""Database models."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class SeverityLevel(str, enum.Enum):
    """Policy severity levels."""

    ERROR = "error"
    WARNING = "warning"


class CloudPlatform(str, enum.Enum):
    """Supported cloud platforms."""

    AWS = "aws"
    AZURE = "azure"
    ALL = "all"


class SecurityPolicy(Base):
    """Security compliance policy model."""

    __tablename__ = "security_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    natural_language_rule = Column(Text, nullable=False)
    executable_rule = Column(JSON)  # AI-converted rule
    cloud_platform = Column(SQLEnum(CloudPlatform), default=CloudPlatform.ALL)
    severity = Column(SQLEnum(SeverityLevel), default=SeverityLevel.ERROR)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LLMConfig(Base):
    """LLM configuration model."""

    __tablename__ = "llm_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_name = Column(String(255), unique=True, nullable=False)
    api_endpoint = Column(String(500), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    model_name = Column(String(100), nullable=False)
    temperature = Column(Integer, default=70)  # Stored as integer (0.7 * 100)
    max_tokens = Column(Integer, default=4000)
    top_p = Column(Integer, default=100)  # Stored as integer (1.0 * 100)
    frequency_penalty = Column(Integer, default=0)
    presence_penalty = Column(Integer, default=0)
    timeout = Column(Integer, default=60)  # seconds
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Session(Base):
    """User session model."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(100), index=True)
    conversation_history = Column(JSON, default=[])
    resource_info = Column(JSON, default=[])  # Fixed: should be list, not dict
    compliance_results = Column(JSON, default={})
    generated_code = Column(JSON, default={})
    workflow_state = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AuditLog(Base):
    """Audit log model."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    action = Column(String(100), nullable=False)
    details = Column(JSON)
    result = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DeploymentEnvironment(Base):
    """Deployment environment configuration model.

    Stores cloud credentials and configuration for deploying Terraform code.
    """

    __tablename__ = "deployment_environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    cloud_platform = Column(SQLEnum(CloudPlatform), nullable=False)

    # AWS Credentials (stored in plaintext for prototype)
    aws_access_key_id = Column(String(255))
    aws_secret_access_key = Column(String(255))
    aws_region = Column(String(50))

    # Azure Credentials (stored in plaintext for prototype)
    azure_subscription_id = Column(String(255))
    azure_tenant_id = Column(String(255))
    azure_client_id = Column(String(255))
    azure_client_secret = Column(String(255))

    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DeploymentStatus(str, enum.Enum):
    """Deployment status enum."""

    PENDING = "pending"
    PLANNING = "planning"
    PLAN_READY = "plan_ready"
    PLAN_FAILED = "plan_failed"
    APPLYING = "applying"
    APPLY_SUCCESS = "apply_success"
    APPLY_FAILED = "apply_failed"
    DESTROYED = "destroyed"


class Deployment(Base):
    """Deployment history model.

    Tracks each deployment attempt and its results.
    """

    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)
    deployment_id = Column(String(100), unique=True, nullable=False, index=True)
    session_id = Column(String(100), index=True)
    environment_id = Column(Integer, index=True)

    status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.PENDING)

    # Terraform code being deployed
    terraform_code = Column(JSON)  # Dict of filename -> content

    # Plan output
    plan_output = Column(Text)
    plan_summary = Column(JSON)  # Parsed plan summary: add/change/destroy counts

    # Apply output
    apply_output = Column(Text)
    terraform_outputs = Column(JSON)  # terraform output -json result

    # Error tracking
    error_message = Column(Text)

    # Working directory for this deployment
    work_dir = Column(String(500))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
