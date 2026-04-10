"""Database models."""

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    JSON,
    UniqueConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
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


class User(Base):
    """Application user model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    password_hash = Column(String(255))
    provider = Column(String(50), nullable=False, default="local")
    provider_user_id = Column(String(255), index=True)
    avatar_url = Column(String(1000))
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sessions = relationship("Session", back_populates="user")
    policies = relationship("SecurityPolicy", back_populates="user")
    llm_configs = relationship("LLMConfig", back_populates="user")
    environments = relationship("DeploymentEnvironment", back_populates="user")


class SecurityPolicy(Base):
    """Security compliance policy model."""

    __tablename__ = "security_policies"
    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uq_policy_name_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    natural_language_rule = Column(Text, nullable=False)
    executable_rule = Column(JSON)
    cloud_platform = Column(SQLEnum(CloudPlatform), default=CloudPlatform.ALL)
    severity = Column(SQLEnum(SeverityLevel), default=SeverityLevel.ERROR)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="policies")


class LLMConfig(Base):
    """LLM configuration model."""

    __tablename__ = "llm_configs"
    __table_args__ = (
        UniqueConstraint("config_name", "user_id", name="uq_llmconfig_name_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    config_name= Column(String(255), nullable=False)
    api_endpoint = Column(String(500), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    model_name = Column(String(100), nullable=False)
    temperature = Column(Integer, default=70)  # Stored as integer (0.7 * 100)
    max_tokens = Column(Integer, default=4000)
    top_p = Column(Integer, default=100)  # Stored as integer (1.0 * 100)
    frequency_penalty = Column(Integer, default=0)
    presence_penalty = Column(Integer, default=0)
    timeout = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="llm_configs")


class Session(Base):
    """User session model."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    conversation_history= Column(JSON, default=list)
    resource_info = Column(JSON, default=list)
    compliance_results = Column(JSON, default=dict)
    generated_code = Column(JSON, default=dict)
    workflow_state = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="sessions")
    deployments = relationship("Deployment", back_populates="session")
    audit_logs = relationship("AuditLog", back_populates="session")


class AuditLog(Base):
    """Audit log model."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        String(100), ForeignKey("sessions.session_id"), nullable=True, index=True
    )
    action = Column(String(100), nullable=False)
    details = Column(JSON)
    result = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="audit_logs")


class DeploymentEnvironment(Base):
    """Deployment environment configuration model.

    Stores cloud credentials and configuration for deploying Terraform code.
    """

    __tablename__ = "deployment_environments"
    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uq_env_name_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description= Column(Text)
    cloud_platform = Column(SQLEnum(CloudPlatform), nullable=False)

    # AWS Credentials (encrypted via Fernet)
    aws_access_key_id = Column(String(255))
    aws_secret_access_key = Column(String(255))
    aws_region = Column(String(50))

    # Azure Credentials (encrypted via Fernet)
    azure_subscription_id = Column(String(255))
    azure_tenant_id = Column(String(255))
    azure_client_id = Column(String(255))
    azure_client_secret = Column(String(255))

    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="environments")


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
    session_id = Column(
        String(100), ForeignKey("sessions.session_id"), nullable=True, index=True
    )
    environment_id = Column(
        Integer, ForeignKey("deployment_environments.id"), nullable=True, index=True
    )

    status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.PENDING)

    terraform_code = Column(JSON)
    plan_output = Column(Text)
    plan_summary = Column(JSON)
    apply_output = Column(Text)
    terraform_outputs = Column(JSON)
    error_message = Column(Text)
    work_dir = Column(String(500))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))

    session = relationship("Session", back_populates="deployments")
    environment = relationship("DeploymentEnvironment")
