"""API v1 router aggregation.

Keep `backend.app.main` thin by collecting all v1 routers here.

All endpoint files define their own prefix and tags.
This file only aggregates them, organized by functional domain.
"""

from fastapi import APIRouter

from backend.app.api.v1.endpoints.analysis import router as analysis_router
from backend.app.api.v1.endpoints.auth import router as auth_router
from backend.app.api.v1.endpoints.billing import router as billing_router
from backend.app.api.v1.endpoints.charts import router as charts_router
from backend.app.api.v1.endpoints.cockpit import router as cockpit_router
from backend.app.api.v1.endpoints.copilot import router as copilot_router
from backend.app.api.v1.endpoints.crew_builder import router as crew_builder_router
from backend.app.api.v1.endpoints.entitlements import router as entitlements_router
from backend.app.api.v1.endpoints.knowledge import router as knowledge_router
from backend.app.api.v1.endpoints.library import router as library_router
from backend.app.api.v1.endpoints.llm_policy import router as llm_policy_router
from backend.app.api.v1.endpoints.market import router as market_router
from backend.app.api.v1.endpoints.notifications import router as notifications_router
from backend.app.api.v1.endpoints.news import router as news_router
from backend.app.api.v1.endpoints.portfolio import router as portfolio_router
from backend.app.api.v1.endpoints.profile import router as profile_router
from backend.app.api.v1.endpoints.preferences import router as preferences_router
from backend.app.api.v1.endpoints.quick_analysis import router as quick_analysis_router
from backend.app.api.v1.endpoints.security import router as security_router
from backend.app.api.v1.endpoints.strategies import router as strategies_router
from backend.app.api.v1.endpoints.system import router as system_router
from backend.app.api.v1.endpoints.templates import router as templates_router
from backend.app.api.v1.endpoints.task_output_schemas import router as task_output_schemas_router
from backend.app.api.v1.endpoints.tool_registry import router as tool_registry_router
from backend.app.api.v1.endpoints.tool_usage import router as tool_usage_router
from backend.app.api.v1.endpoints.tracking import router as tracking_router
from backend.app.api.v1.endpoints.usage import router as usage_router
from backend.app.api.v1.endpoints.skills import router as skills_router
from backend.app.api.v1.endpoints.capability_providers import router as providers_router
from backend.app.api.v1.endpoints.metrics import router as metrics_router
from backend.app.api.v1.endpoints.privacy import router as privacy_router
from backend.app.api.v1.endpoints.agent_models import router as agent_models_router

router = APIRouter(prefix="/api/v1")

# ============================================
# Authentication & User Management
# ============================================
router.include_router(auth_router)
router.include_router(profile_router)
router.include_router(security_router)
router.include_router(preferences_router)
router.include_router(privacy_router)

# ============================================
# Billing & Entitlements
# ============================================
router.include_router(billing_router)
router.include_router(entitlements_router)
router.include_router(notifications_router)

# ============================================
# Analysis & AI Copilot
# ============================================
router.include_router(analysis_router)
router.include_router(quick_analysis_router)
router.include_router(copilot_router)
router.include_router(llm_policy_router)

# ============================================
# Crew Configuration
# ============================================
router.include_router(crew_builder_router)
router.include_router(agent_models_router)

# ============================================
# Tools & Templates
# ============================================
router.include_router(tool_registry_router)
router.include_router(tool_usage_router)
router.include_router(task_output_schemas_router)
router.include_router(templates_router)

# ============================================
# Market Data & Portfolio
# ============================================
router.include_router(market_router)
router.include_router(portfolio_router)
router.include_router(charts_router)
router.include_router(news_router)
router.include_router(library_router)
router.include_router(cockpit_router)

# ============================================
# System & Monitoring
# ============================================
router.include_router(tracking_router)
router.include_router(usage_router)
router.include_router(system_router)
router.include_router(metrics_router)

# ============================================
# Knowledge & Strategies
# ============================================
router.include_router(knowledge_router)
router.include_router(strategies_router)
router.include_router(skills_router)
router.include_router(providers_router)
