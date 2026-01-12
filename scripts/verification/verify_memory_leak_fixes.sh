#!/bin/bash
# Memory Leak Fix Verification Runbook
#
# This script helps verify that the memory leak remediation measures are working correctly.
# It checks for orphan processes, bounded cache sizes, and provides Prometheus query examples.

set -e

COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_RED='\033[0;31m'
COLOR_RESET='\033[0m'

echo "======================================"
echo "Memory Leak Fix Verification Runbook"
echo "======================================"
echo

# Check 1: Orphan Process Detection
echo -e "${COLOR_YELLOW}[1/8] Checking for orphan Python processes...${COLOR_RESET}"
echo "Expected: 0 orphan processes with PPID=1"
echo

# Use ps -eo to correctly get PPID (ps aux column 3 is %CPU, not PPID)
orphans=$(ps -eo pid,ppid,stat,rss,cmd | grep python | grep -v grep | awk '$2 == 1 {print $0}' | wc -l)
if [ "$orphans" -eq 0 ]; then
    echo -e "${COLOR_GREEN}✓ PASS: No orphan processes found${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ FAIL: Found $orphans orphan process(es):${COLOR_RESET}"
    echo "  PID   PPID STAT   RSS CMD"
    ps -eo pid,ppid,stat,rss,cmd | grep python | grep -v grep | awk '$2 == 1 {print "  " $0}'
fi
echo

# Check 2: Process Tree Verification
echo -e "${COLOR_YELLOW}[2/8] Checking uvicorn process tree...${COLOR_RESET}"
echo "Expected: uvicorn parent with child processes, no PPID=1 children"
echo

pgrep -af "uvicorn.*backend\.app\.main:app" > /dev/null && {
    echo "Uvicorn processes found:"
    pgrep -af "uvicorn.*backend\.app\.main:app" | while read pid rest; do
        ppid=$(ps -o ppid= -p $pid | tr -d ' ')
        echo "  PID=$pid PPID=$ppid $rest"
    done
    echo -e "${COLOR_GREEN}✓ INFO: Run 'pstree' to verify tree structure${COLOR_RESET}"
} || {
    echo -e "${COLOR_YELLOW}⚠ INFO: No uvicorn processes running (app may be stopped)${COLOR_RESET}"
}
echo

# Check 3: Configuration Verification
echo -e "${COLOR_YELLOW}[3/8] Checking environment configuration...${COLOR_RESET}"
echo "Verifying bounded cache limits are set:"
echo

check_env_var() {
    var_name=$1
    default_val=$2
    current_val=${!var_name:-$default_val}
    echo "  $var_name=${current_val}"
}

check_env_var "FAIC_RSS_CACHE_MAX_ENTRIES" "1000"
check_env_var "FAIC_NEWS_CACHE_MAX_ENTRIES" "2000"
check_env_var "FAIC_MODEL_CACHE_MAX_ENTRIES" "200"
check_env_var "FAIC_JOB_MAX_IN_MEMORY" "200"
check_env_var "FAIC_JOB_RETENTION_HOURS" "24"
check_env_var "FAIC_JOB_DROP_RESULT_FROM_MEMORY" "true"
check_env_var "FAIC_TRACKING_MAX_RUNS" "1000"
check_env_var "FAIC_TRACKING_RETENTION_HOURS" "24"
check_env_var "FAIC_TRACKING_MAX_EVENTS_PER_RUN" "5000"
check_env_var "FAIC_WS_RUN_LOG_MAX_RUNS" "100"
check_env_var "FAIC_WS_RUN_LOG_MAX_EVENTS_PER_RUN" "1000"

echo -e "${COLOR_GREEN}✓ INFO: Configuration loaded (defaults shown if not set)${COLOR_RESET}"
echo

# Check 4: Memory Baseline Measurement
echo -e "${COLOR_YELLOW}[4/8] Measuring current memory usage...${COLOR_RESET}"
echo "Expected: Stable memory usage (not growing unbounded)"
echo

if pgrep -f "uvicorn.*backend\.app\.main:app" > /dev/null; then
    for pid in $(pgrep -f "uvicorn.*backend\.app\.main:app"); do
        mem_kb=$(ps -o rss= -p $pid | awk '{print $1}')
        mem_mb=$((mem_kb / 1024))
        echo "  Process PID=$pid: ${mem_mb} MB"
    done
    echo -e "${COLOR_GREEN}✓ INFO: Record these values and compare after load testing${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}⚠ INFO: App not running, cannot measure memory${COLOR_RESET}"
fi
echo

# Check 5: Prometheus Metrics Verification
echo -e "${COLOR_YELLOW}[5/8] Prometheus metrics verification...${COLOR_RESET}"
echo "Expected: Metrics endpoint is accessible and returns memory management metrics"
echo

if curl -s http://localhost:8000/metrics > /dev/null 2>&1; then
    echo "Available memory management metrics:"
    echo
    curl -s http://localhost:8000/metrics | grep -E "(job_manager_|tracking_service_|cache_size|websocket_)" | head -20
    echo
    echo -e "${COLOR_GREEN}✓ PASS: Metrics endpoint accessible${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}⚠ INFO: Metrics endpoint not accessible (app may be stopped or metrics disabled)${COLOR_RESET}"
fi
echo

# Check 6: MCP Session Leak Verification
echo -e "${COLOR_YELLOW}[6/8] MCP session leak verification...${COLOR_RESET}"
echo "Expected: MCP clients should not accumulate sessions over time"
echo

if pgrep -f "uvicorn.*backend\.app\.main:app" > /dev/null; then
    # Get current FD count for uvicorn process
    for pid in $(pgrep -f "uvicorn.*backend\.app\.main:app"); do
        fd_count=$(ls /proc/$pid/fd 2>/dev/null | wc -l)
        echo "  Process PID=$pid: $fd_count file descriptors"
    done
    echo
    echo -e "${COLOR_GREEN}✓ INFO: Record FD counts before and after load testing${COLOR_RESET}"
    echo "        If FD count grows linearly with requests → session leak"
    echo "        Expected: FD count stays stable (±20) after warmup"
else
    echo -e "${COLOR_YELLOW}⚠ INFO: App not running, cannot check FD counts${COLOR_RESET}"
fi
echo

# Check 7: MCP Session Stats via API (if available)
echo -e "${COLOR_YELLOW}[7/8] MCP client stats (if available)...${COLOR_RESET}"
echo

# Try to get MCP client stats via a simple Python script
python3 << 'PYEOF' 2>/dev/null || echo "  (MCP stats not available - app may be stopped)"
import sys
sys.path.insert(0, '.')
try:
    from AICrews.infrastructure.mcp import get_mcp_client
    akshare = get_mcp_client("akshare")
    stats = akshare.get_stats()
    print(f"  Akshare MCP Client:")
    print(f"    Primary loop ID: {stats.get('primary_loop_id', 'N/A')}")
    print(f"    Primary session active: {stats.get('primary_session_active', 'N/A')}")
    print(f"    Ephemeral sessions created: {stats.get('ephemeral_sessions_created', 0)}")
    print()
    print("  ✓ INFO: ephemeral_sessions_created should stay LOW")
    print("          If it grows rapidly → consider increasing session reuse")
except Exception as e:
    print(f"  Could not get MCP stats: {e}")
PYEOF
echo

# Check 8: Prometheus Query Examples
echo -e "${COLOR_YELLOW}[8/8] Prometheus query examples for monitoring...${COLOR_RESET}"
echo
cat << 'EOF'
Use these PromQL queries in Grafana or Prometheus UI:

1. JobManager memory usage:
   job_manager_jobs_in_memory

2. TrackingService memory usage:
   tracking_service_runs_in_memory

3. Cache sizes by type:
   cache_size{cache_name="smart_rss"}
   cache_size{cache_name="news_service"}
   cache_size{cache_name="model_service"}

4. WebSocket active connections:
   websocket_active_connections

5. WebSocket run history size:
   websocket_active_runs

6. Memory growth rate (jobs per hour):
   rate(job_manager_jobs_in_memory[1h])

Expected baseline (steady state):
- job_manager_jobs_in_memory: < 200
- tracking_service_runs_in_memory: < 1000
- cache_size{cache_name="smart_rss"}: < 1000
- cache_size{cache_name="news_service"}: < 2000
- cache_size{cache_name="model_service"}: < 200
- websocket_active_runs: < 100

Alert thresholds:
- If any gauge stays at max limit for >1h → LRU eviction working but load is high
- If memory keeps growing despite bounded gauges → new leak source (investigate)
EOF

echo
echo "======================================"
echo "Verification Complete"
echo "======================================"
echo
echo "Next steps:"
echo "  1. Run this script before and after load testing"
echo "  2. Monitor Prometheus metrics over 24h period"
echo "  3. Check that orphan process count stays at 0"
echo "  4. Verify memory usage stabilizes (not growing linearly)"
echo
echo "For continuous monitoring, set up Prometheus alerts:"
echo "  - Alert if orphan_processes > 0"
echo "  - Alert if memory growth rate > 100MB/hour"
echo "  - Alert if any cache_size gauge is stuck at max for >2 hours"
