"""
Cookie utilities for secure session management

Implements HttpOnly cookie-based authentication:
- HttpOnly: Prevents XSS attacks from reading the token
- Secure: Only sent over HTTPS (in production)
- SameSite: CSRF protection
"""
from fastapi import Response
from config import (
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_MAX_AGE,
    SESSION_COOKIE_SECURE,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_DOMAIN,
)


def set_session_cookie(response: Response, token: str) -> None:
    """
    Set HttpOnly session cookie in response
    
    Args:
        response: FastAPI Response object
        token: Session token (UUID string)
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,              # JS cannot read this cookie (XSS protection)
        secure=SESSION_COOKIE_SECURE,  # Only HTTPS in production
        samesite=SESSION_COOKIE_SAMESITE,  # CSRF protection
        domain=SESSION_COOKIE_DOMAIN,  # None for same-domain
        path="/",                   # Available for all paths
    )


def clear_session_cookie(response: Response) -> None:
    """
    Clear session cookie from response
    
    Args:
        response: FastAPI Response object
    """
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        domain=SESSION_COOKIE_DOMAIN,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
    )

