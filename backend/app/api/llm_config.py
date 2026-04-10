"""LLM configuration management API routes."""

import base64
import hashlib
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet, InvalidToken

from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import get_current_user
from app.models import LLMConfig, User
from app.schemas import (
    LLMConfigCreate,
    LLMConfigResponse,
    SuccessResponse,
)

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Derive a Fernet cipher from the application SECRET_KEY."""
    key_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key using Fernet symmetric encryption."""
    return _get_fernet().encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key. Falls back to returning the value as-is for legacy plaintext keys."""
    try:
        return _get_fernet().decrypt(encrypted_key.encode()).decode()
    except (InvalidToken, Exception):
        # Legacy plaintext key stored before encryption was enabled
        logger.warning("decrypt_api_key: value does not appear to be a Fernet token; returning as-is")
        return encrypted_key


@router.get("", response_model=List[LLMConfigResponse])
def list_llm_configs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all LLM configurations owned by current user."""
    query = db.query(LLMConfig).filter(LLMConfig.user_id == current_user.id)

    if active_only:
        query = query.filter(LLMConfig.is_active)

    configs = query.offset(skip).limit(limit).all()
    return configs


@router.post("", response_model=LLMConfigResponse, status_code=status.HTTP_201_CREATED)
def create_llm_config(
    config_data: LLMConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new LLM configuration for current user."""
    existing = (
        db.query(LLMConfig)
        .filter(
            LLMConfig.config_name == config_data.config_name,
            LLMConfig.user_id == current_user.id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM configuration with name '{config_data.config_name}' already exists",
        )

    encrypted_key = encrypt_api_key(config_data.api_key)

    config = LLMConfig(
        user_id=current_user.id,
        config_name=config_data.config_name,
        api_endpoint=config_data.api_endpoint,
        api_key_encrypted=encrypted_key,
        model_name=config_data.model_name,
        temperature=round(config_data.temperature * 100),
        max_tokens=config_data.max_tokens,
        top_p=round(config_data.top_p * 100),
        frequency_penalty=round(config_data.frequency_penalty * 100),
        presence_penalty=round(config_data.presence_penalty * 100),
        timeout=config_data.timeout,
    )

    db.add(config)
    db.commit()
    db.refresh(config)

    return config


@router.get("/{config_id}", response_model=LLMConfigResponse)
def get_llm_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific LLM configuration by ID."""
    config = (
        db.query(LLMConfig)
        .filter(LLMConfig.id == config_id, LLMConfig.user_id == current_user.id)
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM configuration with id {config_id} not found",
        )

    return config


@router.put("/{config_id}", response_model=LLMConfigResponse)
def update_llm_config(
    config_id: int,
    config_data: LLMConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an LLM configuration."""
    config = (
        db.query(LLMConfig)
        .filter(LLMConfig.id == config_id, LLMConfig.user_id == current_user.id)
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM configuration with id {config_id} not found",
        )

    if config_data.config_name != config.config_name:
        existing = (
            db.query(LLMConfig)
            .filter(
                LLMConfig.config_name == config_data.config_name,
                LLMConfig.user_id == current_user.id,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LLM configuration with name '{config_data.config_name}' already exists",
            )

    config.config_name = config_data.config_name
    config.api_endpoint = config_data.api_endpoint

    if config_data.api_key and config_data.api_key.strip():
        config.api_key_encrypted = encrypt_api_key(config_data.api_key)

    config.model_name = config_data.model_name
    config.temperature = round(config_data.temperature * 100)
    config.max_tokens = config_data.max_tokens
    config.top_p = round(config_data.top_p * 100)
    config.frequency_penalty = round(config_data.frequency_penalty * 100)
    config.presence_penalty = round(config_data.presence_penalty * 100)
    config.timeout = config_data.timeout

    db.commit()
    db.refresh(config)

    return config


@router.delete("/{config_id}", response_model=SuccessResponse)
def delete_llm_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an LLM configuration."""
    config = (
        db.query(LLMConfig)
        .filter(LLMConfig.id == config_id, LLMConfig.user_id == current_user.id)
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM configuration with id {config_id} not found",
        )

    db.delete(config)
    db.commit()

    return SuccessResponse(
        success=True,
        message=f"LLM configuration '{config.config_name}' deleted successfully",
    )


@router.post("/{config_id}/test", response_model=SuccessResponse)
async def test_llm_connection(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test LLM configuration connection by making a minimal API call."""
    config = (
        db.query(LLMConfig)
        .filter(LLMConfig.id == config_id, LLMConfig.user_id == current_user.id)
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM configuration with id {config_id} not found",
        )

    api_key = decrypt_api_key(config.api_key_encrypted)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=config.api_endpoint)
        response = client.chat.completions.create(
            model=config.model_name,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
        )
        model_used = response.model or config.model_name
    except Exception as e:
        logger.error("LLM connection test failed for config %s: %s", config_id, e)
        return SuccessResponse(
            success=False,
            message=f"Connection test failed: {e}",
            data={
                "endpoint": config.api_endpoint,
                "model": config.model_name,
                "status": "failed",
            },
        )

    return SuccessResponse(
        success=True,
        message=f"Connection test for '{config.config_name}' completed successfully",
        data={
            "endpoint": config.api_endpoint,
            "model": model_used,
            "status": "connected",
        },
    )


@router.patch("/{config_id}/activate", response_model=LLMConfigResponse)
def activate_llm_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Activate an LLM configuration (deactivate all others for this user)."""
    config = (
        db.query(LLMConfig)
        .filter(LLMConfig.id == config_id, LLMConfig.user_id == current_user.id)
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM configuration with id {config_id} not found",
        )

    # Deactivate only this user's configurations
    db.query(LLMConfig).filter(LLMConfig.user_id == current_user.id).update(
        {"is_active": False}
    )

    config.is_active = True

    db.commit()
    db.refresh(config)

    return config
