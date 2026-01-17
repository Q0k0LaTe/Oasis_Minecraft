"""
Admin authentication and authorization

Provides dependencies for admin-only endpoints.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db, User
from auth.dependencies import get_current_user
from config import ADMIN_EMAILS


async def get_admin_user(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user and verify admin status
    
    Admin status is determined by checking if user's email is in ADMIN_EMAILS list.
    This is a simple approach suitable for small teams.
    
    For production with many admins, consider:
    - Adding is_admin boolean field to User model
    - Using role-based access control (RBAC)
    - Using permission-based system
    
    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If user is not an admin
    """
    # Check if user email is in admin list
    normalized_email = user.email.lower()
    if normalized_email not in ADMIN_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return user

