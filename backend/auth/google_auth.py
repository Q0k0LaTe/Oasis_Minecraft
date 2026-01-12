"""
Google OAuth authentication utilities
Handles Google ID Token verification and user information extraction
"""
from google.auth.transport import requests
from google.oauth2 import id_token
from typing import Dict, Optional
import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import GOOGLE_CLIENT_ID


def verify_google_token(id_token_string: str) -> Optional[Dict[str, any]]:
    """
    Verify Google ID Token and extract user information
    
    Args:
        id_token_string: The Google ID Token string from the client
        
    Returns:
        Dictionary containing user information if token is valid:
        {
            'sub': Google user ID,
            'email': User email,
            'name': User display name,
            'picture': User avatar URL,
            'email_verified': Whether email is verified
        }
        None if token is invalid
        
    Raises:
        ValueError: If token verification fails
    """
    if not GOOGLE_CLIENT_ID:
        raise ValueError('Google Client ID not configured')
    
    try:
        # Verify the token
        # This will raise ValueError if token is invalid
        idinfo = id_token.verify_oauth2_token(
            id_token_string,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        # Verify that the token was issued for our client
        if idinfo['aud'] != GOOGLE_CLIENT_ID:
            raise ValueError('Token audience mismatch')
        
        # Extract user information
        user_info = {
            'sub': idinfo.get('sub'),  # Google user ID
            'email': idinfo.get('email'),
            'name': idinfo.get('name'),
            'picture': idinfo.get('picture'),
            'email_verified': idinfo.get('email_verified', False)
        }
        
        # Ensure email is verified for security
        if not user_info['email_verified']:
            raise ValueError('Email not verified by Google')
        
        return user_info
        
    except ValueError as e:
        # Token verification failed
        return None
    except Exception as e:
        # Other errors (network, etc.)
        return None

