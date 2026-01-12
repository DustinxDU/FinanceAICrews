"""Community Edition entitlements module.

Provides self-hosted detection and tier information for the community edition
of the FinanceAI platform.
"""

import os


def is_self_hosted() -> bool:
    """Detect if running in self-hosted/community edition mode.

    Self-hosted mode is determined by FAIC_SELF_HOSTED environment variable
    set to 'true' (case insensitive).

    Returns:
        bool: True if running in self-hosted mode, False otherwise (SaaS mode).
    """
    return os.environ.get("FAIC_SELF_HOSTED", "").lower() == "true"


def get_community_tier_info() -> tuple[str, str, bool, str]:
    """Get tier information for community edition.

    Community edition provides Pro-tier functionality without SaaS billing.

    Returns:
        tuple: (tier, tier_type, is_saas, source)
            - tier: 'pro'
            - tier_type: 'pro'
            - is_saas: False
            - source: 'community_edition'
    """
    return ("pro", "pro", False, "community_edition")
