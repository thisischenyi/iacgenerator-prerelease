"""Add user isolation and foreign keys.

Revision ID: 91dccd590ca8
Revises: 741f875923a3
Create Date: 2026-04-10

Adds user_id FK to SecurityPolicy, LLMConfig, DeploymentEnvironment.
Changes Session.user_id from String to Integer FK.
Adds FKs for Deployment.session_id, Deployment.environment_id, AuditLog.session_id.
Replaces global unique constraints with per-user unique constraints.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "91dccd590ca8"
down_revision = "741f875923a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add user isolation columns and foreign keys."""

    # --- security_policies ---
    with op.batch_alter_table("security_policies") as batch_op:
        # Drop the old global unique on name
        batch_op.drop_constraint("uq_security_policies_name", type_="unique")
        # Add user_id column
        batch_op.add_column(
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True)
        )
        batch_op.create_index("ix_security_policies_user_id", ["user_id"])
        # Per-user unique on (name, user_id)
        batch_op.create_unique_constraint("uq_policy_name_user", ["name", "user_id"])

    # --- llm_configs ---
    with op.batch_alter_table("llm_configs") as batch_op:
        batch_op.drop_constraint("uq_llm_configs_config_name", type_="unique")
        batch_op.add_column(
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True)
        )
        batch_op.create_index("ix_llm_configs_user_id", ["user_id"])
        batch_op.create_unique_constraint(
            "uq_llmconfig_name_user", ["config_name", "user_id"]
        )

    # --- deployment_environments ---
    with op.batch_alter_table("deployment_environments") as batch_op:
        batch_op.drop_constraint(
            "uq_deployment_environments_name", type_="unique"
        )
        batch_op.add_column(
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True)
        )
        batch_op.create_index("ix_deployment_environments_user_id", ["user_id"])
        batch_op.create_unique_constraint("uq_env_name_user", ["name", "user_id"])

    # --- sessions: change user_id from String to Integer FK ---
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.String(100),
            type_=sa.Integer(),
            existing_nullable=True,
            postgresql_using="user_id::integer",
        )
        batch_op.create_foreign_key(
            "fk_sessions_user_id", "users", ["user_id"], ["id"]
        )

    # --- audit_logs: add FK to sessions ---
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.create_foreign_key(
            "fk_audit_logs_session_id", "sessions", ["session_id"], ["session_id"]
        )

    # --- deployments: add FKs ---
    with op.batch_alter_table("deployments") as batch_op:
        batch_op.create_foreign_key(
            "fk_deployments_session_id", "sessions", ["session_id"], ["session_id"]
        )
        batch_op.create_foreign_key(
            "fk_deployments_environment_id",
            "deployment_environments",
            ["environment_id"],
            ["id"],
        )


def downgrade() -> None:
    """Revert user isolation changes."""

    with op.batch_alter_table("deployments") as batch_op:
        batch_op.drop_constraint("fk_deployments_session_id", type_="foreignkey")
        batch_op.drop_constraint("fk_deployments_environment_id", type_="foreignkey")

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_constraint("fk_audit_logs_session_id", type_="foreignkey")

    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_constraint("fk_sessions_user_id", type_="foreignkey")
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            type_=sa.String(100),
            existing_nullable=True,
        )

    with op.batch_alter_table("deployment_environments") as batch_op:
        batch_op.drop_constraint("uq_env_name_user", type_="unique")
        batch_op.drop_index("ix_deployment_environments_user_id")
        batch_op.drop_column("user_id")
        batch_op.create_unique_constraint(
            "uq_deployment_environments_name", ["name"]
        )

    with op.batch_alter_table("llm_configs") as batch_op:
        batch_op.drop_constraint("uq_llmconfig_name_user", type_="unique")
        batch_op.drop_index("ix_llm_configs_user_id")
        batch_op.drop_column("user_id")
        batch_op.create_unique_constraint("uq_llm_configs_config_name", ["config_name"])

    with op.batch_alter_table("security_policies") as batch_op:
        batch_op.drop_constraint("uq_policy_name_user", type_="unique")
        batch_op.drop_index("ix_security_policies_user_id")
        batch_op.drop_column("user_id")
        batch_op.create_unique_constraint("uq_security_policies_name", ["name"])
