"""
Rate limiting utilities using Redis

Provides simple rate limiting for API endpoints to prevent abuse.
"""
import redis
from typing import Optional, Tuple
from config import REDIS_URL

# Redis client for rate limiting
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def check_rate_limit(
    key: str,
    max_requests: int = 10,
    window_seconds: int = 60
) -> Tuple[bool, Optional[int]]:
    """
    Check if a request should be rate limited
    
    Args:
        key: Unique key for rate limiting (e.g., "ip:127.0.0.1" or "email:user@example.com")
        max_requests: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds
        
    Returns:
        Tuple of (is_allowed, remaining_requests)
        - is_allowed: True if request is allowed, False if rate limited
        - remaining_requests: Number of remaining requests in the window (None if unlimited)
    
    Example:
        allowed, remaining = check_rate_limit("ip:127.0.0.1", max_requests=5, window_seconds=60)
        if not allowed:
            raise HTTPException(429, "Rate limit exceeded")
    """
    try:
        # Get current count
        current = redis_client.get(key)
        
        if current is None:
            # First request in window
            redis_client.setex(key, window_seconds, 1)
            return True, max_requests - 1
        else:
            current_count = int(current)
            if current_count >= max_requests:
                # Rate limit exceeded
                ttl = redis_client.ttl(key)
                return False, 0
            
            # Increment counter
            new_count = redis_client.incr(key)
            if new_count == 1:
                # Set expiration on first increment (in case key was just created)
                redis_client.expire(key, window_seconds)
            
            remaining = max(0, max_requests - new_count)
            return True, remaining
            
    except Exception as e:
        # If Redis fails, allow the request (fail open)
        print(f"Rate limit check failed: {e}")
        return True, None


def get_client_ip(request) -> str:
    """
    Extract client IP address from FastAPI request
    
    Args:
        request: FastAPI Request object
        
    Returns:
        IP address string
    """
    # Check for forwarded IP (from proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"

