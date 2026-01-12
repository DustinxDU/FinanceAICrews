"""
Provider Health Metrics Service - Observability for provider reliability.

Implements health tracking with:
- Raw log recording for every healthcheck
- Daily aggregation with percentile latency and reliability scoring
- Exponential weighting for stability
- 30/90-day retention policy
"""
from AICrews.observability.logging import get_logger
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, delete

from AICrews.database.models.provider import (
    CapabilityProvider,
    ProviderHealthLog,
    ProviderHealthDaily
)

logger = get_logger(__name__)


class ProviderHealthMetricsService:
    """
    Service for provider health tracking and metrics aggregation.

    Responsibilities:
    1. Record raw healthcheck results
    2. Compute daily aggregated metrics (error_rate, reliability_score, latencies)
    3. Provide metrics API for dashboard queries
    4. Enforce retention policies (30-day logs, 90-day aggregates)
    """

    # Exponential weighting constant (0.95 = ~14 observations of memory)
    DECAY_FACTOR = 0.95

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def record_healthcheck(
        self,
        provider_id: int,
        success: bool,
        latency_ms: int,
        error: Optional[str] = None,
        diagnostic_data: Optional[Dict] = None
    ) -> ProviderHealthLog:
        """
        Record a healthcheck result as raw log entry.

        Args:
            provider_id: Provider ID
            success: Whether healthcheck succeeded
            latency_ms: Response time in milliseconds
            error: Error message (truncated to 200 chars)
            diagnostic_data: Optional diagnostic info (HTTP status, tool count, etc.)

        Returns:
            Created ProviderHealthLog record

        Example:
            >>> service.record_healthcheck(
            ...     provider_id=1,
            ...     success=True,
            ...     latency_ms=250,
            ...     diagnostic_data={"tool_count": 15, "http_status": 200}
            ... )
        """
        # Truncate error message to 200 chars
        if error and len(error) > 200:
            error = error[:197] + "..."

        log = ProviderHealthLog(
            provider_id=provider_id,
            timestamp=datetime.now(),
            success=success,
            latency_ms=latency_ms,
            error=error,
            diagnostic_data=diagnostic_data
        )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        logger.debug(
            f"Recorded healthcheck for provider {provider_id}: "
            f"success={success}, latency={latency_ms}ms"
        )

        return log

    def compute_daily_metrics(
        self,
        provider_id: int,
        target_date: Optional[date] = None
    ) -> ProviderHealthDaily:
        """
        Compute and store daily aggregated metrics for a provider.

        Calculates:
        - error_rate: 24h failure rate (0.0-1.0)
        - reliability_score: Exponentially weighted reliability
        - latency_p50/p95/p99: Latency percentiles

        Args:
            provider_id: Provider ID
            target_date: Date to aggregate (defaults to today)

        Returns:
            Created or updated ProviderHealthDaily record

        Raises:
            ValueError: If no healthcheck data exists for the date
        """
        if target_date is None:
            target_date = date.today()

        # Query all healthchecks for this provider on target_date
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())

        logs = self.db.execute(
            select(ProviderHealthLog)
            .where(
                and_(
                    ProviderHealthLog.provider_id == provider_id,
                    ProviderHealthLog.timestamp >= start_dt,
                    ProviderHealthLog.timestamp <= end_dt
                )
            )
            .order_by(ProviderHealthLog.timestamp)
        ).scalars().all()

        if not logs:
            raise ValueError(
                f"No healthcheck data for provider {provider_id} on {target_date}"
            )

        # Calculate metrics
        total_checks = len(logs)
        failed_checks = sum(1 for log in logs if not log.success)
        error_rate = failed_checks / total_checks

        # Compute reliability score with exponential weighting
        reliability_score = self._compute_reliability_score(provider_id, target_date, logs)

        # Compute latency percentiles
        latencies = sorted([log.latency_ms for log in logs])
        latency_p50 = self._percentile(latencies, 0.50)
        latency_p95 = self._percentile(latencies, 0.95)
        latency_p99 = self._percentile(latencies, 0.99)

        # Create or update daily aggregate
        existing = self.db.execute(
            select(ProviderHealthDaily).where(
                and_(
                    ProviderHealthDaily.provider_id == provider_id,
                    ProviderHealthDaily.date == target_date
                )
            )
        ).scalar_one_or_none()

        if existing:
            # Update existing record
            existing.error_rate = error_rate
            existing.reliability_score = reliability_score
            existing.latency_p50 = latency_p50
            existing.latency_p95 = latency_p95
            existing.latency_p99 = latency_p99
            existing.check_count = total_checks
            existing.last_updated = datetime.now()
            daily = existing
        else:
            # Create new record
            daily = ProviderHealthDaily(
                provider_id=provider_id,
                date=target_date,
                error_rate=error_rate,
                reliability_score=reliability_score,
                latency_p50=latency_p50,
                latency_p95=latency_p95,
                latency_p99=latency_p99,
                check_count=total_checks
            )
            self.db.add(daily)

        self.db.commit()
        self.db.refresh(daily)

        logger.info(
            f"Computed daily metrics for provider {provider_id} on {target_date}: "
            f"error_rate={error_rate:.2f}, reliability={reliability_score:.2f}"
        )

        return daily

    def _compute_reliability_score(
        self,
        provider_id: int,
        target_date: date,
        current_logs: List[ProviderHealthLog]
    ) -> float:
        """
        Compute exponentially weighted reliability score.

        Formula: score = DECAY_FACTOR * previous_score + (1 - DECAY_FACTOR) * current_success_rate

        Args:
            provider_id: Provider ID
            target_date: Date being computed
            current_logs: Today's healthcheck logs

        Returns:
            Reliability score (0.0-1.0)
        """
        # Get previous day's score
        previous_date = target_date - timedelta(days=1)
        previous_daily = self.db.execute(
            select(ProviderHealthDaily).where(
                and_(
                    ProviderHealthDaily.provider_id == provider_id,
                    ProviderHealthDaily.date == previous_date
                )
            )
        ).scalar_one_or_none()

        # Calculate current success rate
        total_checks = len(current_logs)
        successful_checks = sum(1 for log in current_logs if log.success)
        current_success_rate = successful_checks / total_checks if total_checks > 0 else 0.0

        if previous_daily:
            # Exponential weighting: blend previous score with current rate
            score = (
                self.DECAY_FACTOR * previous_daily.reliability_score +
                (1 - self.DECAY_FACTOR) * current_success_rate
            )
        else:
            # First day: use current success rate as baseline
            score = current_success_rate

        return round(score, 4)

    def _percentile(self, sorted_values: List[int], p: float) -> int:
        """
        Calculate percentile using linear interpolation.

        Args:
            sorted_values: Sorted list of values
            p: Percentile (0.0-1.0)

        Returns:
            Percentile value
        """
        if not sorted_values:
            return 0

        n = len(sorted_values)
        if n == 1:
            return sorted_values[0]

        # Linear interpolation
        index = p * (n - 1)
        lower_idx = int(index)
        upper_idx = min(lower_idx + 1, n - 1)

        if lower_idx == upper_idx:
            return sorted_values[lower_idx]

        # Interpolate between lower and upper
        fraction = index - lower_idx
        return int(
            sorted_values[lower_idx] +
            fraction * (sorted_values[upper_idx] - sorted_values[lower_idx])
        )

    def get_provider_metrics(
        self,
        provider_id: int,
        days: int = 7
    ) -> List[ProviderHealthDaily]:
        """
        Get aggregated health metrics for a provider over the last N days.

        Args:
            provider_id: Provider ID
            days: Number of days to retrieve (default: 7)

        Returns:
            List of ProviderHealthDaily records, ordered by date descending
        """
        cutoff_date = date.today() - timedelta(days=days)

        metrics = self.db.execute(
            select(ProviderHealthDaily)
            .where(
                and_(
                    ProviderHealthDaily.provider_id == provider_id,
                    ProviderHealthDaily.date > cutoff_date
                )
            )
            .order_by(ProviderHealthDaily.date.desc())
        ).scalars().all()

        return list(metrics)

    def cleanup_old_logs(self, retention_days: int = 30) -> int:
        """
        Delete raw healthcheck logs older than retention period.

        Args:
            retention_days: Number of days to retain (default: 30)

        Returns:
            Number of records deleted
        """
        # Use retention_days + 1 to ensure logs at exactly retention boundary are kept
        cutoff_date = datetime.now() - timedelta(days=retention_days + 1)

        result = self.db.execute(
            delete(ProviderHealthLog).where(
                ProviderHealthLog.timestamp <= cutoff_date
            )
        )

        deleted_count = result.rowcount
        self.db.commit()

        logger.info(f"Deleted {deleted_count} healthcheck logs older than {retention_days} days")
        return deleted_count

    def cleanup_old_aggregates(self, retention_days: int = 90) -> int:
        """
        Delete daily aggregates older than retention period.

        Args:
            retention_days: Number of days to retain (default: 90)

        Returns:
            Number of records deleted
        """
        cutoff_date = date.today() - timedelta(days=retention_days)

        result = self.db.execute(
            delete(ProviderHealthDaily).where(
                ProviderHealthDaily.date < cutoff_date
            )
        )

        deleted_count = result.rowcount
        self.db.commit()

        logger.info(f"Deleted {deleted_count} daily aggregates older than {retention_days} days")
        return deleted_count


def get_health_metrics_service(db: Session) -> ProviderHealthMetricsService:
    """Factory function to get ProviderHealthMetricsService instance."""
    return ProviderHealthMetricsService(db)
