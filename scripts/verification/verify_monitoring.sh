#!/bin/bash
# Monitoring Stack Verification Script
#
# Usage:
#   ./verify_monitoring.sh              # Full verification
#   ./verify_monitoring.sh mvp          # MVP checks only
#   ./verify_monitoring.sh config       # Config file checks only

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

MODE="${1:-full}"

success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; exit 1; }
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

echo "=========================================="
echo "Monitoring Stack Verification"
echo "=========================================="

# === Config Files Check ===
check_config_files() {
    echo ""
    echo "1️⃣ 检查配置文件..."
    echo "----------------------------"

    local files=(
        "config/monitoring/prometheus.yml"
        "config/monitoring/prometheus_alerts.yml"
        "config/monitoring/grafana_dashboard_task_outputs.json"
    )

    for f in "${files[@]}"; do
        if [ -f "$f" ]; then
            success "$f"
        else
            error "$f 不存在"
        fi
    done

    if [ -f "docker/prometheus/docker-compose.yml" ]; then
        success "docker/prometheus/docker-compose.yml"
    else
        warning "docker/prometheus/docker-compose.yml 不存在（可选）"
    fi
}

# === YAML Syntax Check ===
check_yaml_syntax() {
    echo ""
    echo "2️⃣ 验证 YAML 语法..."
    echo "----------------------------"

    if ! command -v python3 &> /dev/null; then
        warning "python3 未安装，跳过 YAML 验证"
        return
    fi

    for file in config/monitoring/prometheus.yml config/monitoring/prometheus_alerts.yml; do
        if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            success "$file (YAML 语法正确)"
        else
            error "$file (YAML 语法错误)"
        fi
    done
}

# === Dashboard JSON Check ===
check_dashboard_json() {
    echo ""
    echo "3️⃣ 验证 Grafana Dashboard..."
    echo "----------------------------"

    if ! command -v jq &> /dev/null; then
        warning "jq 未安装，跳过 JSON 验证"
        return
    fi

    if jq empty config/monitoring/grafana_dashboard_task_outputs.json 2>/dev/null; then
        success "Dashboard JSON 格式正确"

        local panel_count=$(jq '.dashboard.panels | length' config/monitoring/grafana_dashboard_task_outputs.json)
        info "包含 $panel_count 个监控面板"
    else
        error "Dashboard JSON 格式错误"
    fi
}

# === Prometheus Config Check ===
check_prometheus_config() {
    echo ""
    echo "4️⃣ 验证 Prometheus 配置..."
    echo "----------------------------"

    if grep -q "financeai-backend" config/monitoring/prometheus.yml; then
        success "包含 financeai-backend 抓取配置"
    else
        error "缺少 financeai-backend 抓取配置"
    fi
}

# === Alert Rules Check ===
check_alert_rules() {
    echo ""
    echo "5️⃣ 验证告警规则..."
    echo "----------------------------"

    local alerts=("TaskOutputValidationFailed" "HighGuardrailRetryRate")
    for alert in "${alerts[@]}"; do
        if grep -q "$alert" config/monitoring/prometheus_alerts.yml; then
            success "$alert"
        else
            error "$alert 未找到"
        fi
    done
}

# === MVP Specific Checks ===
check_mvp_metrics() {
    echo ""
    echo "6️⃣ 验证 Metrics 代码..."
    echo "----------------------------"

    local metrics=("task_output_total" "task_output_validation_passed_total" "task_output_with_citations_total" "task_output_degraded_total" "guardrail_retry_count")

    for metric in "${metrics[@]}"; do
        if grep -q "$metric" AICrews/infrastructure/metrics/task_output_metrics.py 2>/dev/null; then
            success "$metric"
        else
            warning "$metric 未找到"
        fi
    done
}

# === Main Logic ===
case "$MODE" in
    mvp)
        check_config_files
        check_yaml_syntax
        check_dashboard_json
        check_mvp_metrics
        ;;
    config)
        check_config_files
        check_yaml_syntax
        ;;
    full|*)
        check_config_files
        check_yaml_syntax
        check_dashboard_json
        check_prometheus_config
        check_alert_rules
        check_mvp_metrics
        ;;
esac

# Summary
echo ""
echo "=========================================="
success "验证完成 - 监控栈配置正确"
echo "=========================================="
echo ""
echo "📝 下一步:"
echo "   启动: cd docker/prometheus && docker compose up -d"
echo "   访问: http://localhost:33000 (Grafana)"
echo ""
