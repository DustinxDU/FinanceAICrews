"""Provider management endpoints.

Provides REST API for managing capability providers (MCP servers, builtin tools)
and their capability mappings.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional, Dict
from datetime import datetime
import logging

from backend.app.security import get_db, get_current_user
from AICrews.database.models.provider import CapabilityProvider, ProviderCapabilityMapping
from AICrews.capabilities.taxonomy import ALL_CAPABILITIES
from AICrews.schemas.provider import (
    CreateProviderRequest,
    CapabilityMappingRequest,
    CapabilityProviderResponse as ProviderResponse,
    CapabilityProviderDetailResponse as ProviderDetailResponse,
    SaveApiKeyRequest,
    VerifyApiKeyResponse,
    CredentialStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["Providers"])


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=List[ProviderResponse])
async def list_providers(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    List all providers with their mapped capabilities.

    Returns provider summary including health status and capability count.
    """
    providers = db.query(CapabilityProvider).all()

    return [
        ProviderResponse(
            id=p.id,
            provider_key=p.provider_key,
            provider_type=p.provider_type,
            url=p.url,
            enabled=p.enabled,
            healthy=p.healthy,
            priority=p.priority,
            last_health_check=p.last_health_check,
            # Use set to get unique capabilities (multiple tools can map to same capability)
            capabilities=list(set(m.capability_id for m in p.mappings))
        )
        for p in providers
    ]


@router.get("/{provider_id}", response_model=ProviderDetailResponse)
async def get_provider_detail(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get detailed provider information including all mappings.
    """
    provider = db.query(CapabilityProvider).filter_by(id=provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    return ProviderDetailResponse(
        id=provider.id,
        provider_key=provider.provider_key,
        provider_type=provider.provider_type,
        url=provider.url,
        config=provider.config,
        enabled=provider.enabled,
        healthy=provider.healthy,
        priority=provider.priority,
        last_health_check=provider.last_health_check,
        mappings=[
            {
                "capability_id": m.capability_id,
                "raw_tool_name": m.raw_tool_name,
                "config": m.config,
            }
            for m in provider.mappings
        ]
    )


@router.post("", response_model=dict)
async def create_provider(
    request: CreateProviderRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new provider.

    Provider is created in disabled state by default (design principle:
    new providers/capabilities must be explicitly enabled by user).

    For MCP providers, this endpoint should be followed by:
    1. Tool discovery (separate endpoint or client-side)
    2. POST /{provider_id}/mapping to confirm capability mappings
    3. POST /{provider_id}/enable to activate

    Returns:
        provider_id and message with next steps
    """
    # Validate/Normalize provider_key
    if request.provider_type == "mcp":
        if not request.provider_key.startswith("mcp:"):
            # Auto-prefix if missing
            request.provider_key = f"mcp:{request.provider_key}"

    # Check if provider_key already exists
    existing = db.query(CapabilityProvider).filter_by(
        provider_key=request.provider_key
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Provider with key '{request.provider_key}' already exists"
        )

    # Create provider (disabled by default)
    # Healthy defaults to True for builtin, False for MCP (until checked)
    is_builtin = request.provider_type.startswith("builtin")
    provider = CapabilityProvider(
        provider_key=request.provider_key,
        provider_type=request.provider_type,
        url=request.url,
        config=request.config or {},
        enabled=is_builtin,  # Auto-enable builtin
        healthy=is_builtin,  # Auto-healthy builtin
        priority=request.priority,
    )

    db.add(provider)
    db.commit()
    db.refresh(provider)

    # Optional: Initial discovery if URL provided (best effort)
    discovered_tools = []
    mapping_suggestions = []

    if request.provider_type == "mcp" and request.url:
        try:
            from AICrews.infrastructure.mcp import MCPDiscoveryClient
            from AICrews.services.capability_matcher import get_capability_matcher

            client = MCPDiscoveryClient(server_url=request.url, timeout=5)
            # Use short timeout for inline discovery
            fresh_tools = await client.list_tools()

            if fresh_tools:
                # Extract tool names for backward compatibility
                discovered_tools = [t.get("name") for t in fresh_tools if t.get("name")]

                # Smart mapping suggestions using matching engine
                matcher = get_capability_matcher()
                mapping_suggestions = matcher.suggest_mappings(
                    discovered_tools=fresh_tools,
                    provider_key=request.provider_key
                )

                logger.info(
                    f"Provider {request.provider_key}: discovered {len(discovered_tools)} tools, "
                    f"generated {len(mapping_suggestions)} suggestions"
                )

        except Exception as e:
            logger.warning(f"Initial discovery failed for {request.provider_key}: {e}")

    return {
        "provider_id": provider.id,
        "provider_key": provider.provider_key,
        "enabled": provider.enabled,
        "message": "Provider created (disabled). Next: submit capability mapping, then enable.",
        "discovered_tools": discovered_tools,
        "mapping_suggestions": mapping_suggestions  # NEW: Smart suggestions
    }


@router.post("/{provider_id}/mapping", response_model=dict)
async def submit_capability_mapping(
    provider_id: int,
    request: CapabilityMappingRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Submit capability mapping for a provider.

    Supports two formats (auto-detected):
    1. Legacy: { capability_id: raw_tool_name } - one tool per capability
    2. New: { raw_tool_name: capability_id } - multiple tools can map to same capability

    Request body examples:
        Legacy format:
        {
            "mappings": {
                "equity_quote": "stock_zh_a_spot_em",
                "equity_history": "stock_zh_a_hist"
            }
        }

        New format (tool-first):
        {
            "mappings": {
                "stock_zh_a_spot_em": "equity_quote",
                "stock_zh_a_hist": "equity_history",
                "crypto_quote": "crypto",
                "crypto_history": "crypto"  # Multiple tools -> same capability
            }
        }

    Returns:
        Success message with mapped capability count
    """
    provider = db.query(CapabilityProvider).filter_by(id=provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Auto-detect format: check if keys are capability IDs or tool names
    # If most keys are valid capability IDs, it's legacy format
    keys = list(request.mappings.keys())
    capability_key_count = sum(1 for k in keys if k in ALL_CAPABILITIES)

    # Determine format: if >50% of keys are capabilities, it's legacy format
    is_legacy_format = capability_key_count > len(keys) / 2

    # Normalize to list of (capability_id, raw_tool_name) tuples
    mapping_pairs: list[tuple[str, Optional[str]]] = []

    if is_legacy_format:
        # Legacy: { capability_id: raw_tool_name }
        invalid = [cap for cap in keys if cap not in ALL_CAPABILITIES]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid capability IDs (not in taxonomy): {invalid}"
            )
        for capability_id, raw_tool_name in request.mappings.items():
            mapping_pairs.append((capability_id, raw_tool_name))
    else:
        # New format: { raw_tool_name: capability_id }
        invalid_caps = []
        for raw_tool_name, capability_id in request.mappings.items():
            if capability_id and capability_id not in ALL_CAPABILITIES:
                invalid_caps.append(capability_id)
            elif capability_id:  # Skip if capability_id is None/empty
                mapping_pairs.append((capability_id, raw_tool_name))

        if invalid_caps:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid capability IDs (not in taxonomy): {list(set(invalid_caps))}"
            )

    # Clear existing mappings for this provider
    db.query(ProviderCapabilityMapping).filter_by(provider_id=provider_id).delete()

    # Determine default priority based on provider type
    # - MCP providers: 50-70 based on server (akshare=70, yfinance=60, others=50)
    # - Builtin with API key: 70 (user explicitly configured)
    # - Builtin free: 50 (default)
    default_priority = 50
    if provider.provider_type == "mcp":
        if "akshare" in provider.provider_key:
            default_priority = 70
        elif "yfinance" in provider.provider_key:
            default_priority = 60
    elif provider.provider_type.startswith("builtin"):
        # Check if requires API key
        connection_schema = provider.connection_schema or {}
        if connection_schema.get("requires_env"):
            default_priority = 70  # Premium tool

    # Add new mappings
    capabilities_mapped = set()
    for capability_id, raw_tool_name in mapping_pairs:
        mapping = ProviderCapabilityMapping(
            provider_id=provider_id,
            capability_id=capability_id,
            raw_tool_name=raw_tool_name,
            priority=default_priority,  # Use calculated default priority
        )
        db.add(mapping)
        capabilities_mapped.add(capability_id)

    db.commit()

    return {
        "provider_id": provider_id,
        "provider_key": provider.provider_key,
        "mapped_count": len(mapping_pairs),
        "capabilities": list(capabilities_mapped),
        "message": f"Mapped {len(mapping_pairs)} tool(s) to {len(capabilities_mapped)} capability(ies)"
    }


@router.post("/{provider_id}/enable", response_model=dict)
async def enable_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Enable a provider.

    Once enabled, the provider's capabilities become available for
    skill execution (subject to health checks).
    """
    provider = db.query(CapabilityProvider).filter_by(id=provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider.enabled = True
    db.commit()

    return {
        "provider_id": provider_id,
        "provider_key": provider.provider_key,
        "enabled": True,
        "message": "Provider enabled"
    }


@router.post("/{provider_id}/disable", response_model=dict)
async def disable_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Disable a provider.

    Disabled providers' capabilities become unavailable, which will cause
    dependent skills to become 'blocked' in the UI.
    """
    provider = db.query(CapabilityProvider).filter_by(id=provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider.enabled = False
    db.commit()

    return {
        "provider_id": provider_id,
        "provider_key": provider.provider_key,
        "enabled": False,
        "message": "Provider disabled"
    }


@router.delete("/{provider_id}", response_model=dict)
async def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete a provider.

    Cascade deletes all capability mappings (via database FK constraint).
    """
    provider = db.query(CapabilityProvider).filter_by(id=provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider_key = provider.provider_key
    db.delete(provider)
    db.commit()

    return {
        "provider_key": provider_key,
        "message": "Provider deleted (cascade deleted mappings)"
    }


@router.get("/{provider_id}/discover", response_model=Dict)
async def discover_provider_tools(
    provider_id: int,
    refresh: bool = Query(False, description="Force refresh from MCP server"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Discover tools from a provider.

    For MCP providers:
    - If refresh=False (default): return cached tools from database
    - If refresh=True: fetch fresh tools from MCP server and update database

    For builtin providers:
    - Return tools from existing capability mappings

    Args:
        provider_id: Provider ID
        refresh: If True, fetch fresh data from MCP server (for MCP providers)

    Returns:
        {"tools": [list of tool names]}
    """
    provider = db.execute(
        select(CapabilityProvider).where(CapabilityProvider.id == provider_id)
    ).scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    tools = []

    if provider.provider_type == "mcp":
        from AICrews.database.models.mcp import MCPServer, MCPTool

        server_key = provider.provider_key.replace("mcp:", "")
        mcp_server = db.execute(
            select(MCPServer).where(MCPServer.server_key == server_key)
        ).scalar_one_or_none()

        if not mcp_server:
            # Fallback: if server not found in registry but we have a URL from provider
            # we can try to discover directly (transient discovery)
            if provider.url:
                try:
                    from AICrews.infrastructure.mcp import MCPDiscoveryClient
                    client = MCPDiscoveryClient(server_url=provider.url, timeout=5)
                    # Use a short timeout for transient discovery
                    fresh_tools = await client.list_tools()
                    return {"tools": [t.get("name") for t in fresh_tools if t.get("name")]}
                except Exception as e:
                    logger.warning(f"Fallback discovery failed for {server_key} at {provider.url}: {e}")
                    return {"tools": [], "error": f"Discovery failed: {str(e)}"}

            return {"tools": []}

        if refresh:
            # Force refresh: connect to MCP server and update tools
            try:
                from AICrews.infrastructure.mcp import MCPDiscoveryClient
                from AICrews.services.tool_diff_service import get_tool_diff_service

                client = MCPDiscoveryClient(server_url=mcp_server.url, timeout=10)
                fresh_tools = await client.list_tools()

                # Apply incremental update with field-level diff
                diff_service = get_tool_diff_service(db)
                stats = diff_service.apply_incremental_update(
                    server_id=mcp_server.id,
                    fresh_tools=fresh_tools
                )

                logger.info(
                    f"Tool discovery for {server_key}: "
                    f"created={stats['created']}, updated={stats['updated']}, "
                    f"deleted={stats['deleted']}, unchanged={stats['unchanged']}"
                )
            except Exception as e:
                logger.warning(f"Failed to refresh MCP tools for {server_key}: {e}")

        # Return tools from database (either cached or just refreshed)
        mcp_tools = db.execute(
            select(MCPTool.tool_name)
            .where(MCPTool.server_id == mcp_server.id)
            .order_by(MCPTool.tool_name)
        ).scalars().all()
        tools = list(mcp_tools)

    elif provider.provider_type.startswith("builtin"):
        # Return known builtin tool names from existing mappings
        mappings = db.execute(
            select(ProviderCapabilityMapping.raw_tool_name)
            .where(ProviderCapabilityMapping.provider_id == provider_id)
        ).scalars().all()
        tools = [t for t in mappings if t]

    return {"tools": tools}

@router.post("/{provider_id}/healthcheck", response_model=Dict)
async def healthcheck_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Run healthcheck on provider and update status.

    For MCP providers: Attempts to list tools as healthcheck.
    For builtin providers: Always returns healthy.

    Returns:
        {"healthy": bool, "latency_ms": int, "error": str | null}
    """
    import time
    import asyncio

    provider = db.execute(
        select(CapabilityProvider).where(CapabilityProvider.id == provider_id)
    ).scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    start_time = time.time()
    healthy = False
    error = None

    try:
        if provider.provider_type == "mcp":
            from AICrews.infrastructure.mcp import MCPDiscoveryClient

            # Get URL from provider or MCPServer
            url = provider.url
            if not url:
                server_key = provider.provider_key.replace("mcp:", "")
                from AICrews.database.models.mcp import MCPServer
                mcp_server = db.execute(
                    select(MCPServer).where(MCPServer.server_key == server_key)
                ).scalar_one_or_none()
                url = mcp_server.url if mcp_server else None

            if url:
                client = MCPDiscoveryClient(server_url=url, timeout=10)
                tools = await asyncio.wait_for(client.list_tools(), timeout=10.0)
                healthy = len(tools) > 0
            else:
                error = "No URL configured"
        elif provider.provider_type.startswith("builtin"):
            # Builtin providers: check for credentials based on connection_schema
            from AICrews.services.provider_credential_service import get_provider_credential_service
            cred_service = get_provider_credential_service(db)

            # Check if credentials are configured (uses connection_schema.requires_env)
            cred_status = cred_service.get_credential_status_for_provider(current_user.id, provider)

            if cred_status["requires_credential"]:
                # Provider requires user credentials
                if cred_status["uses_env_var"]:
                    # Env var is set, provider is healthy
                    healthy = True
                elif cred_status["has_credential"] and cred_status["is_verified"]:
                    # User has valid verified credential
                    healthy = True
                else:
                    error = "API key not configured or not verified"
            else:
                # No credentials required (or env var is set)
                healthy = True
        else:
            healthy = True

    except asyncio.TimeoutError:
        error = "Healthcheck timed out after 10s"
    except Exception as e:
        error = str(e)

    latency_ms = int((time.time() - start_time) * 1000)

    # Update provider status
    provider.healthy = healthy
    provider.last_health_check = datetime.now()
    db.commit()

    # Record healthcheck log for observability
    from AICrews.services.health_metrics_service import get_health_metrics_service
    health_service = get_health_metrics_service(db)

    try:
        health_service.record_healthcheck(
            provider_id=provider_id,
            success=healthy,
            latency_ms=latency_ms,
            error=error
        )
    except Exception as log_error:
        logger.warning(f"Failed to record healthcheck log: {log_error}")

    # Fetch 24h aggregated metrics
    metrics_24h = {}
    try:
        recent_metrics = health_service.get_provider_metrics(provider_id, days=1)
        if recent_metrics:
            latest = recent_metrics[0]
            metrics_24h = {
                "error_rate": latest.error_rate,
                "reliability_score": latest.reliability_score,
                "latency_p50": latest.latency_p50,
                "latency_p95": latest.latency_p95,
                "latency_p99": latest.latency_p99,
                "check_count": latest.check_count
            }
    except Exception as metrics_error:
        logger.warning(f"Failed to fetch 24h metrics: {metrics_error}")

    # Get credential status for builtin providers
    credential_status = None
    if provider.provider_type.startswith("builtin"):
        try:
            from AICrews.services.provider_credential_service import get_provider_credential_service
            cred_service = get_provider_credential_service(db)
            credential_status = cred_service.get_credential_status_for_provider(current_user.id, provider)
        except Exception as cred_error:
            logger.warning(f"Failed to get credential status: {cred_error}")

    return {
        "provider_id": provider_id,
        "healthy": healthy,
        "latency_ms": latency_ms,
        "error": error,
        "last_health_check": provider.last_health_check.isoformat(),
        "metrics_24h": metrics_24h,
        "credential_status": credential_status,  # NEW: Credential info for builtin providers
    }


# ============================================================================
# API Key Management Endpoints
# ============================================================================

@router.get("/{provider_id}/credential-status", response_model=CredentialStatusResponse)
async def get_credential_status(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get credential status for a provider.

    Returns whether the user has stored credentials and their verification status.
    """
    provider = db.execute(
        select(CapabilityProvider).where(CapabilityProvider.id == provider_id)
    ).scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    from AICrews.services.provider_credential_service import get_provider_credential_service
    cred_service = get_provider_credential_service(db)

    status = cred_service.get_credential_status_for_provider(current_user.id, provider)

    return CredentialStatusResponse(
        provider_id=provider_id,
        provider_key=provider.provider_key,
        has_credential=status["has_credential"],
        is_verified=status["is_verified"],
        requires_credential=status["requires_credential"],
        uses_env_var=status["uses_env_var"],
    )


@router.post("/{provider_id}/verify-api-key", response_model=VerifyApiKeyResponse)
async def verify_api_key(
    provider_id: int,
    request: SaveApiKeyRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Validate an API key without saving it.

    Use this to test an API key before saving. Returns validation result
    with latency information.
    """
    provider = db.execute(
        select(CapabilityProvider).where(CapabilityProvider.id == provider_id)
    ).scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    from AICrews.services.provider_credential_service import get_provider_credential_service
    cred_service = get_provider_credential_service(db)

    result = cred_service.validate_api_key(current_user.id, provider.provider_key, request.api_key)

    return VerifyApiKeyResponse(
        valid=result["valid"],
        message=result["message"],
        latency_ms=result["latency_ms"],
    )


@router.post("/{provider_id}/save-api-key", response_model=dict)
async def save_api_key(
    provider_id: int,
    request: SaveApiKeyRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Save API key for a provider.

    The key is encrypted before storage and automatically validated.
    If validation succeeds, the key is marked as verified and ready for use.

    Returns the credential status after saving and validation.
    """
    provider = db.execute(
        select(CapabilityProvider).where(CapabilityProvider.id == provider_id)
    ).scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    from AICrews.services.provider_credential_service import get_provider_credential_service
    cred_service = get_provider_credential_service(db)

    # Save the credential
    cred_service.save_api_key(current_user.id, provider.provider_key, request.api_key)

    # Validate the API key
    validation_result = cred_service.validate_api_key(
        current_user.id, provider.provider_key, request.api_key
    )

    # If validation succeeded, mark as verified
    if validation_result["valid"]:
        cred_service.mark_verified(current_user.id, provider.provider_key)

    # Get updated status
    status = cred_service.get_credential_status_for_provider(current_user.id, provider)

    message = (
        "API key saved and verified successfully."
        if validation_result["valid"]
        else f"API key saved but verification failed: {validation_result['message']}"
    )

    return {
        "provider_id": provider_id,
        "provider_key": provider.provider_key,
        "message": message,
        "has_credential": status["has_credential"],
        "is_verified": status["is_verified"],
        "validation_latency_ms": validation_result.get("latency_ms", 0),
    }


@router.delete("/{provider_id}/api-key", response_model=dict)
async def delete_api_key(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete stored API key for a provider.

    This does not affect environment variable-based credentials.
    """
    provider = db.execute(
        select(CapabilityProvider).where(CapabilityProvider.id == provider_id)
    ).scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    from AICrews.services.provider_credential_service import get_provider_credential_service
    cred_service = get_provider_credential_service(db)

    deleted = cred_service.delete_credential(current_user.id, provider.provider_key)

    return {
        "provider_id": provider_id,
        "provider_key": provider.provider_key,
        "deleted": deleted,
        "message": "API key deleted" if deleted else "No credential found to delete"
    }


# ============================================================================
# Multi-Credential Management Endpoints (for MCP providers like OpenBB)
# ============================================================================

class CredentialRequirement(BaseModel):
    """Credential requirement definition."""
    key: str
    display_name: str
    description: str
    required: bool
    get_key_url: str
    has_credential: bool
    is_verified: bool
    uses_env_var: bool


class AllCredentialsResponse(BaseModel):
    """Response with all credential statuses for a provider."""
    provider_id: int
    provider_key: str
    credentials: List[CredentialRequirement]


class SaveCredentialRequest(BaseModel):
    """Request to save a specific credential."""
    api_key: str


@router.get("/{provider_id}/credentials", response_model=AllCredentialsResponse)
async def get_all_credentials(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all credential requirements and statuses for a provider.

    Returns credential definitions from connection_schema.credentials along with
    current status (configured, verified, using env var).

    This endpoint supports providers with multiple credentials (e.g., mcp:openbb
    which needs Polygon, FMP, and Benzinga API keys).
    """
    provider = db.execute(
        select(CapabilityProvider).where(CapabilityProvider.id == provider_id)
    ).scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    from AICrews.services.provider_credential_service import get_provider_credential_service
    cred_service = get_provider_credential_service(db)

    statuses = cred_service.get_all_credential_statuses(current_user.id, provider)

    return AllCredentialsResponse(
        provider_id=provider_id,
        provider_key=provider.provider_key,
        credentials=[
            CredentialRequirement(
                key=s["key"],
                display_name=s["display_name"],
                description=s["description"],
                required=s["required"],
                get_key_url=s["get_key_url"],
                has_credential=s["has_credential"],
                is_verified=s["is_verified"],
                uses_env_var=s["uses_env_var"],
            )
            for s in statuses
        ]
    )


@router.post("/{provider_id}/credentials/{credential_type}", response_model=dict)
async def save_credential(
    provider_id: int,
    credential_type: str,
    request: SaveCredentialRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Save a specific credential for a provider.

    Args:
        provider_id: Provider ID
        credential_type: Credential key (e.g., "polygon_api_key", "fmp_api_key")
        request: Contains the API key to save

    The key is encrypted before storage. For MCP providers, credentials are
    stored but not validated (validation would require provider-specific logic).
    """
    provider = db.execute(
        select(CapabilityProvider).where(CapabilityProvider.id == provider_id)
    ).scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Validate credential_type against connection_schema
    from AICrews.services.provider_credential_service import get_provider_credential_service
    cred_service = get_provider_credential_service(db)

    requirements = cred_service.get_credential_requirements(provider)
    valid_keys = [r["key"] for r in requirements]

    if requirements and credential_type not in valid_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid credential type '{credential_type}'. Valid types: {valid_keys}"
        )

    # Save the credential with specific type
    credential = cred_service.save_api_key(
        user_id=current_user.id,
        provider_key=provider.provider_key,
        api_key=request.api_key,
        credential_type=credential_type
    )

    # For MCP providers, auto-mark as verified (no validation endpoint available)
    # For builtin providers, validation is done separately
    if provider.provider_type == "mcp":
        cred_service.mark_verified(current_user.id, provider.provider_key, credential_type)

    return {
        "provider_id": provider_id,
        "provider_key": provider.provider_key,
        "credential_type": credential_type,
        "has_credential": True,
        "is_verified": provider.provider_type == "mcp",  # Auto-verified for MCP
        "message": f"Credential '{credential_type}' saved successfully"
    }


@router.delete("/{provider_id}/credentials/{credential_type}", response_model=dict)
async def delete_credential(
    provider_id: int,
    credential_type: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete a specific credential for a provider.

    Args:
        provider_id: Provider ID
        credential_type: Credential key to delete (e.g., "polygon_api_key")
    """
    provider = db.execute(
        select(CapabilityProvider).where(CapabilityProvider.id == provider_id)
    ).scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    from AICrews.services.provider_credential_service import get_provider_credential_service
    cred_service = get_provider_credential_service(db)

    deleted = cred_service.delete_credential(
        user_id=current_user.id,
        provider_key=provider.provider_key,
        credential_type=credential_type
    )

    return {
        "provider_id": provider_id,
        "provider_key": provider.provider_key,
        "credential_type": credential_type,
        "deleted": deleted,
        "message": f"Credential '{credential_type}' deleted" if deleted else "No credential found to delete"
    }


# ============================================================================
# Capability Provider Priority Endpoints
# ============================================================================

class CapabilityProviderInfo(BaseModel):
    """Provider info for a specific capability."""
    provider_id: int
    provider_key: str
    provider_type: str
    priority: int
    healthy: bool
    enabled: bool
    raw_tool_name: Optional[str] = None


class CapabilityProvidersResponse(BaseModel):
    """Response with all providers for a capability."""
    capability_id: str
    providers: List[CapabilityProviderInfo]


class UpdatePriorityRequest(BaseModel):
    """Request to update provider priorities for a capability."""
    priorities: List[Dict[str, int]]  # [{"provider_id": 1, "priority": 90}, ...]


@router.get("/capabilities/{capability_id}/providers", response_model=CapabilityProvidersResponse)
async def get_capability_providers(
    capability_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all providers that implement a specific capability, sorted by priority.

    Returns providers with their priority, health status, and the raw tool name
    they use to implement this capability.

    Args:
        capability_id: Capability ID from taxonomy (e.g., "equity_quote")

    Returns:
        List of providers sorted by priority (highest first)
    """
    # Validate capability_id
    if capability_id not in ALL_CAPABILITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid capability_id: {capability_id}. Must be from taxonomy."
        )

    # Query mappings with provider info, sorted by priority DESC
    mappings = db.execute(
        select(ProviderCapabilityMapping, CapabilityProvider)
        .join(CapabilityProvider, ProviderCapabilityMapping.provider_id == CapabilityProvider.id)
        .where(ProviderCapabilityMapping.capability_id == capability_id)
        .where(CapabilityProvider.enabled == True)  # Only enabled providers
        .order_by(ProviderCapabilityMapping.priority.desc())
    ).all()

    providers = [
        CapabilityProviderInfo(
            provider_id=provider.id,
            provider_key=provider.provider_key,
            provider_type=provider.provider_type,
            priority=mapping.priority,
            healthy=provider.healthy,
            enabled=provider.enabled,
            raw_tool_name=mapping.raw_tool_name,
        )
        for mapping, provider in mappings
    ]

    return CapabilityProvidersResponse(
        capability_id=capability_id,
        providers=providers
    )


@router.put("/capabilities/{capability_id}/priorities", response_model=dict)
async def update_capability_priorities(
    capability_id: str,
    request: UpdatePriorityRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update provider priorities for a specific capability.

    Allows users to reorder which providers are tried first when resolving
    a capability. Higher priority = tried first.

    Args:
        capability_id: Capability ID from taxonomy
        request: List of {provider_id, priority} pairs

    Example request body:
        {
            "priorities": [
                {"provider_id": 1, "priority": 90},
                {"provider_id": 2, "priority": 80},
                {"provider_id": 3, "priority": 70}
            ]
        }
    """
    # Validate capability_id
    if capability_id not in ALL_CAPABILITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid capability_id: {capability_id}. Must be from taxonomy."
        )

    updated_count = 0
    for item in request.priorities:
        provider_id = item.get("provider_id")
        priority = item.get("priority")

        if provider_id is None or priority is None:
            continue

        # Clamp priority to 0-100 range
        priority = max(0, min(100, priority))

        # Update the mapping
        result = db.execute(
            select(ProviderCapabilityMapping)
            .where(ProviderCapabilityMapping.provider_id == provider_id)
            .where(ProviderCapabilityMapping.capability_id == capability_id)
        ).scalar_one_or_none()

        if result:
            result.priority = priority
            updated_count += 1

    db.commit()

    return {
        "capability_id": capability_id,
        "updated_count": updated_count,
        "message": f"Updated priorities for {updated_count} provider(s)"
    }

