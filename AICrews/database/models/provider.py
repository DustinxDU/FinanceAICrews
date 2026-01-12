"""Provider and capability mapping models.

Providers are MCP servers or builtin tool collections that implement capabilities.
The mapping table links providers to capability_ids from the taxonomy.

Health monitoring models track provider reliability and performance over time.
"""
from sqlalchemy import String, Boolean, JSON, Integer, Float, ForeignKey, UniqueConstraint, DateTime, Index, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from AICrews.database.models.base import Base


class CapabilityProvider(Base):
    """MCP or builtin provider that implements capabilities.

    Providers are the "source" layer in the Provider → Capability → Skill architecture.
    Each provider can implement multiple capabilities (1:N relationship via mappings).

    Provider types:
    - mcp: MCP server (HTTP/SSE/stdio transport)
    - builtin_external: Built-in external tools (SerperDevTool, ScrapeWebsiteTool)
    - builtin_compute: Built-in compute tools (indicator_calc, strategy_eval)

    Attributes:
        provider_key: Unique identifier (e.g., "mcp:akshare", "builtin:quant")
        provider_type: One of: "mcp", "builtin_external", "builtin_compute"
        url: Connection URL for MCP providers (kept for backwards compatibility)
        config: Provider-specific configuration (auth, timeouts, etc.)
        connection_schema: Unified connection schema for all provider types
            - MCP: {"url": "http://...", "transport": "sse"}
            - Builtin external: {"requires_env": ["SERPER_API_KEY"]}
            - Builtin compute: {} (no special config needed)
        enabled: Whether this provider is active
        healthy: Health check status (updated periodically)
        priority: Routing priority (higher = preferred) for capability resolution
        last_health_check: Timestamp of last health check
    """

    __tablename__ = "capability_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(String(20), nullable=False)  # mcp, builtin_external, builtin_compute

    # Connection info (for MCP providers - kept for backwards compatibility)
    url: Mapped[str | None] = mapped_column(String(500))
    config: Mapped[dict | None] = mapped_column(JSON)  # auth, headers, timeout, etc.

    # NEW: Unified connection schema
    # MCP: {"url": "http://...", "transport": "sse"}
    # Builtin external: {"requires_env": ["SERPER_API_KEY"]}
    # Builtin compute: {} (no special config needed)
    connection_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    healthy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime)

    # Routing priority (higher = preferred when multiple providers offer same capability)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    mappings: Mapped[list["ProviderCapabilityMapping"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<CapabilityProvider(id={self.id}, key='{self.provider_key}', "
            f"type='{self.provider_type}', enabled={self.enabled}, healthy={self.healthy})>"
        )


class ProviderCapabilityMapping(Base):
    """Maps provider to capability_id from taxonomy.

    This table defines which capabilities a provider implements.
    A provider can implement multiple capabilities, and a capability can be
    implemented by multiple providers (N:M via this mapping table).

    Attributes:
        provider_id: Foreign key to CapabilityProvider
        capability_id: Capability from taxonomy (e.g., "equity_quote", "web_search")
        raw_tool_name: Provider's native tool name (for MCP tool discovery)
        priority: Routing priority within this capability (higher = tried first, default 50)
        config: Capability-specific overrides (optional)
    """

    __tablename__ = "provider_capability_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("capability_providers.id", ondelete="CASCADE"), nullable=False
    )
    capability_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Provider's raw tool name (for MCP providers)
    # Example: akshare provider might map capability "equity_quote" to raw tool "stock_zh_a_spot_em"
    raw_tool_name: Mapped[str | None] = mapped_column(String(200))

    # Routing priority within this capability (higher = tried first)
    # Default 50 allows room for both higher and lower priorities
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    # Capability-specific config overrides (optional)
    config: Mapped[dict | None] = mapped_column(JSON)

    # Relationships
    provider: Mapped["CapabilityProvider"] = relationship(back_populates="mappings")

    __table_args__ = (
        UniqueConstraint("provider_id", "capability_id", name="uq_provider_capability"),
    )

    def __repr__(self):
        return (
            f"<ProviderCapabilityMapping(provider_id={self.provider_id}, "
            f"capability='{self.capability_id}', raw_tool='{self.raw_tool_name}')>"
        )


class ProviderHealthLog(Base):
    """Raw health check logs for providers (30-day retention).

    Records every health check attempt with success/failure status and latency.
    Automatically cleaned up after 30 days via daily cron job.

    Attributes:
        provider_id: Foreign key to CapabilityProvider
        timestamp: When health check was performed
        success: Whether health check succeeded
        latency_ms: Response time in milliseconds
        error: Error message (first 200 chars) if failed
        diagnostic_data: Additional diagnostic info (optional)
    """

    __tablename__ = "provider_health_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("capability_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # Error message (truncated to 200 chars for storage efficiency)
    error: Mapped[str | None] = mapped_column(String(200))

    # Optional diagnostic data (HTTP status, tool count, etc.)
    diagnostic_data: Mapped[dict | None] = mapped_column(JSON)

    # Composite index for time-range queries
    __table_args__ = (
        Index('ix_provider_health_logs_provider_timestamp', 'provider_id', 'timestamp'),
    )

    def __repr__(self):
        status = "✓" if self.success else "✗"
        return (
            f"<ProviderHealthLog(provider={self.provider_id}, "
            f"time={self.timestamp}, {status}, {self.latency_ms}ms)>"
        )


class ProviderHealthDaily(Base):
    """Aggregated daily health metrics for providers (90-day retention).

    Pre-aggregated daily statistics for efficient dashboard queries.
    Updated daily via scheduled job that processes raw logs.

    Metrics:
        error_rate: 24h failure rate (0.0-1.0)
        reliability_score: Exponentially weighted reliability (0.0-1.0)
        latency_p50/p95/p99: Latency percentiles in milliseconds
        check_count: Number of health checks performed that day

    Attributes:
        provider_id: Foreign key to CapabilityProvider
        date: Date of aggregation (YYYY-MM-DD)
        error_rate: 24h failure rate
        reliability_score: Exponentially weighted score
        latency_p50: 50th percentile latency (median)
        latency_p95: 95th percentile latency
        latency_p99: 99th percentile latency
        check_count: Number of checks aggregated
        last_updated: When aggregation was computed
    """

    __tablename__ = "provider_health_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("capability_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Reliability metrics (0.0-1.0)
    error_rate: Mapped[float] = mapped_column(Float, nullable=False)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Latency percentiles (milliseconds)
    latency_p50: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_p95: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_p99: Mapped[int] = mapped_column(Integer, nullable=False)

    # Metadata
    check_count: Mapped[int] = mapped_column(Integer, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    __table_args__ = (
        UniqueConstraint('provider_id', 'date', name='uq_provider_health_daily'),
        Index('ix_provider_health_daily_provider_date', 'provider_id', 'date'),
    )

    def __repr__(self):
        return (
            f"<ProviderHealthDaily(provider={self.provider_id}, date={self.date}, "
            f"reliability={self.reliability_score:.2f}, error_rate={self.error_rate:.2f})>"
        )
