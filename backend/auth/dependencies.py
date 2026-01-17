"""
Authentication dependencies for FastAPI routers

Provides reusable authentication helpers that can be used across all routers.
Supports HttpOnly Cookie (primary) and Authorization header (for API clients).

Security:
- HttpOnly Cookie: Primary method, prevents XSS attacks
- Bearer Token in Header: For programmatic API access
- Session expiration: Tokens expire after configured duration
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status, Header, Cookie
from sqlalchemy.orm import Session

from database import get_db, User, UserSession


def get_session_token(
    session_token: Optional[str] = Cookie(None, alias="session_token"),
    authorization: Optional[str] = Header(None, description="Authorization header (Bearer token)")
) -> Optional[str]:
    """
    Extract session token from Cookie or Authorization header
    
    Priority:
    1. HttpOnly Cookie (browser sessions)
    2. Authorization: Bearer xxx (API clients)
    
    Note: Query parameter support has been removed for security reasons.
    Passing tokens in URLs exposes them in logs, browser history, and referrer headers.
    
    Returns the token string, or None if not found
    """
    # First try Cookie (primary method for browser sessions)
    if session_token:
        return session_token
    
    # Then try Authorization header (for API clients)
    if authorization:
        # Support "Bearer <token>" format
        if authorization.startswith("Bearer "):
            return authorization[7:]
        # Also support plain token for flexibility
        return authorization
    
    return None


async def get_current_user(
    session_token: Optional[str] = Cookie(None, alias="session_token"),
    authorization: Optional[str] = Header(None, description="Authorization header (Bearer token)"),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from session token
    
    Supports token via:
    - HttpOnly Cookie: session_token (primary, browser sessions)
    - Authorization header: Bearer xxx (API clients)
    
    Validates:
    - Token exists and is active
    - Session has not expired
    - User exists and is active
    
    Raises:
        HTTPException 401: If authentication fails or user is disabled
    """
    # Extract token from cookie or header
    token = get_session_token(session_token, authorization)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Find active and non-expired session
    now = datetime.now(timezone.utc)
    session = db.query(UserSession).filter(
        UserSession.session_token == token,
        UserSession.is_active == True,
        UserSession.expires_at > now
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Get user and verify active
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


async def get_current_user_optional(
    session_token: Optional[str] = Cookie(None, alias="session_token"),
    authorization: Optional[str] = Header(None, description="Authorization header (Bearer token)"),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    
    Useful for endpoints that work both with and without authentication,
    providing different responses based on auth status.
    """
    token = get_session_token(session_token, authorization)
    
    if not token:
        return None
    
    # Find active and non-expired session
    now = datetime.now(timezone.utc)
    session = db.query(UserSession).filter(
        UserSession.session_token == token,
        UserSession.is_active == True,
        UserSession.expires_at > now
    ).first()
    
    if not session:
        return None
    
    # Get user and verify active
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        return None
    
    return user
