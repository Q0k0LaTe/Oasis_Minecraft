"""
Authentication dependencies for FastAPI routers

Provides reusable authentication helpers that can be used across all routers.
Supports both query parameter (backward compatible) and Authorization header.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Header, Query
from sqlalchemy.orm import Session

from database import get_db, User, UserSession


def get_session_token_from_query_or_header(
    session_token: Optional[str] = Query(None, description="Session token (query parameter)"),
    authorization: Optional[str] = Header(None, description="Authorization header (Bearer token)")
) -> Optional[str]:
    """
    Extract session token from query parameter or Authorization header
    
    Supports both:
    - Query parameter: ?session_token=xxx (backward compatible)
    - Header: Authorization: Bearer xxx (new standard)
    
    Returns the token string, or None if not found
    """
    # First try query parameter (for backward compatibility)
    if session_token:
        return session_token
    
    # Then try Authorization header
    if authorization:
        # Support "Bearer <token>" format
        if authorization.startswith("Bearer "):
            return authorization[7:]
        # Also support plain token
        return authorization
    
    return None


async def get_current_user(
    session_token: Optional[str] = Query(None, description="Session token (query parameter)"),
    authorization: Optional[str] = Header(None, description="Authorization header (Bearer token)"),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from session token
    
    Supports token via:
    - Query parameter: ?session_token=xxx (backward compatible)
    - Authorization header: Authorization: Bearer xxx (new standard)
    
    Raises:
        HTTPException 401: If authentication fails or user is disabled
    """
    # Extract token from query or header
    token = get_session_token_from_query_or_header(session_token, authorization)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Find active session
    session = db.query(UserSession).filter(
        UserSession.session_token == token,
        UserSession.is_active == True
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    # Get user and verify active
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled"
        )
    
    return user

