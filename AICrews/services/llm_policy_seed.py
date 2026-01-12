"""
LLM System Profile Seeding Service

This module provides idempotent seeding of default LLM system profiles
that map internal scopes to LiteLLM proxy model aliases.

Usage:
    from AICrews.services.llm_policy_seed import ensure_default_system_profiles

    with db.get_session() as session:
        ensure_default_system_profiles(session)
        session.commit()
"""

from sqlalchemy.orm import Session

from AICrews.database.models.llm_policy import LLMSystemProfile


# Default system profiles mapping scope -> proxy_model_name
# These must match the model_list in docker/litellm/config.yaml
DEFAULT_SYSTEM_PROFILES = {
    "copilot": "sys_copilot_v1",
    "agents_fast": "sys_agents_fast_v1",
    "agents_balanced": "sys_agents_balanced_v1",
    "agents_best": "sys_agents_best_v1",
}


def ensure_default_system_profiles(db: Session) -> None:
    """
    Idempotently seed default LLM system profiles.

    Creates missing profiles for each scope defined in DEFAULT_SYSTEM_PROFILES.
    Safe to run multiple times - will skip existing profiles.

    Args:
        db: SQLAlchemy session (caller must commit)
    """
    for scope, proxy_model_name in DEFAULT_SYSTEM_PROFILES.items():
        # Check if profile already exists
        existing = db.query(LLMSystemProfile).filter_by(scope=scope).first()

        if existing is None:
            # Create new profile
            profile = LLMSystemProfile(
                scope=scope,
                proxy_model_name=proxy_model_name,
                enabled=True,
                updated_by="system_seed"
            )
            db.add(profile)

    # Caller is responsible for committing
