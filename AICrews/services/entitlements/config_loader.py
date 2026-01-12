from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from AICrews.schemas.entitlements import ComputingMode, PolicyAction, PolicyScope


class TierLimits(BaseModel):
    max_iterations: int = Field(..., ge=1)
    timeout_seconds: int = Field(..., gt=0)
    max_parallel_tools: int = Field(..., ge=0)

    class Config:
        extra = "forbid"


class ByokConfig(BaseModel):
    allowed: bool

    class Config:
        extra = "forbid"


class TierConfig(BaseModel):
    allowed_actions: List[str]
    allowed_modes: List[ComputingMode]
    default_mode: ComputingMode
    byok: ByokConfig
    limits: TierLimits

    @model_validator(mode="after")
    def validate_actions_and_modes(self) -> "TierConfig":
        validated_actions: List[str] = []
        for action in self.allowed_actions:
            if action == "*":
                validated_actions.append(action)
                continue
            if action not in PolicyAction._value2member_map_:  # type: ignore[attr-defined]
                raise ValueError(f"Unknown policy action '{action}' in entitlements config")
            validated_actions.append(action)
        self.allowed_actions = validated_actions

        if self.default_mode not in self.allowed_modes:
            raise ValueError(f"default_mode {self.default_mode} must be within allowed_modes {self.allowed_modes}")
        return self

    class Config:
        extra = "forbid"


class EntitlementsConfig(BaseModel):
    version: Optional[str] = None
    tiers: Dict[str, TierConfig]
    mode_mappings: Dict[ComputingMode, PolicyScope]
    mode_rates: Dict[ComputingMode, int]

    @model_validator(mode="after")
    def validate_tiers(self) -> "EntitlementsConfig":
        required = {"free", "starter", "pro"}
        actual = set(self.tiers.keys())
        if required - actual:
            raise ValueError(f"Missing tier entries: {sorted(required - actual)}")
        if actual - required:
            raise ValueError(f"Unknown tier entries: {sorted(actual - required)}")
        return self

    @model_validator(mode="after")
    def validate_mode_mappings_and_rates(self) -> "EntitlementsConfig":
        required_modes = {ComputingMode.ECO, ComputingMode.STANDARD, ComputingMode.EXTREME}
        missing = required_modes - set(self.mode_mappings.keys())
        if missing:
            raise ValueError(f"Missing mode_mappings for modes: {sorted(m.value for m in missing)}")
        missing_rates = required_modes - set(self.mode_rates.keys())
        if missing_rates:
            raise ValueError(f"Missing mode_rates for modes: {sorted(m.value for m in missing_rates)}")
        return self

    class Config:
        extra = "forbid"


class EntitlementsConfigLoader:
    def __init__(self, path: str = "config/entitlements.yaml"):
        self._path = path
        self._fingerprint: Optional[str] = None

    @lru_cache(maxsize=1)
    def get(self) -> EntitlementsConfig:
        if not os.path.exists(self._path):
            raise FileNotFoundError(f"Entitlements config not found: {self._path}")

        with open(self._path, "r", encoding="utf-8") as f:
            content = f.read()
        self._fingerprint = hashlib.sha256(content.encode("utf-8")).hexdigest()
        data = yaml.safe_load(content) or {}

        try:
            return EntitlementsConfig.model_validate(data)
        except ValidationError as exc:  # pragma: no cover - covered by tests using ValueError below
            raise ValueError(f"Invalid entitlements config: {exc}") from exc

    def fingerprint(self) -> str:
        """
        Returns a stable fingerprint (sha256) of the current entitlements config file.
        Ensures get() has been called to load content and compute the fingerprint.
        """
        if self._fingerprint is None:
            self.get()
        return self._fingerprint or ""
