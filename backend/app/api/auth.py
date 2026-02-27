"""Authentication API routes."""

import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session as DBSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas import (
    AuthTokenResponse,
    UserLoginRequest,
    UserProfileResponse,
    UserRegisterRequest,
)

router = APIRouter()
settings = get_settings()


def _create_auth_response(user: User) -> AuthTokenResponse:
    """Build token response for a user."""
    token = create_access_token(str(user.id))
    return AuthTokenResponse(
        access_token=token,
        user=UserProfileResponse.model_validate(user),
    )


def _upsert_oauth_user(
    db: DBSession,
    provider: str,
    provider_user_id: str,
    email: str,
    full_name: str | None,
    avatar_url: str | None,
) -> User:
    """Create or update OAuth user from provider profile."""
    user = (
        db.query(User)
        .filter(
            User.provider == provider,
            User.provider_user_id == provider_user_id,
        )
        .first()
    )

    if not user:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            email=email,
            full_name=full_name,
            provider=provider,
            provider_user_id=provider_user_id,
            avatar_url=avatar_url,
            is_active=True,
        )
        db.add(user)
    else:
        user.full_name = full_name or user.full_name
        user.avatar_url = avatar_url or user.avatar_url
        user.provider = provider
        user.provider_user_id = provider_user_id
        user.is_active = True

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


@router.post("/register", response_model=AuthTokenResponse)
def register(
    payload: UserRegisterRequest,
    db: DBSession = Depends(get_db),
):
    """Register a new local user."""
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        provider="local",
        is_active=True,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _create_auth_response(user)


@router.post("/login", response_model=AuthTokenResponse)
def login(
    payload: UserLoginRequest,
    db: DBSession = Depends(get_db),
):
    """Login with email and password."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return _create_auth_response(user)


@router.get("/me", response_model=UserProfileResponse)
def me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return UserProfileResponse.model_validate(current_user)


@router.get("/google/login")
def google_login():
    """Start Google OAuth login flow."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured",
        )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": str(uuid.uuid4()),
        "access_type": "online",
        "prompt": "consent",
    }
    return RedirectResponse(
        url=f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    )


@router.get("/google/callback")
def google_callback(
    code: str = Query(...),
    db: DBSession = Depends(get_db),
):
    """Handle Google OAuth callback."""
    token_resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        },
        timeout=20,
    )
    if token_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange Google authorization code",
        )

    access_token = token_resp.json().get("access_token")
    userinfo_resp = httpx.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )
    if userinfo_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch Google user profile",
        )
    profile = userinfo_resp.json()

    email = profile.get("email")
    sub = profile.get("sub")
    if not email or not sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google profile missing required fields",
        )

    user = _upsert_oauth_user(
        db=db,
        provider="google",
        provider_user_id=sub,
        email=email.lower(),
        full_name=profile.get("name"),
        avatar_url=profile.get("picture"),
    )
    token = create_access_token(str(user.id))
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={token}"
    return RedirectResponse(url=redirect_url)


@router.get("/microsoft/login")
def microsoft_login():
    """Start Microsoft OAuth login flow."""
    if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Microsoft OAuth is not configured",
        )

    tenant = settings.MICROSOFT_TENANT_ID or "common"
    params = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "response_mode": "query",
        "scope": "openid profile email",
        "state": str(uuid.uuid4()),
    }
    auth_url = (
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?"
        f"{urlencode(params)}"
    )
    return RedirectResponse(url=auth_url)


@router.get("/microsoft/callback")
def microsoft_callback(
    code: str = Query(...),
    db: DBSession = Depends(get_db),
):
    """Handle Microsoft OAuth callback."""
    tenant = settings.MICROSOFT_TENANT_ID or "common"
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    token_resp = httpx.post(
        token_url,
        data={
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
            "scope": "openid profile email",
        },
        timeout=20,
    )
    if token_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange Microsoft authorization code",
        )

    access_token = token_resp.json().get("access_token")
    userinfo_resp = httpx.get(
        "https://graph.microsoft.com/oidc/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )
    if userinfo_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch Microsoft user profile",
        )
    profile = userinfo_resp.json()

    email = (
        profile.get("email")
        or profile.get("preferred_username")
        or profile.get("upn")
    )
    sub = profile.get("sub")
    if not email or not sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Microsoft profile missing required fields",
        )

    user = _upsert_oauth_user(
        db=db,
        provider="microsoft",
        provider_user_id=sub,
        email=email.lower(),
        full_name=profile.get("name"),
        avatar_url=None,
    )
    token = create_access_token(str(user.id))
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={token}"
    return RedirectResponse(url=redirect_url)
