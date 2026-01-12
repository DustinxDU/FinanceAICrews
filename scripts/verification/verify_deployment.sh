#!/bin/bash
# =============================================================================
# FinanceAI Crews - End-to-End Deployment Verification Script
# =============================================================================
# Run this after `docker compose up -d` to verify all services are operational.
# Usage: ./scripts/verify_deployment.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_pass() {
    echo -e "  ${GREEN}✓ PASS${NC}: $1"
    ((PASS++))
}

check_fail() {
    echo -e "  ${RED}✗ FAIL${NC}: $1"
    ((FAIL++))
}

check_warn() {
    echo -e "  ${YELLOW}⚠ WARN${NC}: $1"
}

# =============================================================================
# STEP 1: Docker Container Health Check
# =============================================================================
print_header "STEP 1: Docker Container Health Status"

REQUIRED_CONTAINERS=("financeai_backend" "financeai_redis" "financeai_db" "akshare_mcp" "yfinance_mcp" "openbb_mcp" "financeai_frontend" "financeai_gateway")

for container in "${REQUIRED_CONTAINERS[@]}"; do
    status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "not_found")
    health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' "$container" 2>/dev/null || echo "unknown")
    
    if [ "$status" == "running" ]; then
        if [ "$health" == "healthy" ] || [ "$health" == "no_healthcheck" ]; then
            check_pass "$container is running (health: $health)"
        else
            check_warn "$container is running but health is: $health"
        fi
    else
        check_fail "$container status: $status"
    fi
done

# =============================================================================
# STEP 2: Redis Connectivity (from Backend container)
# =============================================================================
print_header "STEP 2: Redis Connectivity Test"

# Test Redis PING from inside backend container
redis_ping=$(docker exec financeai_backend python -c "
import redis
import os
host = os.getenv('REDIS_HOST', 'redis')
port = int(os.getenv('REDIS_PORT', 6379))
try:
    r = redis.Redis(host=host, port=port, socket_timeout=5)
    print(r.ping())
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1)

if [ "$redis_ping" == "True" ]; then
    check_pass "Backend can PING Redis at redis:6379"
else
    check_fail "Backend cannot reach Redis: $redis_ping"
fi

# Test Redis SET/GET
redis_setget=$(docker exec financeai_backend python -c "
import redis
import os
host = os.getenv('REDIS_HOST', 'redis')
port = int(os.getenv('REDIS_PORT', 6379))
try:
    r = redis.Redis(host=host, port=port, socket_timeout=5)
    r.set('_verify_test', 'ok', ex=10)
    val = r.get('_verify_test')
    print(val.decode() if val else 'NONE')
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1)

if [ "$redis_setget" == "ok" ]; then
    check_pass "Redis SET/GET working correctly"
else
    check_fail "Redis SET/GET failed: $redis_setget"
fi

# =============================================================================
# STEP 3: MCP Server DNS Resolution & Connectivity
# =============================================================================
print_header "STEP 3: MCP Server Connectivity Tests"

# Test Akshare MCP
akshare_test=$(docker exec financeai_backend python -c "
import httpx
import os
url = os.getenv('AKSHARE_MCP_URL', 'http://akshare_mcp:8009/sse').rstrip('/').removesuffix('/sse').removesuffix('/mcp')
try:
    r = httpx.get(f'{url}/health', timeout=10)
    print(f'HTTP {r.status_code}')
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1)

if [[ "$akshare_test" == *"200"* ]]; then
    check_pass "Akshare MCP reachable at akshare_mcp:8009 ($akshare_test)"
else
    check_fail "Akshare MCP unreachable: $akshare_test"
fi

# Test YFinance MCP
yfinance_test=$(docker exec financeai_backend python -c "
import httpx
import os
url = os.getenv('YFINANCE_MCP_URL', 'http://yfinance_mcp:8010/sse').rstrip('/').removesuffix('/sse').removesuffix('/mcp')
try:
    r = httpx.get(f'{url}/health', timeout=10)
    print(f'HTTP {r.status_code}')
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1)

if [[ "$yfinance_test" == *"200"* ]]; then
    check_pass "YFinance MCP reachable at yfinance_mcp:8010 ($yfinance_test)"
else
    check_fail "YFinance MCP unreachable: $yfinance_test"
fi

# Test OpenBB MCP
openbb_test=$(docker exec financeai_backend python -c "
import httpx
import os
url = os.getenv('OPENBB_MCP_URL', 'http://openbb_mcp:8001/mcp').rstrip('/').removesuffix('/mcp')
try:
    r = httpx.get(f'{url}/mcp/', timeout=15)
    print(f'HTTP {r.status_code}')
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1)

if [[ "$openbb_test" == *"200"* ]] || [[ "$openbb_test" == *"405"* ]]; then
    check_pass "OpenBB MCP reachable at openbb_mcp:8001 ($openbb_test)"
else
    check_warn "OpenBB MCP may have issues: $openbb_test (this is optional)"
fi

# =============================================================================
# STEP 4: Backend API Health Check
# =============================================================================
print_header "STEP 4: Backend FastAPI Health Check"

# Verify AICrews imports
import_check=$(docker exec financeai_backend python -c "
try:
    import AICrews
    import AICrews.core.registry
    import AICrews.runner
    print('IMPORT_OK')
except Exception as e:
    print(f'IMPORT_FAIL: {e}')
" 2>&1)

if [ "$import_check" == "IMPORT_OK" ]; then
    check_pass "AICrews core modules importable"
else
    check_fail "AICrews import failed: $import_check"
fi

# Direct backend health check (internal)
backend_health=$(docker exec financeai_backend curl -sf http://localhost:8000/health 2>&1 || echo "FAILED")

if [[ "$backend_health" == *"ok"* ]] || [[ "$backend_health" == *"healthy"* ]] || [[ "$backend_health" == *"status"* ]]; then
    check_pass "Backend /health endpoint responding"
else
    check_fail "Backend /health failed: $backend_health"
fi

# =============================================================================
# STEP 5: Frontend-to-Backend via Gateway
# =============================================================================
print_header "STEP 5: Gateway Proxy Test (Frontend -> Backend)"

# Test via gateway (simulates browser request)
gateway_port="${GATEWAY_PORT:-8081}"
gateway_api=$(curl -sf "http://localhost:${gateway_port}/api/health" 2>&1 || echo "FAILED")

if [[ "$gateway_api" == *"ok"* ]] || [[ "$gateway_api" == *"healthy"* ]] || [[ "$gateway_api" == *"status"* ]]; then
    check_pass "Gateway proxying /api/health to backend correctly"
else
    check_warn "Gateway /api/health: $gateway_api (may need nginx config check)"
fi

# Test frontend static serving
frontend_test=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:${gateway_port}/" 2>&1 || echo "000")

if [ "$frontend_test" == "200" ]; then
    check_pass "Frontend serving via gateway at :${gateway_port}/"
else
    check_warn "Frontend via gateway returned HTTP $frontend_test"
fi

# =============================================================================
# STEP 6: Database Connectivity
# =============================================================================
print_header "STEP 6: PostgreSQL Database Connectivity"

db_test=$(docker exec financeai_backend python -c "
from sqlalchemy import create_engine, text
import os
url = os.getenv('DATABASE_URL', '')
try:
    engine = create_engine(url)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('OK')
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1)

if [ "$db_test" == "OK" ]; then
    check_pass "Backend can connect to PostgreSQL database"
else
    check_fail "Database connection failed: $db_test"
fi

# =============================================================================
# SUMMARY
# =============================================================================
print_header "VERIFICATION SUMMARY"

TOTAL=$((PASS + FAIL))
echo ""
echo -e "  ${GREEN}Passed${NC}: $PASS / $TOTAL"
echo -e "  ${RED}Failed${NC}: $FAIL / $TOTAL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL CHECKS PASSED! System is operational.${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some checks failed. Review the output above.${NC}"
    exit 1
fi
