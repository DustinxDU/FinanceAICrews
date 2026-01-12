"""
Services - 业务逻辑层

统一导出所有服务。

服务分类:
- 核心服务 (Core): BaseService, UserService, MarketService, AnalysisService
- 领域服务 (Domain): PortfolioService, CockpitService, NewsService, etc.
- 基础设施服务 (Infrastructure): UnifiedSyncService, NotificationService, etc.
- 分析服务 (Analysis): QuickAnalysisService, InsightIngestor
- 管理服务 (Admin): ProviderCredentialService, UsageService, etc.

导入方式:
    from AICrews.services import (
        BaseService,
        UserService,
        MarketService,
        AnalysisService,
        PortfolioService,
        # ... etc
    )
"""

from __future__ import annotations

# Core Services
from .base import BaseService
from .user_service import UserService
from .market_service import MarketService
from .analysis_service import AnalysisService

# Domain Services
from .portfolio_service import PortfolioService
from .cockpit_service import CockpitService
from .news_service import NewsService, get_news_service
from .knowledge_service import KnowledgeService
from .chart_service import ChartDataService
from .copilot_service import CopilotService
from .strategy_service import StrategyService
from .library_service import LibraryService
from .template_service import TemplateService
from .export_service import ExportService

# Infrastructure Services
from .unified_sync_service import UnifiedSyncService, get_unified_sync_service
from .daily_archiver_service import DailyArchiverService, get_daily_archiver_service
from .cockpit_macro_sync_service import (
    CockpitMacroSyncService,
    get_cockpit_macro_sync_service,
)
from .notification_service import NotificationService
from .user_notification_service import UserNotificationService
from .tracking_service import TrackingService
from .realtime_ws_manager import RealtimeWebSocketManager, get_realtime_ws_manager
from .security_service import TwoFactorAuthService, SessionService
from .privacy_service import PrivacyService
from .stripe_service import StripeService

# Analysis Services
from .quick_analysis_service import QuickAnalysisService
from .insight_ingestor import InsightIngestor, get_insight_ingestor
from .crew_run_archive_service import archive_crew_run_result

# Admin Services
from .provider_credential_service import (
    ProviderCredentialService,
    get_provider_credential_service,
)
from .provisioner_service import ProvisionerService
from .usage_service import UsageService
from .health_metrics_service import (
    ProviderHealthMetricsService,
    get_health_metrics_service,
)
from .litellm_admin_client import LiteLLMAdminClient
from .tool_diff_service import ToolDiffService, get_tool_diff_service
from .capability_matcher import CapabilityMatcher, get_capability_matcher
from .loadout_resolver import LoadoutResolver
from .llm_policy_seed import ensure_default_system_profiles

__all__ = [
    # Core
    "BaseService",
    "UserService",
    "MarketService",
    "AnalysisService",
    # Domain
    "PortfolioService",
    "CockpitService",
    "NewsService",
    "get_news_service",
    "KnowledgeService",
    "ChartDataService",
    "CopilotService",
    "StrategyService",
    "LibraryService",
    "TemplateService",
    "ExportService",
    # Infrastructure
    "UnifiedSyncService",
    "get_unified_sync_service",
    "DailyArchiverService",
    "get_daily_archiver_service",
    "CockpitMacroSyncService",
    "get_cockpit_macro_sync_service",
    "NotificationService",
    "UserNotificationService",
    "TrackingService",
    "RealtimeWebSocketManager",
    "get_realtime_ws_manager",
    "TwoFactorAuthService",
    "SessionService",
    "PrivacyService",
    "StripeService",
    # Analysis
    "QuickAnalysisService",
    "InsightIngestor",
    "get_insight_ingestor",
    "archive_crew_run_result",
    # Admin
    "ProviderCredentialService",
    "get_provider_credential_service",
    "ProvisionerService",
    "UsageService",
    "ProviderHealthMetricsService",
    "get_health_metrics_service",
    "LiteLLMAdminClient",
    "ToolDiffService",
    "get_tool_diff_service",
    "CapabilityMatcher",
    "get_capability_matcher",
    "LoadoutResolver",
    "ensure_default_system_profiles",
]
