"""
Prometheus Metrics for Task Structured Outputs

在 TrackingService 中集成这些 metrics 来采集关键指标：
- task_output_total: 任务输出总数
- task_output_validation_passed_total: 验证通过的输出数
- task_output_with_citations_total: 包含引用的输出数
- task_output_degraded_total: 降级的输出数
- guardrail_retry_count: Guardrail 重试次数直方图

使用方式:
1. 安装依赖: pip install prometheus-client
2. 在 backend/app/main.py 中暴露 /metrics 端点
3. 在 TrackingService.add_task_output_event() 中调用这些 metrics
"""

from prometheus_client import Counter, Histogram, Gauge

# Counter: 任务输出总数
task_output_total = Counter(
    'task_output_total',
    'Total number of task outputs',
    ['crew_id', 'task_id', 'agent_name', 'output_mode']
)

# Counter: 验证通过的输出数
task_output_validation_passed_total = Counter(
    'task_output_validation_passed_total',
    'Number of task outputs that passed validation',
    ['crew_id', 'task_id', 'output_mode']
)

# Counter: 包含引用的输出数
task_output_with_citations_total = Counter(
    'task_output_with_citations_total',
    'Number of task outputs containing citations',
    ['crew_id', 'task_id']
)

# Counter: 降级的输出数
task_output_degraded_total = Counter(
    'task_output_degraded_total',
    'Number of task outputs that degraded from native to soft mode',
    ['crew_id', 'task_id', 'degraded_from']
)

# Histogram: Guardrail 重试次数
guardrail_retry_count = Histogram(
    'guardrail_retry_count',
    'Distribution of guardrail retry counts',
    ['crew_id', 'task_id'],
    buckets=[0, 1, 2, 3, 5, 10]  # 重试次数分桶
)

# Gauge: 当前活跃的任务数
active_tasks_gauge = Gauge(
    'active_tasks',
    'Number of currently executing tasks',
    ['crew_id']
)


def record_task_output_event(
    crew_id: str,
    task_id: str,
    agent_name: str,
    payload: dict
) -> None:
    """
    记录 TASK_OUTPUT 事件的 metrics

    在 TrackingService.add_task_output_event() 中调用此函数

    Args:
        crew_id: Crew ID
        task_id: Task ID
        agent_name: Agent 名称
        payload: TASK_OUTPUT 事件的 payload
    """
    summary = payload.get("summary", {})
    diagnostics = payload.get("diagnostics", {})

    output_mode = diagnostics.get("output_mode", "unknown")
    validation_passed = summary.get("validation_passed", True)
    citation_count = diagnostics.get("citation_count", 0)
    degraded_from = diagnostics.get("degraded_from")
    retry_count = diagnostics.get("guardrail_retries", 0)

    # 记录总数
    task_output_total.labels(
        crew_id=crew_id,
        task_id=task_id,
        agent_name=agent_name,
        output_mode=output_mode
    ).inc()

    # 记录验证通过
    if validation_passed:
        task_output_validation_passed_total.labels(
            crew_id=crew_id,
            task_id=task_id,
            output_mode=output_mode
        ).inc()

    # 记录包含引用
    if citation_count > 0:
        task_output_with_citations_total.labels(
            crew_id=crew_id,
            task_id=task_id
        ).inc()

    # 记录降级
    if degraded_from:
        task_output_degraded_total.labels(
            crew_id=crew_id,
            task_id=task_id,
            degraded_from=degraded_from
        ).inc()

    # 记录重试次数
    guardrail_retry_count.labels(
        crew_id=crew_id,
        task_id=task_id
    ).observe(retry_count)


# 示例集成代码（供参考）
"""
# 在 AICrews/services/tracking_service.py 中:

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
        # ... 现有代码 ...

        # 🆕 记录 Prometheus metrics
        try:
            from AICrews.infrastructure.metrics.task_output_metrics import record_task_output_event
            record_task_output_event(
                crew_id=job_id,  # 或者从 payload 中提取真实的 crew_id
                task_id=task_id,
                agent_name=agent_name,
                payload=payload
            )
        except Exception as e:
            logger.warning(f"Failed to record task output metrics: {e}")

        # ... 其余代码 ...
"""


# 在 backend/app/main.py 中暴露 /metrics 端点
"""
from prometheus_client import make_asgi_app

app = FastAPI(...)

# 挂载 Prometheus metrics 端点
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
"""
