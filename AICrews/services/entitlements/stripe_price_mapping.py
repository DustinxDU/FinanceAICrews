from __future__ import annotations

import os
from typing import Dict

import yaml

DEFAULT_MAPPING_PATH = "config/billing/stripe_price_to_tier.yaml"

_CACHE: dict[str, Dict[str, str]] = {}


def load_price_to_tier(path: str = DEFAULT_MAPPING_PATH) -> Dict[str, str]:
    """
    Load Stripe price_id -> tier mapping from YAML with in-memory caching.

    Raises:
        FileNotFoundError: if the mapping file does not exist
        ValueError: if required keys are missing
    """
    resolved_path = os.path.abspath(path)
    if resolved_path in _CACHE:
        return _CACHE[resolved_path]

    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"Stripe price mapping file not found: {resolved_path}")

    with open(resolved_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if "prices" not in data:
        raise ValueError("Stripe price mapping file missing 'prices' section")

    mapping = {str(price_id): str(tier) for price_id, tier in data["prices"].items()}
    _CACHE[resolved_path] = mapping
    return mapping


def map_price_to_tier(price_id: str | None, path: str = DEFAULT_MAPPING_PATH) -> str:
    """Map a Stripe price_id to canonical tier, defaulting to free on unknowns."""
    if not price_id:
        return "free"
    try:
        mapping = load_price_to_tier(path)
    except Exception:
        return "free"
    tier = mapping.get(price_id, "free")
    return tier if tier in {"free", "starter", "pro"} else "free"
