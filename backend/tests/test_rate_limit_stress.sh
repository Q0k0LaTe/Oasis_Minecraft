#!/bin/bash
# =============================================================================
# Rate Limit Stress Test Script
# =============================================================================
# Tests the IP rate limiting middleware by sending rapid requests
#
# Usage:
#   chmod +x test_rate_limit_stress.sh
#   ./test_rate_limit_stress.sh [URL] [REQUESTS] [CONCURRENCY]
#
# Examples:
#   ./test_rate_limit_stress.sh                           # Default: health endpoint, 50 requests
#   ./test_rate_limit_stress.sh http://localhost:3000     # Custom base URL
#   ./test_rate_limit_stress.sh http://localhost:3000 100 # 100 requests
#   ./test_rate_limit_stress.sh http://localhost:3000 100 20  # 100 requests, 20 concurrent
# =============================================================================

set -e

# Configuration
BASE_URL="${1:-http://localhost:3000}"
TOTAL_REQUESTS="${2:-50}"
CONCURRENCY="${3:-10}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "Rate Limit Stress Test"
echo "=============================================="
echo "Base URL: $BASE_URL"
echo "Total Requests: $TOTAL_REQUESTS"
echo "Concurrency: $CONCURRENCY"
echo "=============================================="

# Test 1: Health endpoint (should be excluded from rate limiting)
echo ""
echo -e "${YELLOW}Test 1: Health endpoint (excluded from rate limiting)${NC}"
echo "Endpoint: GET /api/health"
echo "Expected: All requests should succeed (200)"
echo "----------------------------------------------"

success_count=0
fail_count=0
rate_limited=0

for i in $(seq 1 20); do
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/health")
    status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" = "200" ]; then
        ((success_count++))
    elif [ "$status_code" = "429" ]; then
        ((rate_limited++))
    else
        ((fail_count++))
    fi
done

echo "Success (200): $success_count"
echo "Rate Limited (429): $rate_limited"
echo "Other Errors: $fail_count"

if [ "$rate_limited" -eq 0 ]; then
    echo -e "${GREEN}✓ PASS: Health endpoint not rate limited${NC}"
else
    echo -e "${RED}✗ FAIL: Health endpoint was rate limited!${NC}"
fi

# Test 2: Burst limit test (rapid sequential requests)
echo ""
echo -e "${YELLOW}Test 2: Burst limit test (10 req/1s limit)${NC}"
echo "Endpoint: GET /"
echo "Expected: First ~10 requests succeed, rest get 429"
echo "----------------------------------------------"

success_count=0
rate_limited=0

# Send 20 requests as fast as possible (no delay)
for i in $(seq 1 20); do
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/")
    status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" = "200" ]; then
        ((success_count++))
    elif [ "$status_code" = "429" ]; then
        ((rate_limited++))
        # Show first 429 response
        if [ "$rate_limited" -eq 1 ]; then
            echo ""
            echo "First 429 response body:"
            curl -s "$BASE_URL/" | head -c 200
            echo ""
            echo ""
        fi
    fi
done

echo "Success (200): $success_count"
echo "Rate Limited (429): $rate_limited"

if [ "$rate_limited" -gt 0 ]; then
    echo -e "${GREEN}✓ PASS: Burst rate limiting is working${NC}"
else
    echo -e "${RED}✗ FAIL: Burst rate limiting NOT triggered (expected 429 after ~10 requests)${NC}"
fi

# Test 3: Global limit test (sustained requests)
echo ""
echo -e "${YELLOW}Test 3: Global limit test (30 req/10s limit)${NC}"
echo "Endpoint: GET /"
echo "Expected: After ~30 requests total, start getting 429"
echo "----------------------------------------------"

# Wait for burst window to reset (but global window should still be counting)
sleep 2

success_count=0
rate_limited=0

for i in $(seq 1 $TOTAL_REQUESTS); do
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/")
    status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" = "200" ]; then
        ((success_count++))
    elif [ "$status_code" = "429" ]; then
        ((rate_limited++))
        # Show rate limit response headers on first 429
        if [ "$rate_limited" -eq 1 ]; then
            echo ""
            echo "First 429 response headers:"
            curl -sI "$BASE_URL/" | grep -i "x-ratelimit\|retry-after" || echo "(headers not shown for non-GET)"
            echo ""
        fi
    fi
    # Small delay to avoid burst limit but still hit global limit
    sleep 0.1
done

echo "Success (200): $success_count"
echo "Rate Limited (429): $rate_limited"

if [ "$rate_limited" -gt 0 ]; then
    echo -e "${GREEN}✓ PASS: Global rate limiting is working${NC}"
else
    echo -e "${RED}✗ FAIL: Global rate limiting NOT triggered${NC}"
fi

# Test 4: Auth endpoint rate limit (stricter)
echo ""
echo -e "${YELLOW}Test 4: Auth endpoint rate limit (10 req/60s)${NC}"
echo "Endpoint: POST /api/auth/login"
echo "Expected: After 10 requests, get 429"
echo "----------------------------------------------"

# Wait for burst window to reset
sleep 2

success_count=0
rate_limited=0
auth_errors=0

for i in $(seq 1 15); do
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@test.com","password":"wrong"}')
    status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" = "401" ] || [ "$status_code" = "400" ]; then
        ((success_count++))  # Auth failed is expected, but not rate limited
    elif [ "$status_code" = "429" ]; then
        ((rate_limited++))
    else
        ((auth_errors++))
    fi
done

echo "Auth Errors (expected): $success_count"
echo "Rate Limited (429): $rate_limited"
echo "Other Errors: $auth_errors"

if [ "$rate_limited" -gt 0 ]; then
    echo -e "${GREEN}✓ PASS: Auth endpoint rate limiting is working${NC}"
else
    echo -e "${YELLOW}⚠ INFO: Auth rate limiting not triggered (may need more requests)${NC}"
fi

# Test 5: Check rate limit headers
echo ""
echo -e "${YELLOW}Test 5: Rate limit headers${NC}"
echo "Checking X-RateLimit-* headers in response"
echo "----------------------------------------------"

# Wait for windows to reset
sleep 2

headers=$(curl -sI "$BASE_URL/")
echo "Response headers:"
echo "$headers" | grep -i "x-ratelimit" || echo "(No rate limit headers found)"

if echo "$headers" | grep -qi "x-ratelimit-limit"; then
    echo -e "${GREEN}✓ PASS: Rate limit headers present${NC}"
else
    echo -e "${YELLOW}⚠ INFO: Rate limit headers not found${NC}"
fi

# Summary
echo ""
echo "=============================================="
echo "Test Complete"
echo "=============================================="
echo ""
echo "Rate Limit Configuration:"
echo "  - Global: 30 requests per 10 seconds"
echo "  - Burst: 10 requests per 1 second"
echo "  - Auth endpoints: 10 requests per 60 seconds"
echo "  - Verification code: 3 requests per 60 seconds"
echo "  - Build/AI: 5 requests per 60 seconds"
echo ""
echo "Excluded paths:"
echo "  - /docs, /redoc, /openapi.json"
echo "  - /api/health"
echo ""
echo "Whitelisted IPs: (none by default, set RATE_LIMIT_WHITELIST_IPS)"
echo ""
