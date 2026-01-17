"""
Rate limiting utilities using Redis

Provides simple rate limiting for API endpoints to prevent abuse.

Security: Fail-Closed by default - if Redis is unavailable, requests are denied
to prevent abuse during outages. Can be configured to use local fallback.
"""
import time
import threading
import warnings
from collections import defaultdict
from typing import Optional, Tuple
import redis
from config import REDIS_URL

# =============================================================================
# Configuration
# =============================================================================
import os

# Fail-Closed mode (default: True for security)
# Set RATE_LIMIT_FAIL_OPEN=true to allow requests when Redis fails (NOT recommended for production)
FAIL_OPEN = os.getenv("RATE_LIMIT_FAIL_OPEN", "false").lower() == "true"

# Enable local fallback when Redis fails (provides degraded rate limiting instead of blocking all)
# This is safer than FAIL_OPEN as it still provides some protection
LOCAL_FALLBACK_ENABLED = os.getenv("RATE_LIMIT_LOCAL_FALLBACK", "true").lower() == "true"

# Warn on startup if using unsafe configuration
if FAIL_OPEN:
    warnings.warn(
        "⚠️  RATE_LIMIT_FAIL_OPEN=true is set. This is a security risk! "
        "Rate limiting will be disabled when Redis is unavailable. "
        "Consider using RATE_LIMIT_LOCAL_FALLBACK=true instead for degraded protection.",
        RuntimeWarning
    )

# =============================================================================
# Redis Client
# =============================================================================
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2.0)
    # Test connection on startup
    redis_client.ping()
    _redis_available = True
except Exception as e:
    warnings.warn(
        f"⚠️  Redis connection failed on startup: {e}. "
        f"Rate limiting will use {'local fallback' if LOCAL_FALLBACK_ENABLED else 'fail-closed mode'}.",
        RuntimeWarning
    )
    redis_client = None
    _redis_available = False


# =============================================================================
# Local Fallback Rate Limiter (Thread-Safe)
# =============================================================================
class LocalRateLimiter:
    """
    Simple in-memory rate limiter as fallback when Redis is unavailable.
    
    Limitations compared to Redis:
    - Not shared across multiple server instances
    - Memory grows with unique keys (includes periodic cleanup)
    - Less precise timing (uses simple sliding window approximation)
    
    This is a degraded mode - better than nothing, but Redis should be restored ASAP.
    """
    
    def __init__(self, cleanup_interval: int = 300):
        self._data: dict = defaultdict(lambda: {"count": 0, "window_start": 0})
        self._lock = threading.Lock()
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
    
    def check(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """Check rate limit using local storage"""
        now = time.time()
        
        with self._lock:
            # Periodic cleanup to prevent memory growth
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup(now)
                self._last_cleanup = now
            
            entry = self._data[key]
            
            # Reset window if expired
            if now - entry["window_start"] > window_seconds:
                entry["count"] = 0
                entry["window_start"] = now
            
            # Check limit
            if entry["count"] >= max_requests:
                return False, 0
            
            # Increment and allow
            entry["count"] += 1
            remaining = max(0, max_requests - entry["count"])
            return True, remaining
    
    def _cleanup(self, now: float):
        """Remove expired entries to prevent memory growth"""
        # Keep entries from the last hour at most
        max_age = 3600
        keys_to_remove = [
            k for k, v in self._data.items()
            if now - v["window_start"] > max_age
        ]
        for k in keys_to_remove:
            del self._data[k]


# Global local rate limiter instance
_local_limiter = LocalRateLimiter()

# Track Redis failure state for logging (avoid log spam)
_redis_failure_logged = False


# =============================================================================
# Main Rate Limiting Function
# =============================================================================
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
        - remaining_requests: Number of remaining requests in the window (None if unknown)
    
    Security behavior on Redis failure:
        - Default (Fail-Closed): Returns (False, 0) - denies request
        - With LOCAL_FALLBACK_ENABLED: Uses in-memory rate limiter (degraded but protected)
        - With FAIL_OPEN=true: Returns (True, None) - allows request (NOT RECOMMENDED)
    
    Example:
        allowed, remaining = check_rate_limit("ip:127.0.0.1", max_requests=5, window_seconds=60)
        if not allowed:
            raise HTTPException(429, "Rate limit exceeded")
    """
    global _redis_failure_logged
    
    # Try Redis first
    if redis_client is not None:
        try:
            # Get current count
            current = redis_client.get(key)
            
            if current is None:
                # First request in window
                redis_client.setex(key, window_seconds, 1)
                _redis_failure_logged = False  # Reset failure flag on success
                return True, max_requests - 1
            else:
                current_count = int(current)
                if current_count >= max_requests:
                    # Rate limit exceeded
                    return False, 0
                
                # Increment counter
                new_count = redis_client.incr(key)
                if new_count == 1:
                    # Set expiration on first increment (in case key was just created)
                    redis_client.expire(key, window_seconds)
                
                remaining = max(0, max_requests - new_count)
                _redis_failure_logged = False  # Reset failure flag on success
                return True, remaining
                
        except Exception as e:
            # Redis operation failed - log once to avoid spam
            if not _redis_failure_logged:
                # Use proper logging in production
                print(f"🚨 ALERT: Redis rate limit check failed: {e}")
                print(f"   Fallback mode: {'local limiter' if LOCAL_FALLBACK_ENABLED else ('FAIL-OPEN (UNSAFE!)' if FAIL_OPEN else 'fail-closed')}")
                _redis_failure_logged = True
    
    # Redis unavailable or failed - apply fallback strategy
    return _handle_redis_failure(key, max_requests, window_seconds)


def _handle_redis_failure(
    key: str,
    max_requests: int,
    window_seconds: int
) -> Tuple[bool, Optional[int]]:
    """
    Handle rate limiting when Redis is unavailable
    
    Security priority:
    1. Local fallback (if enabled) - degraded but still protected
    2. Fail-closed (default) - deny request for safety
    3. Fail-open (if explicitly enabled) - allow request (UNSAFE)
    """
    # Option 1: Use local fallback (recommended degraded mode)
    if LOCAL_FALLBACK_ENABLED:
        return _local_limiter.check(key, max_requests, window_seconds)
    
    # Option 2: Fail-open if explicitly configured (NOT recommended)
    if FAIL_OPEN:
        return True, None
    
    # Option 3: Fail-closed (default, most secure)
    # Deny the request when we can't verify rate limits
    return False, 0


def is_redis_healthy() -> bool:
    """
    Check if Redis is currently healthy
    
    Useful for health checks and monitoring.
    """
    if redis_client is None:
        return False
    try:
        redis_client.ping()
        return True
    except Exception:
        return False


# =============================================================================
# Utility Functions
# =============================================================================
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
