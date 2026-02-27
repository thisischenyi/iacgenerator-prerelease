"""Session management API routes."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Session, User
from app.schemas import SessionCreate, SessionResponse

router = APIRouter()


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """List sessions owned by current user."""
    sessions = (
        db.query(Session)
        .filter(Session.user_id == str(current_user.id))
        .order_by(Session.created_at.desc())
        .all()
    )
    return sessions


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Create a new user session.

    Args:
        session_data: Session creation data
        db: Database session

    Returns:
        Created session
    """
    # Generate unique session ID
    session_id = str(uuid.uuid4())

    # Create new session
    session = Session(
        session_id=session_id,
        user_id=str(current_user.id),
        conversation_history=[],
        resource_info=[],  # Fixed: should be a list, not dict
        compliance_results={},
        generated_code={},
        workflow_state="initialized",
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Get session information by session ID.

    Args:
        session_id: Session ID
        db: Database session

    Returns:
        Session information

    Raises:
        HTTPException: If session not found
    """
    session = db.query(Session).filter(Session.session_id == session_id).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found",
        )
    if session.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this session",
        )

    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Delete a session owned by current user."""
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found",
        )
    if session.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this session",
        )

    db.delete(session)
    db.commit()
