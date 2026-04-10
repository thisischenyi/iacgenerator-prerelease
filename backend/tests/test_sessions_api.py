"""API regression tests for session creation."""

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models import User


def _setup_test_db() -> tuple[sessionmaker, int]:
    """Create an isolated in-memory database with one active user."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    seeded_user_id = 1

    with TestingSessionLocal() as db:
        user = User(
            id=seeded_user_id,
            email="oauth-user@example.com",
            full_name="OAuth User",
            provider="microsoft",
            provider_user_id="provider-user-1",
            is_active=True,
        )
        db.add(user)
        db.commit()

    return TestingSessionLocal, seeded_user_id


def test_create_session_accepts_empty_body_for_authenticated_user() -> None:
    """Authenticated clients can create a session without sending a request body."""
    TestingSessionLocal, seeded_user_id = _setup_test_db()

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

        response = client.post("/api/sessions")

        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["session_id"]
        assert payload["workflow_state"] == "initialized"
    finally:
        app.dependency_overrides.clear()
