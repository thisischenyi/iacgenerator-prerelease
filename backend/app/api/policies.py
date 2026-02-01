"""Security policy management API routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import SecurityPolicy
from app.schemas import (
    SecurityPolicyCreate,
    SecurityPolicyUpdate,
    SecurityPolicyResponse,
    SuccessResponse,
)

router = APIRouter()


@router.get("", response_model=List[SecurityPolicyResponse])
def list_policies(
    skip: int = 0,
    limit: int = 100,
    enabled_only: bool = False,
    db: Session = Depends(get_db),
):
    """
    Get all security policies.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        enabled_only: If True, return only enabled policies
        db: Database session

    Returns:
        List of security policies
    """
    query = db.query(SecurityPolicy)

    if enabled_only:
        query = query.filter(SecurityPolicy.enabled == True)

    policies = query.offset(skip).limit(limit).all()
    return policies


from app.agents.llm_client import LLMClient
import json


def _convert_rule_to_executable(db: Session, natural_language_rule: str) -> dict:
    """Use LLM to convert natural language rule to executable JSON."""
    client = LLMClient(db)

    system_prompt = """
    You are a Security Policy Translator.
    Convert the user's natural language security rule into a JSON object strictly following this schema:
    
    1. For blocking ports:
       {"block_ports": [22, 3389, ...]}
       
    2. For required tags:
       {"required_tags": ["Environment", "Owner", ...]}
       
    3. For allowed regions:
       {"allowed_regions": ["us-east-1", "eu-west-1", ...]}
       
    Output ONLY the JSON object. Do not explain.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": natural_language_rule},
    ]

    try:
        response = client.chat(messages, temperature=0.1)
        # Clean up code blocks if present
        if "```" in response:
            response = response.split("```")[1].strip()
            if response.startswith("json"):
                response = response[4:].strip()

        return json.loads(response)
    except Exception as e:
        print(f"Error converting rule: {e}")
        return {}


@router.post(
    "", response_model=SecurityPolicyResponse, status_code=status.HTTP_201_CREATED
)
def create_policy(
    policy_data: SecurityPolicyCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new security policy.
    """
    # Check if policy with same name exists
    existing = (
        db.query(SecurityPolicy).filter(SecurityPolicy.name == policy_data.name).first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Policy with name '{policy_data.name}' already exists",
        )

    # Convert natural language rule to executable JSON
    executable_rule = _convert_rule_to_executable(db, policy_data.natural_language_rule)

    # Create new policy
    policy = SecurityPolicy(
        name=policy_data.name,
        description=policy_data.description,
        natural_language_rule=policy_data.natural_language_rule,
        executable_rule=executable_rule,
        cloud_platform=policy_data.cloud_platform,
        severity=policy_data.severity,
        enabled=policy_data.enabled,
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return policy


@router.get("/{policy_id}", response_model=SecurityPolicyResponse)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific security policy by ID.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Security policy

    Raises:
        HTTPException: If policy not found
    """
    policy = db.query(SecurityPolicy).filter(SecurityPolicy.id == policy_id).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security policy with id {policy_id} not found",
        )

    return policy


@router.put("/{policy_id}", response_model=SecurityPolicyResponse)
def update_policy(
    policy_id: int,
    policy_data: SecurityPolicyUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a security policy.

    Args:
        policy_id: Policy ID
        policy_data: Policy update data
        db: Database session

    Returns:
        Updated policy

    Raises:
        HTTPException: If policy not found or name conflict
    """
    policy = db.query(SecurityPolicy).filter(SecurityPolicy.id == policy_id).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security policy with id {policy_id} not found",
        )

    # Check for name conflict if name is being updated
    if policy_data.name and policy_data.name != policy.name:
        existing = (
            db.query(SecurityPolicy)
            .filter(SecurityPolicy.name == policy_data.name)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Policy with name '{policy_data.name}' already exists",
            )

    # Update fields
    update_data = policy_data.model_dump(exclude_unset=True)

    # If natural_language_rule is changing, re-generate executable_rule
    if "natural_language_rule" in update_data:
        update_data["executable_rule"] = _convert_rule_to_executable(
            db, update_data["natural_language_rule"]
        )

    for field, value in update_data.items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)

    return policy


@router.delete("/{policy_id}", response_model=SuccessResponse)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a security policy.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If policy not found
    """
    policy = db.query(SecurityPolicy).filter(SecurityPolicy.id == policy_id).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security policy with id {policy_id} not found",
        )

    db.delete(policy)
    db.commit()

    return SuccessResponse(
        success=True,
        message=f"Policy '{policy.name}' deleted successfully",
    )


@router.patch("/{policy_id}/toggle", response_model=SecurityPolicyResponse)
def toggle_policy(
    policy_id: int,
    db: Session = Depends(get_db),
):
    """
    Toggle policy enabled status.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Updated policy

    Raises:
        HTTPException: If policy not found
    """
    policy = db.query(SecurityPolicy).filter(SecurityPolicy.id == policy_id).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security policy with id {policy_id} not found",
        )

    policy.enabled = not policy.enabled
    db.commit()
    db.refresh(policy)

    return policy
