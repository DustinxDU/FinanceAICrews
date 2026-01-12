"""
Prometheus Metrics Endpoint
暴露 Task Structured Outputs 相关的监控指标
"""

import os
from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import logging

logger = logging.getLogger(__name__)

# Environment check for test endpoints
_IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/prometheus")
async def prometheus_metrics():
    """
    导出 Prometheus 格式的指标

    返回格式符合 Prometheus text-based exposition format
    Grafana/Prometheus 可以定期抓取这个 endpoint

    示例 URL: http://localhost:8000/api/v1/metrics/prometheus
    """
    try:
        metrics_output = generate_latest()
        return Response(
            content=metrics_output,
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Failed to generate Prometheus metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {e}\n",
            media_type="text/plain",
            status_code=500
        )


@router.get("/health")
async def metrics_health():
    """
    健康检查端点
    用于验证 metrics 服务是否正常运行
    """
    try:
        from AICrews.infrastructure.metrics import get_metrics
        metrics = get_metrics()

        return {
            "status": "healthy",
            "metrics_enabled": metrics is not None,
            "endpoint": "/api/v1/metrics/prometheus"
        }
    except Exception as e:
        logger.error(f"Metrics health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Only register test endpoint in non-production environments
if not _IS_PRODUCTION:
    @router.post("/test-task-output")
    async def test_task_output():
        """
        测试端点：触发一个模拟的 TASK_OUTPUT 事件

        用于验证 Prometheus metrics 是否正确采集和导出

        NOTE: This endpoint is disabled in production (ENVIRONMENT=production).
        """
        try:
            from AICrews.services.tracking_service import TrackingService

            # 创建测试 payload（模拟 soft_pydantic 模式）
            test_payload = {
                "summary": {
                    "raw_preview": "Test output: AI is transforming the world!",
                    "validation_passed": True,
                    "has_pydantic": True
                },
                "artifact_ref": {
                    "tasks_output_path": "artifacts/test/tasks_output.json"
                },
                "diagnostics": {
                    "output_mode": "soft_pydantic",
                    "schema_key": "sentiment_analysis_v1",
                    "degraded_from": None,
                    "citation_count": 3,
                    "guardrail_retries": 1,
                    "parse_error_type": None
                }
            }

            # 记录事件（会自动触发 metrics 采集）
            ts = TrackingService()
            ts.add_task_output_event(
                job_id="test_metrics_job",
                agent_name="Test Agent",
                task_id="999",
                payload=test_payload,
                severity="info"
            )

            return {
                "status": "success",
                "message": "Test TASK_OUTPUT event recorded",
                "job_id": "test_metrics_job",
                "validation_passed": test_payload["summary"]["validation_passed"],
                "output_mode": test_payload["diagnostics"]["output_mode"]
            }
        except Exception as e:
            logger.error(f"Failed to record test task output: {e}")
            return {
                "status": "error",
                "message": str(e)
            }, 500
