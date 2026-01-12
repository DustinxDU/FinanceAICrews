"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw, Trash2 } from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import { useToast } from "@/lib/toast";
import type {
  LLMPolicyProvider,
  LLMPolicyStatus,
  LLMUserByokProfileResponse,
  LLMUserByokProfileUpdate,
  LLMRoutingOverrideResponse,
  LLMVirtualKeyResponse,
} from "@/lib/types";

const TIERS = ["fast", "balanced", "best"] as const;
const ROUTING_MODES = ["AUTO", "SYSTEM_ONLY", "USER_BYOK_ONLY"] as const;

type Tier = typeof TIERS[number];

type ByokFormState = Record<Tier, {
  provider: string;
  model: string;
  api_key: string;
  enabled: boolean;
}>;

const emptyFormState: ByokFormState = {
  fast: { provider: "", model: "", api_key: "", enabled: false },
  balanced: { provider: "", model: "", api_key: "", enabled: false },
  best: { provider: "", model: "", api_key: "", enabled: false },
};

export function LlmPolicyTab() {
  const t = useTranslations("settings");
  const { error, success } = useToast();
  const [status, setStatus] = useState<LLMPolicyStatus | null>(null);
  const [providers, setProviders] = useState<LLMPolicyProvider[]>([]);
  const [profiles, setProfiles] = useState<LLMUserByokProfileResponse[]>([]);
  const [routingOverrides, setRoutingOverrides] = useState<LLMRoutingOverrideResponse[]>([]);
  const [virtualKeys, setVirtualKeys] = useState<LLMVirtualKeyResponse[]>([]);
  const [forms, setForms] = useState<ByokFormState>(emptyFormState);
  const [isLoading, setIsLoading] = useState(true);
  const [savingTier, setSavingTier] = useState<Tier | null>(null);
  const [testingTier, setTestingTier] = useState<Tier | null>(null);
  const [savingOverride, setSavingOverride] = useState(false);
  const [deletingOverride, setDeletingOverride] = useState<number | null>(null);
  const [overrideScope, setOverrideScope] = useState("");
  const [overrideMode, setOverrideMode] = useState<(typeof ROUTING_MODES)[number]>("AUTO");

  const profilesByTier = useMemo(() => {
    const map: Partial<Record<Tier, LLMUserByokProfileResponse>> = {};
    profiles.forEach((profile) => {
      if (TIERS.includes(profile.tier as Tier)) {
        map[profile.tier as Tier] = profile;
      }
    });
    return map;
  }, [profiles]);

  useEffect(() => {
    const nextState = { ...emptyFormState };
    TIERS.forEach((tier) => {
      const profile = profilesByTier[tier];
      if (profile) {
        nextState[tier] = {
          provider: profile.provider,
          model: profile.model,
          api_key: "",
          enabled: profile.enabled,
        };
      }
    });
    setForms(nextState);
  }, [profilesByTier]);

  useEffect(() => {
    void loadAll();
  }, []);

  async function loadAll() {
    setIsLoading(true);
    try {
      const [statusResp, providersResp, profilesResp, overridesResp, keysResp] = await Promise.all([
        apiClient.getLlmPolicyStatus(),
        apiClient.listLlmPolicyProviders(),
        apiClient.listByokProfiles(),
        apiClient.listRoutingOverrides(),
        apiClient.listVirtualKeys(),
      ]);
      setStatus(statusResp);
      setProviders(providersResp);
      setProfiles(profilesResp);
      setRoutingOverrides(overridesResp);
      setVirtualKeys(keysResp);
    } catch (err: any) {
      console.error(t('failed') + " to load LLM policy data:", err);
      error("LLM Policy", err?.message || t('failed') + " to load LLM policy settings");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSaveTier(tier: Tier) {
    const form = forms[tier];
    if (!form.provider.trim() || !form.model.trim()) {
      error("BYOK Profile", "Provider and model are required");
      return;
    }

    const payload: LLMUserByokProfileUpdate = {
      provider: form.provider.trim(),
      model: form.model.trim(),
      enabled: form.enabled,
    };
    if (form.api_key && form.api_key.trim()) {
      payload.api_key = form.api_key.trim();
    }

    try {
      setSavingTier(tier);
      await apiClient.upsertByokProfileByTier(tier, payload);
      const refreshed = await apiClient.listByokProfiles();
      setProfiles(refreshed);
      setForms((prev) => ({
        ...prev,
        [tier]: { ...prev[tier], api_key: "" },
      }));
      success("BYOK Profile", `Saved ${tier} profile`);
    } catch (err: any) {
      console.error(t('failed') + " to save BYOK profile:", err);
      error("BYOK Profile", err?.message || t('failed') + " to save profile");
    } finally {
      setSavingTier(null);
    }
  }

  async function handleTestTier(tier: Tier) {
    try {
      setTestingTier(tier);
      await apiClient.testByokProfile(tier);
      const refreshed = await apiClient.listByokProfiles();
      setProfiles(refreshed);
      success("BYOK Profile", `Tested ${tier} profile`);
    } catch (err: any) {
      console.error(t('failed') + " to test BYOK profile:", err);
      error("BYOK Profile", err?.message || t('failed') + " to test profile");
    } finally {
      setTestingTier(null);
    }
  }

  async function handleCreateOverride() {
    if (!overrideScope.trim()) {
      error("Routing Override", "Scope is required");
      return;
    }

    try {
      setSavingOverride(true);
      await apiClient.upsertRoutingOverride({
        scope: overrideScope.trim(),
        mode: overrideMode,
      });
      const refreshed = await apiClient.listRoutingOverrides();
      setRoutingOverrides(refreshed);
      setOverrideScope("");
      setOverrideMode("AUTO");
      success("Routing Override", "Override saved");
    } catch (err: any) {
      console.error(t('failed') + " to save routing override:", err);
      error("Routing Override", err?.message || t('failed') + " to save override");
    } finally {
      setSavingOverride(false);
    }
  }

  async function handleDeleteOverride(id: number) {
    try {
      setDeletingOverride(id);
      await apiClient.deleteRoutingOverride(id);
      const refreshed = await apiClient.listRoutingOverrides();
      setRoutingOverrides(refreshed);
      success("Routing Override", "Override removed");
    } catch (err: any) {
      console.error(t('failed') + " to delete routing override:", err);
      error("Routing Override", err?.message || t('failed') + " to delete override");
    } finally {
      setDeletingOverride(null);
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h2 className="text-xl font-bold mb-1">LLM Policy</h2>
        <p className="text-sm text-[var(--text-secondary)]">
          {t('configure')} routing, BYOK profiles, and virtual key visibility.
        </p>
      </div>

      <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">{t('routerStatus')}</h3>
          <span className={`text-xs px-2 py-0.5 rounded-full border ${status?.enabled ? "bg-green-900/20 text-green-400 border-green-900/50" : "bg-zinc-900/20 text-zinc-300 border-zinc-800"}`}>
            {status?.enabled ? "Enabled" : "Disabled"}
          </span>
        </div>
        <p className="text-sm text-[var(--text-secondary)]">
          {status?.message || "Router status unavailable"}
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">BYOK Profiles</h3>
        </div>

        {TIERS.map((tier) => {
          const profile = profilesByTier[tier];
          const form = forms[tier];
          return (
            <div key={tier} className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium capitalize">{tier} tier</div>
                  <div className="text-xs text-[var(--text-secondary)]">
                    {profile?.key_masked ? `Key: ${profile.key_masked}` : "No key stored"}
                  </div>
                </div>
                <label className="flex items-center gap-2 text-xs">
                  <input
                    type="checkbox"
                    checked={form.enabled}
                    onChange={(event) =>
                      setForms((prev) => ({
                        ...prev,
                        [tier]: { ...prev[tier], enabled: event.target.checked },
                      }))
                    }
                  />
                  Enabled
                </label>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-[var(--text-secondary)]">Provider</label>
                  <select
                    value={form.provider}
                    onChange={(event) =>
                      setForms((prev) => ({
                        ...prev,
                        [tier]: { ...prev[tier], provider: event.target.value },
                      }))
                    }
                    className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm"
                  >
                    <option value="">{t('selectProvider')}</option>
                    {providers.map((provider) => (
                      <option key={provider.provider_key} value={provider.provider_key}>
                        {provider.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[var(--text-secondary)]">Model</label>
                  <input
                    value={form.model}
                    onChange={(event) =>
                      setForms((prev) => ({
                        ...prev,
                        [tier]: { ...prev[tier], model: event.target.value },
                      }))
                    }
                    className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm"
                    placeholder="model name"
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--text-secondary)]">API Key</label>
                  <input
                    type="password"
                    value={form.api_key}
                    onChange={(event) =>
                      setForms((prev) => ({
                        ...prev,
                        [tier]: { ...prev[tier], api_key: event.target.value },
                      }))
                    }
                    className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm"
                    placeholder="Enter new key to update"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => handleSaveTier(tier)}
                  disabled={savingTier === tier}
                  className="px-3 py-1.5 bg-[var(--accent-blue)] text-white rounded text-xs font-medium hover:bg-blue-600 disabled:opacity-50"
                >
                  {savingTier === tier ? t('saving') : t('save')}
                </button>
                <button
                  onClick={() => handleTestTier(tier)}
                  disabled={testingTier === tier}
                  className="px-3 py-1.5 border border-[var(--border-color)] rounded text-xs font-medium hover:bg-[var(--bg-panel)] disabled:opacity-50"
                >
                  {testingTier === tier ? "Testing..." : "Test"}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Routing Overrides</h3>
          <button
            onClick={loadAll}
            className="text-xs flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            {t('refresh')}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            value={overrideScope}
            onChange={(event) => setOverrideScope(event.target.value)}
            className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm"
            placeholder="scope (e.g. crew_router)"
          />
          <select
            value={overrideMode}
            onChange={(event) => setOverrideMode(event.target.value as typeof ROUTING_MODES[number])}
            className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm"
          >
            {ROUTING_MODES.map((mode) => (
              <option key={mode} value={mode}>{mode}</option>
            ))}
          </select>
          <button
            onClick={handleCreateOverride}
            disabled={savingOverride}
            className="px-3 py-2 bg-[var(--accent-blue)] text-white rounded text-xs font-medium hover:bg-blue-600 disabled:opacity-50"
          >
            {savingOverride ? t('saving') : t('saveOverride')}
          </button>
        </div>

        <div className="space-y-2">
          {routingOverrides.length === 0 && (
            <div className="text-xs text-[var(--text-secondary)]">{t('noOverridesConfigured')}</div>
          )}
          {routingOverrides.map((override) => (
            <div key={override.id} className="flex items-center justify-between text-sm border border-[var(--border-color)] rounded-lg px-3 py-2">
              <div>
                <div className="font-medium">{override.scope}</div>
                <div className="text-xs text-[var(--text-secondary)]">{override.mode}</div>
              </div>
              <button
                onClick={() => handleDeleteOverride(override.id)}
                disabled={deletingOverride === override.id}
                className="p-2 text-[var(--text-secondary)] hover:text-red-400 hover:bg-[var(--bg-panel)] rounded disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg space-y-3">
        <h3 className="font-semibold">Virtual Keys</h3>
        {virtualKeys.length === 0 ? (
          <div className="text-xs text-[var(--text-secondary)]">{t('noVirtualKeysAvailable')}</div>
        ) : (
          <div className="space-y-2">
            {virtualKeys.map((key) => (
              <div key={key.id} className="text-sm border border-[var(--border-color)] rounded-lg px-3 py-2">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{key.key_type}</div>
                    <div className="text-xs text-[var(--text-secondary)]">Status: {key.status}</div>
                  </div>
                  <div className="text-xs text-[var(--text-secondary)]">{key.allowed_models.join(", ")}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
