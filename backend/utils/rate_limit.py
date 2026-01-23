"""
Rate limiting utilities using Redis

Provides rate limiting for API endpoints to prevent abuse.

Features:
- Atomic Redis operations using Lua scripts (no race conditions)
- Multi-tier rate limiting (global + burst windows)
- Local fallback when Redis is unavailable
- Configurable fail-open/fail-closed behavior

Security: Fail-Closed by default - if Redis is unavailable, requests are denied
to prevent abuse during outages. Can be configured to use local fallback.
"""
import time
import threading
import warnings
import ipaddress
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any
import redis
from config import (
    REDIS_URL,
    RATE_LIMIT_GLOBAL_MAX,
    RATE_LIMIT_GLOBAL_WINDOW,
    RATE_LIMIT_BURST_MAX,
    RATE_LIMIT_BURST_WINDOW,
    RATE_LIMIT_WHITELIST_IPS,
    RATE_LIMIT_FAIL_MODE,
)

# =============================================================================
# Configuration
# =============================================================================
import os

# Fail-Closed mode (default: True for security)
# Set RATE_LIMIT_FAIL_OPEN=true to allow requests when Redis fails (NOT recommended for production)
FAIL_OPEN = os.getenv("RATE_LIMIT_FAIL_OPEN", "false").lower() == "true" or RATE_LIMIT_FAIL_MODE == "open"

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
# Rate Limit Result Data Class
# =============================================================================
@dataclass
class RateLimitResult:
    """Result of a rate limit check"""
    allowed: bool
    remaining: int
    limit: int
    reset_after: float  # seconds until window resets
    retry_after: Optional[float] = None  # seconds to wait if blocked
    tier: str = "global"  # which tier blocked ("global", "burst", or "allowed")


# =============================================================================
# Lua Script for Atomic Rate Limiting
# =============================================================================
# This script atomically increments counter and checks limit
# Returns: [current_count, ttl_remaining, is_new_key]
RATE_LIMIT_LUA_SCRIPT = """
local key = KEYS[1]
local max_requests = tonumber(ARGV[1])
local window_seconds = tonumber(ARGV[2])

local current = redis.call('GET', key)
if current == false then
    -- Key doesn't exist, create it
    redis.call('SETEX', key, window_seconds, 1)
    return {1, window_seconds, 1}
end

local count = tonumber(current)
if count >= max_requests then
    -- Rate limit exceeded, return current count and TTL
    local ttl = redis.call('TTL', key)
    return {count, ttl, 0}
end

-- Increment and return
local new_count = redis.call('INCR', key)
local ttl = redis.call('TTL', key)
return {new_count, ttl, 0}
"""

# =============================================================================
# Redis Client
# =============================================================================
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2.0)
    # Test connection on startup
    redis_client.ping()
    _redis_available = True
    # Register Lua script
    _rate_limit_script = redis_client.register_script(RATE_LIMIT_LUA_SCRIPT)
except Exception as e:
    warnings.warn(
        f"⚠️  Redis connection failed on startup: {e}. "
        f"Rate limiting will use {'local fallback' if LOCAL_FALLBACK_ENABLED else 'fail-closed mode'}.",
        RuntimeWarning
    )
    redis_client = None
    _redis_available = False
    _rate_limit_script = None


# =============================================================================
# IP Whitelist Check
# =============================================================================
def _parse_whitelist() -> List[ipaddress.IPv4Network | ipaddress.IPv6Network | str]:
    """Parse whitelist IPs into network objects for efficient matching"""
    result = []
    for ip_str in RATE_LIMIT_WHITELIST_IPS:
        try:
            # Try to parse as network (CIDR notation)
            if '/' in ip_str:
                result.append(ipaddress.ip_network(ip_str, strict=False))
            else:
                # Single IP - wrap in /32 or /128
                addr = ipaddress.ip_address(ip_str)
                if isinstance(addr, ipaddress.IPv4Address):
                    result.append(ipaddress.ip_network(f"{ip_str}/32"))
                else:
                    result.append(ipaddress.ip_network(f"{ip_str}/128"))
        except ValueError:
            # Keep as string for exact match
            result.append(ip_str)
    return result


_whitelist_networks = _parse_whitelist()


def is_ip_whitelisted(ip: str) -> bool:
    """Check if an IP address is in the whitelist"""
    if not ip or ip == "unknown":
        return False
    
    try:
        ip_addr = ipaddress.ip_address(ip)
        for network in _whitelist_networks:
            if isinstance(network, str):
                if ip == network:
                    return True
            else:
                if ip_addr in network:
                    return True
    except ValueError:
        # Invalid IP, check exact match
        return ip in RATE_LIMIT_WHITELIST_IPS
    
    return False


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
# Main Rate Limiting Function (Legacy - Backward Compatible)
# =============================================================================
def check_rate_limit(
    key: str,
    max_requests: int = 10,
    window_seconds: int = 60
) -> Tuple[bool, Optional[int]]:
    """
    Check if a request should be rate limited (Legacy API, backward compatible)
    
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
    result = check_rate_limit_atomic(key, max_requests, window_seconds)
    return result.allowed, result.remaining if result.allowed else 0


def check_rate_limit_atomic(
    key: str,
    max_requests: int = 10,
    window_seconds: int = 60
) -> RateLimitResult:
    """
    Check rate limit using atomic Lua script (recommended for new code)
    
    Args:
        key: Unique key for rate limiting (e.g., "rl:ip:127.0.0.1:global")
        max_requests: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds
        
    Returns:
        RateLimitResult with detailed information
    """
    global _redis_failure_logged
    
    # Try Redis first with atomic Lua script
    if redis_client is not None and _rate_limit_script is not None:
        try:
            result = _rate_limit_script(keys=[key], args=[max_requests, window_seconds])
            current_count, ttl, _ = result
            
            allowed = current_count <= max_requests
            remaining = max(0, max_requests - current_count)
            
            _redis_failure_logged = False  # Reset failure flag on success
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                limit=max_requests,
                reset_after=float(ttl) if ttl > 0 else float(window_seconds),
                retry_after=float(ttl) if not allowed and ttl > 0 else None,
                tier="global"
            )
                
        except Exception as e:
            # Redis operation failed - log once to avoid spam
            if not _redis_failure_logged:
                print(f"🚨 ALERT: Redis rate limit check failed: {e}")
                print(f"   Fallback mode: {'local limiter' if LOCAL_FALLBACK_ENABLED else ('FAIL-OPEN (UNSAFE!)' if FAIL_OPEN else 'fail-closed')}")
                _redis_failure_logged = True
    
    # Redis unavailable or failed - apply fallback strategy
    allowed, remaining = _handle_redis_failure(key, max_requests, window_seconds)
    return RateLimitResult(
        allowed=allowed,
        remaining=remaining if remaining is not None else 0,
        limit=max_requests,
        reset_after=float(window_seconds),
        retry_after=float(window_seconds) if not allowed else None,
        tier="fallback"
    )


def check_multi_tier_rate_limit(
    ip: str,
    global_max: int = RATE_LIMIT_GLOBAL_MAX,
    global_window: int = RATE_LIMIT_GLOBAL_WINDOW,
    burst_max: int = RATE_LIMIT_BURST_MAX,
    burst_window: int = RATE_LIMIT_BURST_WINDOW,
    key_prefix: str = "rl:ip"
) -> RateLimitResult:
    """
    Check rate limit across multiple tiers (global + burst)
    
    This implements a two-tier rate limiting strategy:
    1. Burst limit: Short window (1s) to prevent sudden spikes
    2. Global limit: Longer window (10s) to prevent sustained abuse
    
    Args:
        ip: Client IP address
        global_max: Max requests in global window
        global_window: Global window in seconds
        burst_max: Max requests in burst window
        burst_window: Burst window in seconds
        key_prefix: Prefix for Redis keys
        
    Returns:
        RateLimitResult from the most restrictive tier
    """
    # Check if IP is whitelisted
    if is_ip_whitelisted(ip):
        return RateLimitResult(
            allowed=True,
            remaining=global_max,
            limit=global_max,
            reset_after=0,
            tier="whitelist"
        )
    
    # Check burst limit first (more likely to block sudden spikes)
    burst_key = f"{key_prefix}:{ip}:burst"
    burst_result = check_rate_limit_atomic(burst_key, burst_max, burst_window)
    burst_result.tier = "burst"
    
    if not burst_result.allowed:
        return burst_result
    
    # Check global limit
    global_key = f"{key_prefix}:{ip}:global"
    global_result = check_rate_limit_atomic(global_key, global_max, global_window)
    global_result.tier = "global"
    
    if not global_result.allowed:
        return global_result
    
    # Both passed - return the more restrictive remaining count
    if burst_result.remaining < global_result.remaining:
        return burst_result
    return global_result


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
    
    Handles reverse proxy scenarios by checking common headers.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        IP address string
    """
    # Check for forwarded IP (from proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one (original client)
        # Format: "client, proxy1, proxy2"
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Check for CF-Connecting-IP (Cloudflare)
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    
    # Check for True-Client-IP (Akamai, Cloudflare Enterprise)
    true_client_ip = request.headers.get("True-Client-IP")
    if true_client_ip:
        return true_client_ip.strip()
    
    # Fallback to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


def build_rate_limit_headers(result: RateLimitResult) -> Dict[str, str]:
    """
    Build rate limit response headers
    
    Args:
        result: RateLimitResult from rate limit check
        
    Returns:
        Dict of header name -> value
    """
    headers = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(int(time.time() + result.reset_after)),
    }
    
    if result.retry_after is not None:
        headers["Retry-After"] = str(int(result.retry_after))
    
    return headers


def rate_limit_response_body(result: RateLimitResult) -> Dict[str, Any]:
    """
    Build standard rate limit error response body
    
    Args:
        result: RateLimitResult from rate limit check
        
    Returns:
        Dict suitable for JSON response
    """
    return {
        "detail": "Too many requests. Please slow down.",
        "error": "rate_limit_exceeded",
        "retry_after_seconds": int(result.retry_after) if result.retry_after else int(result.reset_after),
        "limit": result.limit,
        "tier": result.tier,
    }
