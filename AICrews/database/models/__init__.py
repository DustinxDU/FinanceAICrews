"""
Database Models - 数据库模型

统一导出所有 ORM 模型。

导入方式:
    from AICrews.database.models import Base, User, Asset, CrewDefinition, ...
"""

from __future__ import annotations

from .base import Base, SourceScope, SourceTier
from .user import (
    User, UserPortfolio, UserCredential, UserUpload,
    UserCockpitIndicator, UserAssetCache, UserStrategy
)
from .market import (
    Asset, RealtimeQuote, StockPrice, FundamentalData,
    FinancialStatement, TechnicalIndicator, MarketNews,
    InsiderActivity, ActiveMonitoring
)
from .llm import (
    LLMProvider, LLMModel, UserLLMConfig,
    UserModelConfig, CrewAgentLLMConfig
)
from .mcp import (
    MCPServer, UserMCPServer, MCPTool,
    UserMCPTool, UserToolConfig, UserMCPSubscription,
    AgentToolBinding
)
from .knowledge import (
    KnowledgeSource, UserKnowledgeSubscription, UserKnowledgeSource,
    CrewKnowledgeBinding, AgentKnowledgeBinding,
    KnowledgeSourceVersion, KnowledgeUsageLog
)
from .agent import (
    AgentDefinition, TaskDefinition, CrewDefinition,
    CrewVersion, TemplateCatalog, TemplateImportLog,
    TemplateUpdateNotification
)
from .cockpit import (
    MacroIndicatorCache, AssetSearchCache
)
from .analysis import (
    AnalysisReport, ExecutionLog, ReportArtifact,
    ReportChunk, TradingLesson
)
from .insight import (
    UserAssetInsight, InsightAttachment, InsightTrace,
    UserToolPreference, BuiltinTool
)
from .skill import (
    SkillKind, SkillCatalog, UserSkillPreference
)
from .provider import (
    CapabilityProvider, ProviderCapabilityMapping
)
from .billing import (
    Subscription, Invoice, StripeEvent
)
from .security import (
    UserSecurity, LoginSession, LoginEvent
)
from .notifications import (
    UserWebhookSettings
)
from .preferences import (
    UserPreferences
)
from .user_preferences import (
    UserNotificationPreferences
)
from .privacy import (
    ExportStatus, DeletionStatus,
    DataExportJob, AccountDeletionRequest
)

__all__ = [
    # Base
    "Base", "SourceScope", "SourceTier",
    
    # User
    "User", "UserPortfolio", "UserCredential", "UserUpload",
    "UserCockpitIndicator", "UserAssetCache", "UserStrategy",
    
    # Market
    "Asset", "RealtimeQuote", "StockPrice", "FundamentalData",
    "FinancialStatement", "TechnicalIndicator", "MarketNews",
    "InsiderActivity", "ActiveMonitoring",
    
    # LLM
    "LLMProvider", "LLMModel", "UserLLMConfig",
    "UserModelConfig", "CrewAgentLLMConfig",
    
    # MCP
    "MCPServer", "UserMCPServer", "MCPTool",
    "UserMCPTool", "UserToolConfig", "UserMCPSubscription",
    "AgentToolBinding",
    
    # Knowledge
    "KnowledgeSource", "UserKnowledgeSubscription", "UserKnowledgeSource",
    "CrewKnowledgeBinding", "AgentKnowledgeBinding",
    "KnowledgeSourceVersion", "KnowledgeUsageLog",
    
    # Agent
    "AgentDefinition", "TaskDefinition", "CrewDefinition",
    "CrewVersion", "TemplateCatalog", "TemplateImportLog",
    "TemplateUpdateNotification",
    
    # Cockpit
    "MacroIndicatorCache", "AssetSearchCache",
    
    # Analysis
    "AnalysisReport", "ExecutionLog", "ReportArtifact",
    "ReportChunk", "TradingLesson",
    
    # Insight
    "UserAssetInsight", "InsightAttachment", "InsightTrace",
    "UserToolPreference", "BuiltinTool",

    # Skill
    "SkillKind", "SkillCatalog", "UserSkillPreference",

    # Provider
    "CapabilityProvider", "ProviderCapabilityMapping",

    # Billing
    "Subscription", "Invoice", "StripeEvent",

    # Security
    "UserSecurity", "LoginSession", "LoginEvent",

    # Notifications
    "UserWebhookSettings",

    # Preferences
    "UserPreferences",

    # User Notification Preferences
    "UserNotificationPreferences",

    # Privacy
    "ExportStatus", "DeletionStatus",
    "DataExportJob", "AccountDeletionRequest",
]
