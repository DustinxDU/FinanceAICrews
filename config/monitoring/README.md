# Task Structured Outputs - 监控部署指南

本目录包含 Task Structured Outputs 功能的 Grafana dashboard 和 Prometheus 告警配置。

## 📁 文件清单

| 文件 | 说明 |
|-----|------|
| `grafana_dashboard_task_outputs.json` | Grafana dashboard 配置（4个核心指标） |
| `prometheus_alerts.yml` | Prometheus 告警规则（2个关键告警） |
| `prometheus.yml` | Prometheus 抓取配置 |
| `../infrastructure/metrics/task_output_metrics.py` | Prometheus metrics 埋点代码 |

## 🐳 Docker 部署（推荐）

### 快速启动

```bash
# 1. 启动 Prometheus + Grafana
cd docker/prometheus
docker-compose up -d

# 2. 验证服务
curl http://localhost:9090/api/v1/status/config  # Prometheus
curl http://localhost:33000/api/health           # Grafana

# 3. 访问 Grafana
# URL: http://localhost:33000
# 默认登录: admin/admin
```

### Docker 配置结构

```
docker/prometheus/
├── docker-compose.yml              # Prometheus + Grafana 服务
├── prometheus.yml                  # Prometheus 抓取配置
├── prometheus_alerts.yml           # 告警规则
└── grafana/
    └── provisioning/
        ├── datasources/
        │   └── prometheus.yml      # Grafana 数据源（自动配置）
        └── dashboards/
            ├── dashboards.yml      # Dashboard 自动导入配置
            └── grafana_dashboard_task_outputs.json  # Task Output Dashboard
```

### 环境变量（可选）

```bash
# 在 .env 或 docker-compose.override.yml 中配置
PROMETHEUS_PORT=9090       # Prometheus 端口（默认 9090）
GRAFANA_PORT=33000         # Grafana 端口（默认 33000，避免与前端冲突）
GRAFANA_ADMIN_USER=admin   # Grafana 管理员用户名
GRAFANA_ADMIN_PASSWORD=admin  # Grafana 管理员密码
```

## 🎯 监控指标

### 4个核心指标

| 指标 | 说明 | 目标值 | 告警阈值 |
|-----|------|--------|---------|
| **Validation Passed Rate** | 验证通过率 | >95% | <90% |
| **Average Guardrail Retries** | 平均重试次数 | <1.5 | >2.0 |
| **Citation Coverage** | 引用覆盖率 | >80% | <60% |
| **Degradation Rate** | 降级率 | <20% | >40% |

### 2个关键告警

| 告警名称 | 触发条件 | 持续时间 | 严重级别 |
|---------|---------|---------|---------|
| **TaskOutputValidationFailed** | 验证通过率 < 90% | 10分钟 | warning |
| **HighGuardrailRetryRate** | P90重试次数 > 2.0 | 15分钟 | info |

## 🚀 部署步骤

### Step 1: 安装依赖

```bash
# 安装 prometheus-client
pip install prometheus-client

# 或添加到 requirements.txt
echo "prometheus-client==0.19.0" >> requirements.txt
```

### Step 2: 暴露 Prometheus metrics 端点

编辑 `backend/app/main.py`:

```python
from prometheus_client import make_asgi_app

app = FastAPI(...)

# 挂载 Prometheus metrics 端点
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

重启后端:
```bash
python -m backend.app.main
```

验证 metrics 端点:
```bash
curl http://localhost:8000/metrics
# 应看到 Prometheus 格式的 metrics
```

### Step 3: 集成 metrics 到 TrackingService

编辑 `AICrews/services/tracking_service.py`:

```python
from AICrews.infrastructure.metrics.task_output_metrics import record_task_output_event

class TrackingService:
    def add_task_output_event(
        self,
        job_id: str,
        agent_name: str,
        task_id: str,
        payload: Dict[str, Any],
        severity: str = "info",
    ) -> None:
        # ... 现有代码（redaction等）...

        # 🆕 记录 Prometheus metrics
        try:
            record_task_output_event(
                crew_id=job_id,
                task_id=task_id,
                agent_name=agent_name,
                payload=payload
            )
        except Exception as e:
            logger.warning(f"Failed to record task output metrics: {e}")

        # ... 其余代码 ...
```

### Step 4: 配置 Prometheus 抓取

编辑 Prometheus 配置文件 (`prometheus.yml`):

```yaml
scrape_configs:
  - job_name: 'financeaicrews'
    scrape_interval: 15s
    static_configs:
      - targets: ['backend:8000']  # 或 localhost:8000
    metrics_path: '/metrics'
```

重新加载 Prometheus 配置:
```bash
# 如果使用 Docker
docker exec prometheus kill -HUP 1

# 或通过 API
curl -X POST http://localhost:9090/-/reload
```

### Step 5: 导入 Grafana Dashboard

**方式 1: 通过 UI 导入**

1. 打开 Grafana: http://localhost:3000
2. 点击左侧菜单 `Dashboards` → `Import`
3. 上传 `grafana_dashboard_task_outputs.json` 文件
4. 选择 Prometheus 数据源
5. 点击 `Import`

**方式 2: 通过 API 导入**

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d @config/monitoring/grafana_dashboard_task_outputs.json \
  http://localhost:3000/api/dashboards/db
```

### Step 6: 配置 Prometheus 告警规则

**方式 1: 直接编辑 Prometheus 配置**

将 `prometheus_alerts.yml` 内容添加到 Prometheus 的 `rules` 目录:

```bash
cp config/monitoring/prometheus_alerts.yml /etc/prometheus/rules/task_outputs.yml
```

在 `prometheus.yml` 中引用:
```yaml
rule_files:
  - "/etc/prometheus/rules/*.yml"
```

**方式 2: Docker Compose 挂载**

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./config/monitoring/prometheus_alerts.yml:/etc/prometheus/rules/task_outputs.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
```

重新加载 Prometheus:
```bash
curl -X POST http://localhost:9090/-/reload
```

验证告警规则:
```bash
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name=="task_output_quality")'
```

## ✅ 验证部署

### 1. 验证 Metrics 采集

```bash
# 查询 task_output_total
curl 'http://localhost:9090/api/v1/query?query=task_output_total' | jq

# 查询 validation_passed_rate
curl 'http://localhost:9090/api/v1/query?query=sum(rate(task_output_validation_passed_total[5m]))/sum(rate(task_output_total[5m]))' | jq
```

### 2. 验证 Grafana Dashboard

访问: http://localhost:3000/d/task-outputs/task-structured-outputs

应看到 4 个指标面板：
- ✅ Validation Passed Rate (%)
- ✅ Average Guardrail Retries
- ✅ Citation Coverage (%)
- ✅ Degradation Rate (%)

### 3. 验证告警规则

```bash
# 查看告警状态
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.component=="task_outputs")'
```

### 4. 触发测试告警

运行试点 Crew 并观测 metrics:

```bash
# 运行 Hello World Joke Crew
curl -X POST http://localhost:8000/api/v1/crews/9/run \
  -H "Content-Type: application/json" \
  -d '{"variables": {"topic": "AI"}}'

# 查看 task_output 事件
curl http://localhost:8000/api/v1/jobs/{job_id}/status | jq '.task_outputs'
```

## 📊 Dashboard 截图示例

```
┌────────────────────────────────────────────────────────────┐
│  Task Structured Outputs - Monitoring Dashboard           │
├────────────┬────────────┬────────────┬────────────────────┤
│ Validation │  Guardrail │  Citation  │    Degradation     │
│   Passed   │  Retries   │  Coverage  │       Rate         │
│            │            │            │                    │
│   96.5%    │    1.2     │   82.3%    │      15.4%         │
│    🟢      │    🟢      │    🟢      │       🟢           │
└────────────┴────────────┴────────────┴────────────────────┘
│                                                            │
│  Task Output Events Timeline                               │
│  ▁▂▃▅▇█▇▅▃▂▁  (1分钟内的事件速率)                         │
│                                                            │
│  Guardrail Retry Distribution                              │
│  P50: 1.0  P90: 2.3  P99: 4.1                             │
└────────────────────────────────────────────────────────────┘
```

## 🔍 故障排查

### Metrics 未采集

1. 检查 `/metrics` 端点是否可访问
2. 检查 Prometheus 的 `targets` 页面状态
3. 检查 TrackingService 是否正确调用 `record_task_output_event()`

### Dashboard 无数据

1. 验证 Prometheus 数据源配置正确
2. 检查时间范围（默认 1小时）
3. 确认 metrics 名称拼写正确

### 告警未触发

1. 检查告警规则是否加载: `http://localhost:9090/rules`
2. 验证查询表达式: 在 Prometheus UI 测试 PromQL
3. 检查 `for` 持续时间是否满足

## 📚 参考资料

- Prometheus 文档: https://prometheus.io/docs/
- Grafana 文档: https://grafana.com/docs/
- Prometheus Client (Python): https://github.com/prometheus/client_python

---

**Last Updated**: 2026-01-02
**Maintainer**: FinanceAICrews Monitoring Team
