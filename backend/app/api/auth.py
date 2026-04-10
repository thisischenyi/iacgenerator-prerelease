"""Authentication API routes."""

import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
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
logger = logging.getLogger(__name__)

# In-memory stores with TTL for OAuth state and one-time codes.
# Production should use Redis or DB-backed storage.
_oauth_states: dict[str, datetime] = {}
_auth_codes: dict[str, tuple[int, datetime]] = {}  # code -> (user_id, expires_at)

_STATE_TTL = timedelta(minutes=10)
_CODE_TTL = timedelta(minutes=2)


def _store_oauth_state(state: str) -> None:
    """Store an OAuth state value with expiration."""
    _cleanup_expired_states()
    _oauth_states[state] = datetime.now(timezone.utc) + _STATE_TTL


def _validate_oauth_state(state: str | None) -> None:
    """Validate and consume an OAuth state value."""
    if not state or state not in _oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state parameter",
        )
    expires = _oauth_states.pop(state)
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state has expired",
        )


def _create_auth_code(user_id: int) -> str:
    """Create a one-time auth code that can be exchanged for a JWT."""
    _cleanup_expired_codes()
    code = secrets.token_urlsafe(48)
    _auth_codes[code] = (user_id, datetime.now(timezone.utc) + _CODE_TTL)
    return code


def _cleanup_expired_states() -> None:
    now = datetime.now(timezone.utc)
    expired = [k for k, v in _oauth_states.items() if now > v]
    for k in expired:
        _oauth_states.pop(k, None)


def _cleanup_expired_codes() -> None:
    now = datetime.now(timezone.utc)
    expired = [k for k, v in _auth_codes.items() if now > v[1]]
    for k in expired:
        _auth_codes.pop(k, None)


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
    """Create or update OAuth user from provider profile.

    Matching priority:
    1. Exact (provider, provider_user_id) match → update profile fields.
    2. Email match → only auto-link if existing account is also an OAuth account
       (has a provider set). Local-password accounts are NOT auto-linked to
       prevent account takeover.
    3. No match → create a new user.
    """
    # 1. Exact provider match
    user = (
        db.query(User)
        .filter(
            User.provider == provider,
            User.provider_user_id == provider_user_id,
        )
        .first()
    )

    if not user:
        # 2. Email-based lookup
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.provider and existing.provider_user_id:
                # Existing OAuth account with different provider — safe to link
                user = existing
            else:
                # Local-password account — refuse auto-link to prevent takeover
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An account with this email already exists. "
                    "Please log in with your password first, then link "
                    "your OAuth account from settings.",
                )

    if not user:
        # 3. Create new user
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

    state = str(uuid.uuid4())
    _store_oauth_state(state)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "consent",
    }
    return RedirectResponse(
        url=f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    )


@router.get("/google/callback")
def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: DBSession = Depends(get_db),
):
    """Handle Google OAuth callback."""
    _validate_oauth_state(state)

    try:
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
    except httpx.HTTPError as e:
        logger.error("Google token exchange failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to connect to Google authentication service",
        )

    if token_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange Google authorization code",
        )

    access_token = token_resp.json().get("access_token")

    try:
        userinfo_resp = httpx.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
    except httpx.HTTPError as e:
        logger.error("Google userinfo fetch failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch Google user profile",
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
    auth_code = _create_auth_code(user.id)
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?code={auth_code}"
    return RedirectResponse(url=redirect_url)


@router.get("/microsoft/login")
def microsoft_login():
    """Start Microsoft OAuth login flow."""
    if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Microsoft OAuth is not configured",
        )

    state = str(uuid.uuid4())
    _store_oauth_state(state)

    tenant = settings.MICROSOFT_TENANT_ID or "common"
    params = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "response_mode": "query",
        "scope": "openid profile email",
        "state": state,
    }
    auth_url = (
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?"
        f"{urlencode(params)}"
    )
    return RedirectResponse(url=auth_url)


@router.get("/microsoft/callback")
def microsoft_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: DBSession = Depends(get_db),
):
    """Handle Microsoft OAuth callback."""
    _validate_oauth_state(state)

    tenant = settings.MICROSOFT_TENANT_ID or "common"
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

    try:
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
    except httpx.HTTPError as e:
        logger.error("Microsoft token exchange failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to connect to Microsoft authentication service",
        )

    if token_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange Microsoft authorization code",
        )

    access_token = token_resp.json().get("access_token")

    try:
        userinfo_resp = httpx.get(
            "https://graph.microsoft.com/oidc/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
    except httpx.HTTPError as e:
        logger.error("Microsoft userinfo fetch failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch Microsoft user profile",
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
    auth_code = _create_auth_code(user.id)
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?code={auth_code}"
    return RedirectResponse(url=redirect_url)


class _CodeExchangeRequest(BaseModel):
    """Request body for one-time code exchange."""

    code: str


@router.post("/exchange", response_model=AuthTokenResponse)
def exchange_code(
    body: _CodeExchangeRequest,
    db: DBSession = Depends(get_db),
):
    """Exchange a one-time OAuth code for a JWT access token."""
    _cleanup_expired_codes()
    entry = _auth_codes.pop(body.code, None)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired authorization code",
        )
    user_id, expires_at = entry
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code has expired",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return _create_auth_response(user)
