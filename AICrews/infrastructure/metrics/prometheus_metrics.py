"""
Prometheus metrics collector for Task Structured Outputs
收集 TASK_OUTPUT 事件的关键指标

NOTE: Avoid high-cardinality labels (job_id, crew_id, task_id) as they cause
memory leaks - each unique label combination creates a new metrics series.
"""

from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from AICrews.observability.logging import get_logger
logger = get_logger(__name__)


class TaskOutputMetrics:
    """Task Output 相关的 Prometheus 指标

    Uses LOW-CARDINALITY labels only (output_mode, error_type) to prevent
    memory leaks from metrics series accumulation.
    """

    def __init__(self, registry: CollectorRegistry = None):
        """
        初始化 Prometheus 指标

        Args:
            registry: Prometheus registry，如果为 None 则使用默认 registry
        """
        self.registry = registry

        # 1. 总输出计数 (LOW CARDINALITY: only output_mode)
        self.task_output_total = Counter(
            'task_output_total',
            'Total number of task outputs',
            ['output_mode'],
            registry=self.registry
        )

        # 2. 验证通过计数 (LOW CARDINALITY: only output_mode)
        self.task_output_validation_passed = Counter(
            'task_output_validation_passed',
            'Number of task outputs that passed validation',
            ['output_mode'],
            registry=self.registry
        )

        # 3. 验证失败计数 (LOW CARDINALITY: output_mode, error_type)
        self.task_output_validation_failed = Counter(
            'task_output_validation_failed',
            'Number of task outputs that failed validation',
            ['output_mode', 'error_type'],
            registry=self.registry
        )

        # 4. Guardrail 重试次数分布 (LOW CARDINALITY: none)
        self.guardrail_retry_count = Histogram(
            'guardrail_retry_count',
            'Distribution of guardrail retry counts',
            buckets=[0, 1, 2, 3, 5, 10],
            registry=self.registry
        )

        # 5. 降级事件计数 (LOW CARDINALITY: degraded_from, degraded_to)
        self.task_output_degraded = Counter(
            'task_output_degraded',
            'Number of task outputs that were degraded from native to soft mode',
            ['degraded_from', 'degraded_to'],
            registry=self.registry
        )

        # 6. Citations 计数分布 (LOW CARDINALITY: none)
        self.citation_count = Histogram(
            'citation_count',
            'Distribution of citation counts per task output',
            buckets=[0, 1, 3, 5, 10, 20],
            registry=self.registry
        )

        # 7. 输出长度分布 (LOW CARDINALITY: only output_mode)
        self.output_length = Histogram(
            'output_length_bytes',
            'Distribution of output lengths in bytes',
            ['output_mode'],
            buckets=[100, 500, 1000, 2000, 5000, 10000],
            registry=self.registry
        )

        # 8. 当前活跃的结构化输出任务数
        self.active_structured_tasks = Gauge(
            'active_structured_tasks',
            'Number of active tasks using structured output',
            ['output_mode'],
            registry=self.registry
        )

    def record_task_output_event(
        self,
        payload: Dict[str, Any]
    ) -> None:
        """
        从 TASK_OUTPUT 事件中提取并记录指标

        Args:
            payload: TASK_OUTPUT 事件的 payload (3层结构)

        Note: crew_id and task_id are intentionally NOT recorded as labels
        to prevent high-cardinality memory leaks.
        """
        try:
            summary = payload.get("summary", {})
            diagnostics = payload.get("diagnostics", {})

            output_mode = diagnostics.get("output_mode", "raw")
            validation_passed = summary.get("validation_passed", True)
            citation_count = diagnostics.get("citation_count", 0)
            guardrail_retries = diagnostics.get("guardrail_retries", 0)
            degraded_from = diagnostics.get("degraded_from")
            raw_preview = summary.get("raw_preview", "")

            # 记录总数 (LOW CARDINALITY)
            self.task_output_total.labels(
                output_mode=output_mode
            ).inc()

            # 记录验证状态 (LOW CARDINALITY)
            if validation_passed:
                self.task_output_validation_passed.labels(
                    output_mode=output_mode
                ).inc()
            else:
                error_type = diagnostics.get("parse_error_type", "unknown")
                self.task_output_validation_failed.labels(
                    output_mode=output_mode,
                    error_type=error_type
                ).inc()

            # 记录 guardrail 重试次数 (NO LABELS)
            if output_mode.startswith("soft_"):
                self.guardrail_retry_count.observe(guardrail_retries)

            # 记录降级事件 (LOW CARDINALITY)
            if degraded_from:
                self.task_output_degraded.labels(
                    degraded_from=degraded_from,
                    degraded_to=output_mode
                ).inc()

            # 记录 citations 数量 (NO LABELS)
            self.citation_count.observe(citation_count)

            # 记录输出长度 (LOW CARDINALITY)
            self.output_length.labels(
                output_mode=output_mode
            ).observe(len(raw_preview.encode('utf-8')))

        except Exception as e:
            logger.error(f"Failed to record task output metrics: {e}")

    def update_active_tasks_gauge(self, output_mode_counts: Dict[str, int]) -> None:
        """
        更新当前活跃的结构化输出任务数

        Args:
            output_mode_counts: {output_mode: count} 字典
        """
        for output_mode, count in output_mode_counts.items():
            self.active_structured_tasks.labels(
                output_mode=output_mode
            ).set(count)


# 全局单例和共享 registry
_metrics_instance = None
_shared_registry = None


def set_shared_registry(registry: CollectorRegistry) -> None:
    """设置共享的 Prometheus registry（由 main.py 调用）"""
    global _shared_registry, _metrics_instance
    _shared_registry = registry
    # 如果已经创建了实例，重新创建以使用共享 registry
    if _metrics_instance is not None:
        _metrics_instance = TaskOutputMetrics(registry=registry)


def get_metrics(registry: CollectorRegistry = None) -> TaskOutputMetrics:
    """获取全局 metrics 实例"""
    global _metrics_instance
    # 如果已设置共享 registry，使用它
    if _shared_registry is not None:
        registry = _shared_registry

    if _metrics_instance is None:
        _metrics_instance = TaskOutputMetrics(registry=registry)
    return _metrics_instance


class MemoryManagementMetrics:
    """Memory Management 相关的 Prometheus 指标

    Low-cardinality gauges for monitoring bounded caches and memory retention policies.
    """

    def __init__(self, registry: CollectorRegistry = None):
        """
        初始化 Memory Management 指标

        Args:
            registry: Prometheus registry，如果为 None 则使用默认 registry
        """
        self.registry = registry

        # JobManager metrics
        self.job_manager_jobs_in_memory = Gauge(
            'job_manager_jobs_in_memory',
            'Number of jobs currently held in JobManager memory',
            registry=self.registry
        )
        self.job_manager_jobs_running = Gauge(
            'job_manager_jobs_running',
            'Number of jobs currently in running state',
            registry=self.registry
        )

        # TrackingService metrics
        self.tracking_service_runs_in_memory = Gauge(
            'tracking_service_runs_in_memory',
            'Number of runs currently held in TrackingService memory',
            registry=self.registry
        )
        self.tracking_service_runs_running = Gauge(
            'tracking_service_runs_running',
            'Number of runs currently in running state',
            registry=self.registry
        )

        # Cache size metrics (total entries, not per-key)
        self.cache_size = Gauge(
            'cache_size',
            'Number of entries in various caches',
            ['cache_name'],
            registry=self.registry
        )

        # WebSocket ConnectionManager metrics
        self.websocket_active_runs = Gauge(
            'websocket_active_runs',
            'Number of runs with message history in WebSocket manager',
            registry=self.registry
        )
        self.websocket_active_connections = Gauge(
            'websocket_active_connections',
            'Number of active WebSocket connections',
            registry=self.registry
        )

    def update_job_manager_stats(self, total_jobs: int, running_jobs: int) -> None:
        """Update JobManager statistics"""
        self.job_manager_jobs_in_memory.set(total_jobs)
        self.job_manager_jobs_running.set(running_jobs)

    def update_tracking_service_stats(self, total_runs: int, running_runs: int) -> None:
        """Update TrackingService statistics"""
        self.tracking_service_runs_in_memory.set(total_runs)
        self.tracking_service_runs_running.set(running_runs)

    def update_cache_size(self, cache_name: str, size: int) -> None:
        """
        Update cache size gauge

        Args:
            cache_name: Name of the cache (e.g., 'smart_rss', 'news_service', 'model_service')
            size: Number of entries in the cache
        """
        self.cache_size.labels(cache_name=cache_name).set(size)

    def update_websocket_stats(self, active_runs: int, active_connections: int) -> None:
        """Update WebSocket ConnectionManager statistics"""
        self.websocket_active_runs.set(active_runs)
        self.websocket_active_connections.set(active_connections)


# 全局 MemoryManagementMetrics 单例
_memory_metrics_instance = None


def get_memory_metrics(registry: CollectorRegistry = None) -> MemoryManagementMetrics:
    """获取全局 MemoryManagementMetrics 实例"""
    global _memory_metrics_instance
    # 如果已设置共享 registry，使用它
    if _shared_registry is not None:
        registry = _shared_registry

    if _memory_metrics_instance is None:
        _memory_metrics_instance = MemoryManagementMetrics(registry=registry)
    return _memory_metrics_instance

