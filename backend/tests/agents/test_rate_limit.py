"""
Unit tests for rate limiting utilities

Tests the rate_limit.py module including:
- Atomic rate limiting with Lua scripts
- Multi-tier rate limiting (global + burst)
- IP whitelist checking
- Local fallback behavior
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock

# Import the modules to test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from utils.rate_limit import (
    check_rate_limit,
    check_rate_limit_atomic,
    check_multi_tier_rate_limit,
    get_client_ip,
    is_ip_whitelisted,
    build_rate_limit_headers,
    rate_limit_response_body,
    RateLimitResult,
    LocalRateLimiter,
)


class TestRateLimitResult:
    """Tests for RateLimitResult dataclass"""
    
    def test_allowed_result(self):
        """Test creating an allowed result"""
        result = RateLimitResult(
            allowed=True,
            remaining=5,
            limit=10,
            reset_after=60.0,
            tier="global"
        )
        assert result.allowed is True
        assert result.remaining == 5
        assert result.limit == 10
        assert result.reset_after == 60.0
        assert result.retry_after is None
        assert result.tier == "global"
    
    def test_blocked_result(self):
        """Test creating a blocked result"""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            limit=10,
            reset_after=30.0,
            retry_after=30.0,
            tier="burst"
        )
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after == 30.0
        assert result.tier == "burst"


class TestIPWhitelist:
    """Tests for IP whitelist functionality"""
    
    def test_localhost_whitelisted(self):
        """Test that localhost is whitelisted by default"""
        # Note: This depends on RATE_LIMIT_WHITELIST_IPS configuration
        # Default includes 127.0.0.1 and ::1
        assert is_ip_whitelisted("127.0.0.1") is True
    
    def test_ipv6_localhost_whitelisted(self):
        """Test that IPv6 localhost is whitelisted"""
        assert is_ip_whitelisted("::1") is True
    
    def test_unknown_ip_not_whitelisted(self):
        """Test that unknown marker is not whitelisted"""
        assert is_ip_whitelisted("unknown") is False
    
    def test_empty_ip_not_whitelisted(self):
        """Test that empty IP is not whitelisted"""
        assert is_ip_whitelisted("") is False
    
    def test_random_ip_not_whitelisted(self):
        """Test that random IPs are not whitelisted by default"""
        assert is_ip_whitelisted("8.8.8.8") is False
        assert is_ip_whitelisted("192.168.1.1") is False


class TestGetClientIP:
    """Tests for IP extraction from requests"""
    
    def test_x_forwarded_for(self):
        """Test extraction from X-Forwarded-For header"""
        request = Mock()
        request.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 9.10.11.12"}
        request.client = None
        
        assert get_client_ip(request) == "1.2.3.4"
    
    def test_x_real_ip(self):
        """Test extraction from X-Real-IP header"""
        request = Mock()
        request.headers = {"X-Real-IP": "1.2.3.4"}
        request.client = None
        
        assert get_client_ip(request) == "1.2.3.4"
    
    def test_cf_connecting_ip(self):
        """Test extraction from CF-Connecting-IP header (Cloudflare)"""
        request = Mock()
        request.headers = {"CF-Connecting-IP": "1.2.3.4"}
        request.client = None
        
        assert get_client_ip(request) == "1.2.3.4"
    
    def test_direct_client(self):
        """Test extraction from direct client connection"""
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "1.2.3.4"
        
        assert get_client_ip(request) == "1.2.3.4"
    
    def test_no_ip_available(self):
        """Test when no IP is available"""
        request = Mock()
        request.headers = {}
        request.client = None
        
        assert get_client_ip(request) == "unknown"
    
    def test_header_priority(self):
        """Test that X-Forwarded-For takes priority"""
        request = Mock()
        request.headers = {
            "X-Forwarded-For": "1.1.1.1",
            "X-Real-IP": "2.2.2.2",
            "CF-Connecting-IP": "3.3.3.3",
        }
        request.client = Mock()
        request.client.host = "4.4.4.4"
        
        assert get_client_ip(request) == "1.1.1.1"


class TestBuildRateLimitHeaders:
    """Tests for rate limit header generation"""
    
    def test_allowed_headers(self):
        """Test headers for allowed request"""
        result = RateLimitResult(
            allowed=True,
            remaining=5,
            limit=10,
            reset_after=60.0,
            tier="global"
        )
        
        headers = build_rate_limit_headers(result)
        
        assert headers["X-RateLimit-Limit"] == "10"
        assert headers["X-RateLimit-Remaining"] == "5"
        assert "X-RateLimit-Reset" in headers
        assert "Retry-After" not in headers
    
    def test_blocked_headers(self):
        """Test headers for blocked request"""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            limit=10,
            reset_after=30.0,
            retry_after=30.0,
            tier="burst"
        )
        
        headers = build_rate_limit_headers(result)
        
        assert headers["X-RateLimit-Limit"] == "10"
        assert headers["X-RateLimit-Remaining"] == "0"
        assert headers["Retry-After"] == "30"


class TestRateLimitResponseBody:
    """Tests for rate limit error response body"""
    
    def test_response_body_structure(self):
        """Test response body has correct structure"""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            limit=10,
            reset_after=30.0,
            retry_after=30.0,
            tier="burst"
        )
        
        body = rate_limit_response_body(result)
        
        assert "detail" in body
        assert "error" in body
        assert body["error"] == "rate_limit_exceeded"
        assert "retry_after_seconds" in body
        assert body["retry_after_seconds"] == 30
        assert "limit" in body
        assert body["limit"] == 10
        assert "tier" in body
        assert body["tier"] == "burst"


class TestLocalRateLimiter:
    """Tests for local fallback rate limiter"""
    
    def test_first_request_allowed(self):
        """Test that first request is allowed"""
        limiter = LocalRateLimiter()
        allowed, remaining = limiter.check("test_key", max_requests=5, window_seconds=60)
        
        assert allowed is True
        assert remaining == 4
    
    def test_requests_within_limit(self):
        """Test requests within limit are allowed"""
        limiter = LocalRateLimiter()
        
        for i in range(5):
            allowed, remaining = limiter.check("test_key", max_requests=5, window_seconds=60)
            assert allowed is True
            assert remaining == 4 - i
    
    def test_requests_exceed_limit(self):
        """Test requests exceeding limit are blocked"""
        limiter = LocalRateLimiter()
        
        # Use up the limit
        for _ in range(5):
            limiter.check("test_key", max_requests=5, window_seconds=60)
        
        # 6th request should be blocked
        allowed, remaining = limiter.check("test_key", max_requests=5, window_seconds=60)
        assert allowed is False
        assert remaining == 0
    
    def test_different_keys_independent(self):
        """Test that different keys have independent limits"""
        limiter = LocalRateLimiter()
        
        # Use up key1's limit
        for _ in range(5):
            limiter.check("key1", max_requests=5, window_seconds=60)
        
        # key2 should still have its limit
        allowed, remaining = limiter.check("key2", max_requests=5, window_seconds=60)
        assert allowed is True
        assert remaining == 4
    
    def test_window_reset(self):
        """Test that window resets after expiration"""
        limiter = LocalRateLimiter()
        
        # Use up the limit with a very short window
        for _ in range(5):
            limiter.check("test_key", max_requests=5, window_seconds=1)
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        allowed, remaining = limiter.check("test_key", max_requests=5, window_seconds=1)
        assert allowed is True


class TestCheckRateLimitLegacy:
    """Tests for legacy check_rate_limit function"""
    
    @patch('utils.rate_limit.check_rate_limit_atomic')
    def test_returns_tuple(self, mock_atomic):
        """Test that legacy function returns tuple format"""
        mock_atomic.return_value = RateLimitResult(
            allowed=True,
            remaining=5,
            limit=10,
            reset_after=60.0,
            tier="global"
        )
        
        allowed, remaining = check_rate_limit("test_key", max_requests=10, window_seconds=60)
        
        assert allowed is True
        assert remaining == 5
    
    @patch('utils.rate_limit.check_rate_limit_atomic')
    def test_blocked_returns_zero_remaining(self, mock_atomic):
        """Test that blocked requests return 0 remaining"""
        mock_atomic.return_value = RateLimitResult(
            allowed=False,
            remaining=0,
            limit=10,
            reset_after=30.0,
            retry_after=30.0,
            tier="burst"
        )
        
        allowed, remaining = check_rate_limit("test_key", max_requests=10, window_seconds=60)
        
        assert allowed is False
        assert remaining == 0


class TestMultiTierRateLimit:
    """Tests for multi-tier rate limiting"""
    
    @patch('utils.rate_limit.check_rate_limit_atomic')
    def test_whitelisted_ip_bypasses_all(self, mock_atomic):
        """Test that whitelisted IPs bypass all rate limits"""
        result = check_multi_tier_rate_limit("127.0.0.1")
        
        assert result.allowed is True
        assert result.tier == "whitelist"
        mock_atomic.assert_not_called()
    
    @patch('utils.rate_limit.check_rate_limit_atomic')
    def test_burst_checked_first(self, mock_atomic):
        """Test that burst limit is checked before global"""
        # Mock burst to fail
        burst_result = RateLimitResult(
            allowed=False,
            remaining=0,
            limit=10,
            reset_after=1.0,
            retry_after=1.0,
            tier="burst"
        )
        mock_atomic.return_value = burst_result
        
        result = check_multi_tier_rate_limit("8.8.8.8")
        
        assert result.allowed is False
        assert result.tier == "burst"
        # Should only be called once (burst check)
        assert mock_atomic.call_count == 1
    
    @patch('utils.rate_limit.check_rate_limit_atomic')
    def test_global_checked_after_burst(self, mock_atomic):
        """Test that global is checked after burst passes"""
        # First call (burst) passes, second call (global) fails
        burst_result = RateLimitResult(
            allowed=True, remaining=5, limit=10, reset_after=1.0, tier="burst"
        )
        global_result = RateLimitResult(
            allowed=False, remaining=0, limit=30, reset_after=10.0,
            retry_after=10.0, tier="global"
        )
        mock_atomic.side_effect = [burst_result, global_result]
        
        result = check_multi_tier_rate_limit("8.8.8.8")
        
        assert result.allowed is False
        assert result.tier == "global"
        assert mock_atomic.call_count == 2


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

