"""
Email verification code management
Uses Redis to store verification codes with expiration
"""
import random
import string
import redis
from typing import Optional
from config import REDIS_URL, VERIFICATION_CODE_EXPIRE_MINUTES, VERIFICATION_CODE_LENGTH

# Redis client for storing verification codes
# Format: verification_code:{email} -> code
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def normalize_email(email: str) -> str:
    """
    Normalize email address to lowercase for consistent storage and lookup
    
    Args:
        email: Email address to normalize
        
    Returns:
        Lowercase email address
        
    Reason:
        - Email addresses should be case-insensitive for storage/retrieval
        - Prevents issues when user types "Test@Example.com" vs "test@example.com"
        - RFC 5321 specifies that local part can be case-sensitive, but in practice
          most systems treat emails as case-insensitive for user convenience
    """
    return email.lower()


def generate_verification_code(length: int = VERIFICATION_CODE_LENGTH) -> str:
    """
    Generate a random verification code
    
    Args:
        length: Length of the code (default: 6)
        
    Returns:
        Random numeric code string
        
    Reason:
        - Generates numeric codes for easy user input
        - Configurable length for security vs usability tradeoff
    """
    return ''.join(random.choices(string.digits, k=length))


def store_verification_code(email: str, code: str, expire_minutes: int = VERIFICATION_CODE_EXPIRE_MINUTES) -> bool:
    """
    Store verification code in Redis with expiration
    
    Args:
        email: User's email address
        code: Verification code to store
        expire_minutes: Expiration time in minutes
        
    Returns:
        True if successful, False otherwise
        
    Reason:
        - Uses Redis for fast access and automatic expiration
        - Prevents code reuse after expiration
        - Key format: verification_code:{email}
        - Email is normalized to lowercase for consistent lookup
    """
    try:
        normalized_email = normalize_email(email)
        key = f"verification_code:{normalized_email}"
        redis_client.setex(key, expire_minutes * 60, code)
        return True
    except Exception as e:
        print(f"Error storing verification code: {e}")
        return False


def check_code(email: str, code: str) -> bool:
    """
    Check if a code matches stored code for email (without deleting)
    
    Args:
        email: User's email address
        code: Code to check
        
    Returns:
        True if code matches and is valid, False otherwise
        
    Reason:
        - Checks if code exists and matches without deleting
        - Used for verification endpoints that don't consume the code
        - Email is normalized to lowercase for consistent lookup
    """
    try:
        normalized_email = normalize_email(email)
        key = f"verification_code:{normalized_email}"
        stored_code = redis_client.get(key)
        
        if not stored_code:
            return False
        
        return stored_code == code
    except Exception as e:
        print(f"Error checking code: {e}")
        return False


def verify_code(email: str, code: str) -> bool:
    """
    Verify a code against stored code for email and delete it
    
    Args:
        email: User's email address
        code: Code to verify
        
    Returns:
        True if code matches and is valid, False otherwise
        
    Reason:
        - Checks if code exists and matches
        - Automatically deletes code after successful verification (one-time use)
        - Should be used when the code is consumed (e.g., during registration)
        - Email is normalized to lowercase for consistent lookup
    """
    try:
        normalized_email = normalize_email(email)
        key = f"verification_code:{normalized_email}"
        stored_code = redis_client.get(key)
        
        if not stored_code:
            return False
        
        if stored_code == code:
            # Delete code after successful verification (one-time use)
            redis_client.delete(key)
            return True
        
        return False
    except Exception as e:
        print(f"Error verifying code: {e}")
        return False


def get_verification_code(email: str) -> Optional[str]:
    """
    Get stored verification code for email (for testing/debugging)
    
    Args:
        email: User's email address
        
    Returns:
        Stored code or None if not found/expired
        
    Reason:
        - Email is normalized to lowercase for consistent lookup
    """
    try:
        normalized_email = normalize_email(email)
        key = f"verification_code:{normalized_email}"
        return redis_client.get(key)
    except Exception:
        return None


def delete_verification_code(email: str) -> bool:
    """
    Delete verification code for email
    
    Args:
        email: User's email address
        
    Returns:
        True if successful
        
    Reason:
        - Email is normalized to lowercase for consistent lookup
    """
    try:
        normalized_email = normalize_email(email)
        key = f"verification_code:{normalized_email}"
        redis_client.delete(key)
        return True
    except Exception:
        return False

