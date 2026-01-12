"""
LLM Routing Metrics - Observability for LLM Policy Router

Tracks routing decisions and provisioning events for the LLM Policy Router system.
"""

from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from AICrews.observability.logging import get_logger
logger = get_logger(__name__)


class LLMRoutingMetrics:
    """LLM routing observability metrics"""

    def __init__(self, registry: CollectorRegistry = None):
        """
        Initialize LLM routing Prometheus metrics

        Args:
            registry: Prometheus registry, uses default if None
        """
        self.registry = registry

        # =====================================================================
        # Policy Router Metrics
        # =====================================================================

        # 1. Total router resolve calls
        self.router_resolve_total = Counter(
            'llm_router_resolve_total',
            'Total number of Policy Router resolve() calls',
            ['scope', 'routing_effective', 'result'],
            registry=self.registry
        )

        # 2. BYOK test calls
        self.byok_test_total = Counter(
            'llm_byok_test_total',
            'Total number of BYOK credential test calls',
            ['provider', 'result', 'error_code'],
            registry=self.registry
        )

        # 3. Virtual key provisioning events
        self.provisioning_total = Counter(
            'llm_provisioning_total',
            'Total number of virtual key provisioning attempts',
            ['user_tier', 'result'],
            registry=self.registry
        )

        # 4. Active virtual keys gauge
        self.active_virtual_keys = Gauge(
            'llm_active_virtual_keys',
            'Number of active virtual keys per status',
            ['status'],  # active, provisioning, failed, revoked
            registry=self.registry
        )

        # 5. Routing mode distribution
        self.routing_mode_total = Counter(
            'llm_routing_mode_total',
            'Distribution of routing modes used',
            ['scope', 'mode'],  # mode: system, byok
            registry=self.registry
        )

        # 6. LLM call duration histogram
        self.llm_call_duration = Histogram(
            'llm_call_duration_ms',
            'LLM call duration distribution',
            ['routing_type', 'scope'],
            buckets=[100, 500, 1000, 2000, 5000, 10000, 30000],
            registry=self.registry
        )

    def record_router_resolve(
        self,
        scope: str,
        routing_effective: str,
        result: str = "success"
    ) -> None:
        """
        Record a Policy Router resolve() call

        Args:
            scope: LLM scope (copilot, crew_analysis, agents_fast, etc.)
            routing_effective: Effective routing mode (system, byok)
            result: success, error, provisioning_error
        """
        try:
            self.router_resolve_total.labels(
                scope=scope,
                routing_effective=routing_effective,
                result=result
            ).inc()

            self.routing_mode_total.labels(
                scope=scope,
                mode=routing_effective
            ).inc()
        except Exception as e:
            logger.error(f"Failed to record router resolve metrics: {e}")

    def record_byok_test(
        self,
        provider: str,
        result: str,
        error_code: Optional[str] = None
    ) -> None:
        """
        Record a BYOK credential test call

        Args:
            provider: LLM provider (openai, anthropic, etc.)
            result: success, failure
            error_code: Error code if failed (invalid_key, network_error, etc.)
        """
        try:
            self.byok_test_total.labels(
                provider=provider,
                result=result,
                error_code=error_code or "none"
            ).inc()
        except Exception as e:
            logger.error(f"Failed to record BYOK test metrics: {e}")

    def record_provisioning_attempt(
        self,
        user_tier: str,
        result: str
    ) -> None:
        """
        Record a virtual key provisioning attempt

        Args:
            user_tier: User tier (agents_fast, agents_balanced, agents_best)
            result: success, pending, failed
        """
        try:
            self.provisioning_total.labels(
                user_tier=user_tier,
                result=result
            ).inc()
        except Exception as e:
            logger.error(f"Failed to record provisioning metrics: {e}")

    def update_active_virtual_keys_gauge(self, status_counts: dict) -> None:
        """
        Update active virtual keys gauge

        Args:
            status_counts: Dict of {status: count} from database query
                          e.g., {"active": 42, "provisioning": 3, "failed": 1}
        """
        try:
            for status, count in status_counts.items():
                self.active_virtual_keys.labels(status=status).set(count)
        except Exception as e:
            logger.error(f"Failed to update virtual keys gauge: {e}")

    def record_llm_call_duration(
        self,
        duration_ms: int,
        routing_type: str,
        scope: Optional[str] = None
    ) -> None:
        """
        Record LLM call duration

        Args:
            duration_ms: Duration in milliseconds
            routing_type: Routing type identifier
            scope: LLM scope (optional)
        """
        try:
            self.llm_call_duration.labels(
                routing_type=routing_type,
                scope=scope or "unknown"
            ).observe(duration_ms)
        except Exception as e:
            logger.error(f"Failed to record LLM call duration: {e}")


# Global singleton
_llm_routing_metrics_instance = None


def get_llm_routing_metrics(registry: CollectorRegistry = None) -> LLMRoutingMetrics:
    """Get global LLM routing metrics instance"""
    global _llm_routing_metrics_instance
    if _llm_routing_metrics_instance is None:
        _llm_routing_metrics_instance = LLMRoutingMetrics(registry=registry)
    return _llm_routing_metrics_instance
