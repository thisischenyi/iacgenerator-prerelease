"""Regression tests for deployment environment detail responses."""

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.llm_config import encrypt_api_key
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models import CloudPlatform, DeploymentEnvironment, User


def _setup_test_db() -> tuple[sessionmaker, int, int]:
    """Create an isolated in-memory database with one user and one environment."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    seeded_user_id = 1
    seeded_env_id = 1

    with TestingSessionLocal() as db:
        user = User(
            id=seeded_user_id,
            email="owner@example.com",
            full_name="Owner",
            provider="microsoft",
            provider_user_id="provider-user-1",
            is_active=True,
        )
        environment = DeploymentEnvironment(
            id=seeded_env_id,
            user_id=seeded_user_id,
            name="azure-demo-env",
            description="existing azure env",
            cloud_platform=CloudPlatform.AZURE,
            azure_subscription_id=encrypt_api_key("sub-123"),
            azure_tenant_id=encrypt_api_key("tenant-456"),
            azure_client_id=encrypt_api_key("client-789"),
            azure_client_secret=encrypt_api_key("super-secret"),
            is_default=True,
        )
        db.add(user)
        db.add(environment)
        db.commit()

    return TestingSessionLocal, seeded_user_id, seeded_env_id


def test_get_environment_returns_prefill_values_and_masked_secret() -> None:
    """Environment detail endpoint exposes editable values and masks secrets."""
    TestingSessionLocal, seeded_user_id, seeded_env_id = _setup_test_db()

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user() -> User:
        with TestingSessionLocal() as db:
            user = db.query(User).filter(User.id == seeded_user_id).first()
            assert user is not None
            return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        client = TestClient(app)

        response = client.get(f"/api/deployments/environments/{seeded_env_id}")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["azure_subscription_id"] == "sub-123"
        assert payload["azure_tenant_id"] == "tenant-456"
        assert payload["azure_client_id"] == "client-789"
        assert payload["azure_client_secret"] == "***"
    finally:
        app.dependency_overrides.clear()
