"""
IP Rate Limiting Middleware for FastAPI

Provides global IP-based rate limiting with multi-tier support:
- Global limit: Sustained rate over longer window (default: 30 req / 10s)
- Burst limit: Peak rate over short window (default: 10 req / 1s)

Features:
- Path-based rate limit configuration
- Whitelist support for trusted IPs
- Standard rate limit headers (X-RateLimit-*)
- Configurable exclusions for docs, health checks, etc.

Usage:
    from utils.ip_rate_limit_middleware import IPRateLimitMiddleware
    
    app.add_middleware(IPRateLimitMiddleware)
"""
from typing import Callable, Dict, List, Optional, Tuple
import re
from dataclasses import dataclass, field

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from config import (
    RATE_LIMIT_GLOBAL_MAX,
    RATE_LIMIT_GLOBAL_WINDOW,
    RATE_LIMIT_BURST_MAX,
    RATE_LIMIT_BURST_WINDOW,
    RATE_LIMIT_AUTH_MAX,
    RATE_LIMIT_AUTH_WINDOW,
    RATE_LIMIT_VERIFICATION_MAX,
    RATE_LIMIT_VERIFICATION_WINDOW,
    RATE_LIMIT_RESOURCE_MAX,
    RATE_LIMIT_RESOURCE_WINDOW,
    RATE_LIMIT_EXCLUDE_PATHS,
)
from utils.rate_limit import (
    get_client_ip,
    check_multi_tier_rate_limit,
    check_rate_limit_atomic,
    build_rate_limit_headers,
    rate_limit_response_body,
    is_ip_whitelisted,
    RateLimitResult,
)


# =============================================================================
# Path-Based Rate Limit Configuration
# =============================================================================
@dataclass
class PathRateLimit:
    """Rate limit configuration for a specific path pattern"""
    pattern: str  # Regex pattern to match paths
    max_requests: int
    window_seconds: int
    key_suffix: str  # Suffix for Redis key to separate from global
    description: str = ""
    
    def __post_init__(self):
        self._compiled_pattern = re.compile(self.pattern)
    
    def matches(self, path: str) -> bool:
        return bool(self._compiled_pattern.match(path))


# Default path-based rate limits (high-risk endpoints)
DEFAULT_PATH_LIMITS: List[PathRateLimit] = [
    # Auth endpoints - stricter limits
    PathRateLimit(
        pattern=r"^/api/auth/send-verification-code$",
        max_requests=RATE_LIMIT_VERIFICATION_MAX,
        window_seconds=RATE_LIMIT_VERIFICATION_WINDOW,
        key_suffix="verification",
        description="Send verification code - very strict to prevent email abuse"
    ),
    PathRateLimit(
        pattern=r"^/api/auth/login$",
        max_requests=RATE_LIMIT_AUTH_MAX,
        window_seconds=RATE_LIMIT_AUTH_WINDOW,
        key_suffix="login",
        description="Login attempts"
    ),
    PathRateLimit(
        pattern=r"^/api/auth/register$",
        max_requests=RATE_LIMIT_AUTH_MAX,
        window_seconds=RATE_LIMIT_AUTH_WINDOW,
        key_suffix="register",
        description="Registration attempts"
    ),
    PathRateLimit(
        pattern=r"^/api/auth/verify-code$",
        max_requests=RATE_LIMIT_AUTH_MAX,
        window_seconds=RATE_LIMIT_AUTH_WINDOW,
        key_suffix="verify",
        description="Code verification attempts"
    ),
    PathRateLimit(
        pattern=r"^/api/auth/google-login$",
        max_requests=RATE_LIMIT_AUTH_MAX,
        window_seconds=RATE_LIMIT_AUTH_WINDOW,
        key_suffix="google-login",
        description="Google OAuth login attempts"
    ),
    PathRateLimit(
        pattern=r"^/api/auth/set-username$",
        max_requests=RATE_LIMIT_AUTH_MAX,
        window_seconds=RATE_LIMIT_AUTH_WINDOW,
        key_suffix="set-username",
        description="Set username attempts"
    ),
    PathRateLimit(
        pattern=r"^/api/auth/reactivate$",
        max_requests=RATE_LIMIT_AUTH_MAX,
        window_seconds=RATE_LIMIT_AUTH_WINDOW,
        key_suffix="reactivate",
        description="Account reactivation attempts"
    ),
    
    # Resource-intensive endpoints
    PathRateLimit(
        pattern=r"^/api/runs/workspace/[^/]+/build$",
        max_requests=RATE_LIMIT_RESOURCE_MAX,
        window_seconds=RATE_LIMIT_RESOURCE_WINDOW,
        key_suffix="build",
        description="Build triggers - resource intensive"
    ),
    PathRateLimit(
        pattern=r"^/api/conversations/[^/]+/messages$",
        max_requests=RATE_LIMIT_RESOURCE_MAX * 2,  # Slightly more lenient
        window_seconds=RATE_LIMIT_RESOURCE_WINDOW,
        key_suffix="messages",
        description="AI message generation"
    ),
    
    # Subscription endpoints
    PathRateLimit(
        pattern=r"^/api/subscriptions$",
        max_requests=5,
        window_seconds=60,
        key_suffix="subscribe",
        description="Email subscription"
    ),
]


# =============================================================================
# Middleware Implementation
# =============================================================================
class IPRateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for IP-based rate limiting
    
    Features:
    - Global rate limit for all endpoints
    - Path-specific rate limits for high-risk endpoints
    - Whitelist support for trusted IPs
    - Standard rate limit headers
    
    Args:
        app: FastAPI application
        exclude_paths: List of exact paths to exclude from rate limiting
        path_limits: List of PathRateLimit configurations (overrides defaults if provided)
        global_max: Global rate limit max requests
        global_window: Global rate limit window in seconds
        burst_max: Burst rate limit max requests
        burst_window: Burst rate limit window in seconds
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[List[str]] = None,
        path_limits: Optional[List[PathRateLimit]] = None,
        global_max: int = RATE_LIMIT_GLOBAL_MAX,
        global_window: int = RATE_LIMIT_GLOBAL_WINDOW,
        burst_max: int = RATE_LIMIT_BURST_MAX,
        burst_window: int = RATE_LIMIT_BURST_WINDOW,
    ):
        super().__init__(app)
        self.exclude_paths = set(exclude_paths or RATE_LIMIT_EXCLUDE_PATHS)
        self.path_limits = path_limits or DEFAULT_PATH_LIMITS
        self.global_max = global_max
        self.global_window = global_window
        self.burst_max = burst_max
        self.burst_window = burst_window
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through rate limiting"""
        path = request.url.path
        method = request.method
        
        # Skip excluded paths
        if self._should_exclude(path):
            return await call_next(request)
        
        # Skip OPTIONS requests (CORS preflight)
        if method == "OPTIONS":
            return await call_next(request)
        
        # Get client IP
        client_ip = get_client_ip(request)
        
        # Check if whitelisted
        if is_ip_whitelisted(client_ip):
            return await call_next(request)
        
        # Check path-specific rate limit first
        path_result = self._check_path_rate_limit(client_ip, path, method)
        if path_result and not path_result.allowed:
            return self._rate_limit_response(path_result)
        
        # Check global rate limit (multi-tier: global + burst)
        global_result = check_multi_tier_rate_limit(
            ip=client_ip,
            global_max=self.global_max,
            global_window=self.global_window,
            burst_max=self.burst_max,
            burst_window=self.burst_window,
        )
        
        if not global_result.allowed:
            return self._rate_limit_response(global_result)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to successful responses
        # Use the most restrictive result for headers
        result_for_headers = path_result if path_result else global_result
        for header, value in build_rate_limit_headers(result_for_headers).items():
            response.headers[header] = value
        
        return response
    
    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from rate limiting"""
        # Exact match
        if path in self.exclude_paths:
            return True
        
        # Prefix match for static files
        if path.startswith("/static/") or path.startswith("/favicon"):
            return True
        
        return False
    
    def _check_path_rate_limit(
        self,
        client_ip: str,
        path: str,
        method: str
    ) -> Optional[RateLimitResult]:
        """Check path-specific rate limit if applicable"""
        # Only check for POST/PUT/PATCH/DELETE (mutating operations)
        # GET requests typically don't need path-specific limits
        if method not in ("POST", "PUT", "PATCH", "DELETE"):
            return None
        
        for limit in self.path_limits:
            if limit.matches(path):
                key = f"rl:ip:{client_ip}:path:{limit.key_suffix}"
                result = check_rate_limit_atomic(
                    key=key,
                    max_requests=limit.max_requests,
                    window_seconds=limit.window_seconds
                )
                result.tier = f"path:{limit.key_suffix}"
                return result
        
        return None
    
    def _rate_limit_response(self, result: RateLimitResult) -> JSONResponse:
        """Build rate limit exceeded response"""
        return JSONResponse(
            status_code=429,
            content=rate_limit_response_body(result),
            headers=build_rate_limit_headers(result)
        )


# =============================================================================
# SSE-Specific Rate Limiter (for long-running connections)
# =============================================================================
class SSEConnectionLimiter:
    """
    Rate limiter for SSE connections
    
    Unlike request-based rate limiting, this tracks active connections
    rather than request count. This prevents users from opening too many
    simultaneous SSE streams.
    
    Note: This is a simpler in-memory implementation since SSE connections
    are long-lived and we need to track active connections, not just count.
    For multi-instance deployments, consider using Redis pub/sub for coordination.
    """
    
    def __init__(self, max_connections_per_ip: int = 10):
        self.max_connections = max_connections_per_ip
        self._connections: Dict[str, int] = {}
        self._lock = __import__("threading").Lock()
    
    def acquire(self, ip: str) -> bool:
        """Try to acquire an SSE connection slot for an IP"""
        with self._lock:
            current = self._connections.get(ip, 0)
            if current >= self.max_connections:
                return False
            self._connections[ip] = current + 1
            return True
    
    def release(self, ip: str) -> None:
        """Release an SSE connection slot for an IP"""
        with self._lock:
            current = self._connections.get(ip, 0)
            if current > 0:
                self._connections[ip] = current - 1
                if self._connections[ip] == 0:
                    del self._connections[ip]
    
    def get_count(self, ip: str) -> int:
        """Get current connection count for an IP"""
        return self._connections.get(ip, 0)


# Global SSE limiter instance
sse_limiter = SSEConnectionLimiter()

