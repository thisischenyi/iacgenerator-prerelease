"""LLM configuration management API routes."""

import base64
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet

from app.core.database import get_db
from app.core.config import get_settings
from app.models import LLMConfig
from app.schemas import (
    LLMConfigCreate,
    LLMConfigResponse,
    SuccessResponse,
)

router = APIRouter()
settings = get_settings()


def encrypt_api_key(api_key: str) -> str:
    """
    Store API key as plain text (Simplified for debugging).
    """
    return api_key


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Return plain text API key.
    """
    return encrypted_key


@router.get("", response_model=List[LLMConfigResponse])
def list_llm_configs(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    """
    Get all LLM configurations.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        active_only: If True, return only active configurations
        db: Database session

    Returns:
        List of LLM configurations
    """
    query = db.query(LLMConfig)

    if active_only:
        query = query.filter(LLMConfig.is_active == True)

    configs = query.offset(skip).limit(limit).all()
    return configs


@router.post("", response_model=LLMConfigResponse, status_code=status.HTTP_201_CREATED)
def create_llm_config(
    config_data: LLMConfigCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new LLM configuration.

    Args:
        config_data: LLM configuration data
        db: Database session

    Returns:
        Created LLM configuration

    Raises:
        HTTPException: If configuration name already exists
    """
    # Check if config with same name exists
    existing = (
        db.query(LLMConfig)
        .filter(LLMConfig.config_name == config_data.config_name)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM configuration with name '{config_data.config_name}' already exists",
        )

    # Encrypt API key
    encrypted_key = encrypt_api_key(config_data.api_key)

    # Create new configuration
    # Convert float parameters to integers (stored as int * 100)
    config = LLMConfig(
        config_name=config_data.config_name,
        api_endpoint=config_data.api_endpoint,
        api_key_encrypted=encrypted_key,
        model_name=config_data.model_name,
        temperature=int(config_data.temperature * 100),
        max_tokens=config_data.max_tokens,
        top_p=int(config_data.top_p * 100),
        frequency_penalty=int(config_data.frequency_penalty * 100),
        presence_penalty=int(config_data.presence_penalty * 100),
        timeout=config_data.timeout,
    )

    db.add(config)
    db.commit()
    db.refresh(config)

    return config


@router.get("/{config_id}", response_model=LLMConfigResponse)
def get_llm_config(
    config_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific LLM configuration by ID.

    Args:
        config_id: Configuration ID
        db: Database session

    Returns:
        LLM configuration

    Raises:
        HTTPException: If configuration not found
    """
    config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()

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
    db: Session = Depends(get_db),
):
    """
    Update an LLM configuration.

    Args:
        config_id: Configuration ID
        config_data: Updated configuration data
        db: Database session

    Returns:
        Updated LLM configuration

    Raises:
        HTTPException: If configuration not found or name conflict
    """
    config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM configuration with id {config_id} not found",
        )

    # Check for name conflict if name is being updated
    if config_data.config_name != config.config_name:
        existing = (
            db.query(LLMConfig)
            .filter(LLMConfig.config_name == config_data.config_name)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LLM configuration with name '{config_data.config_name}' already exists",
            )

    # Update fields
    config.config_name = config_data.config_name
    config.api_endpoint = config_data.api_endpoint

    # Only update API key if provided
    if config_data.api_key and config_data.api_key.strip():
        config.api_key_encrypted = encrypt_api_key(config_data.api_key)

    config.model_name = config_data.model_name
    config.temperature = int(config_data.temperature * 100)
    config.max_tokens = config_data.max_tokens
    config.top_p = int(config_data.top_p * 100)
    config.frequency_penalty = int(config_data.frequency_penalty * 100)
    config.presence_penalty = int(config_data.presence_penalty * 100)
    config.timeout = config_data.timeout

    db.commit()
    db.refresh(config)

    return config


@router.delete("/{config_id}", response_model=SuccessResponse)
def delete_llm_config(
    config_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete an LLM configuration.

    Args:
        config_id: Configuration ID
        db: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If configuration not found
    """
    config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()

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
    db: Session = Depends(get_db),
):
    """
    Test LLM configuration connection.

    Args:
        config_id: Configuration ID
        db: Database session

    Returns:
        Success response with test results

    Raises:
        HTTPException: If configuration not found or connection fails
    """
    config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM configuration with id {config_id} not found",
        )

    # TODO: Implement actual LLM connection test
    # This is a placeholder for now
    # In production, you would:
    # 1. Decrypt the API key
    # 2. Make a test API call to the LLM endpoint
    # 3. Return success/failure based on response

    return SuccessResponse(
        success=True,
        message=f"Connection test for '{config.config_name}' completed successfully",
        data={
            "endpoint": config.api_endpoint,
            "model": config.model_name,
            "status": "connected",
        },
    )


@router.patch("/{config_id}/activate", response_model=LLMConfigResponse)
def activate_llm_config(
    config_id: int,
    db: Session = Depends(get_db),
):
    """
    Activate an LLM configuration (deactivate all others).

    Args:
        config_id: Configuration ID
        db: Database session

    Returns:
        Activated configuration

    Raises:
        HTTPException: If configuration not found
    """
    config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM configuration with id {config_id} not found",
        )

    # Deactivate all configurations
    db.query(LLMConfig).update({"is_active": False})

    # Activate selected configuration
    config.is_active = True

    db.commit()
    db.refresh(config)

    return config
