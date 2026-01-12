"use client";

import React, { useEffect, useState } from "react";
import { Loader2, RefreshCw, CheckCircle, XCircle, AlertCircle, Key } from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import { useToast } from "@/lib/toast";

interface ProviderSummary {
  config_id: number;
  provider_key: string;
  provider_name: string;
  is_validated: boolean;
  model_count: number;
  endpoints?: string[];
}

interface ModelSummary {
  model_config_id: number;
  model_key: string;
  model_name: string;
  context_length?: number;
  volcengine_endpoint_id?: string;
}

interface AgentModelConfig {
  scenario: string;
  scenario_name: string;
  scenario_description: string;
  scenario_icon: string;
  provider_config_id?: number;
  provider_name?: string;
  model_config_id?: number;
  model_name?: string;
  volcengine_endpoint?: string;
  enabled: boolean;
  last_tested_at?: string;
  last_test_status?: string;
  last_test_message?: string;
}

interface AgentModelsResponse {
  use_own_llm_keys: boolean;
  scenarios: AgentModelConfig[];
  available_providers: ProviderSummary[];
}

// Form state for each scenario
interface ScenarioFormState {
  provider_config_id: number | null;
  model_config_id: number | null;
  volcengine_endpoint: string;
}

export function AgentModelsTab() {
  const t = useTranslations("settings");
  const { error, success } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [useOwnLlmKeys, setUseOwnLlmKeys] = useState(false);
  const [isTogglingByok, setIsTogglingByok] = useState(false);
  const [scenarios, setScenarios] = useState<AgentModelConfig[]>([]);
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [forms, setForms] = useState<Record<string, ScenarioFormState>>({});
  const [models, setModels] = useState<Record<number, ModelSummary[]>>({});
  const [savingScenario, setSavingScenario] = useState<string | null>(null);
  const [loadingModels, setLoadingModels] = useState<number | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setIsLoading(true);
    try {
      const response = await apiClient.getAgentModels();
      setUseOwnLlmKeys(response.use_own_llm_keys);
      setScenarios(response.scenarios);
      setProviders(response.available_providers);

      // Initialize form state from scenarios
      const initialForms: Record<string, ScenarioFormState> = {};
      for (const scenario of response.scenarios) {
        initialForms[scenario.scenario] = {
          provider_config_id: scenario.provider_config_id || null,
          model_config_id: scenario.model_config_id || null,
          volcengine_endpoint: scenario.volcengine_endpoint || "",
        };
      }
      setForms(initialForms);

      // Load models for configured providers
      const configuredProviderIds = new Set(
        response.scenarios
          .filter(s => s.provider_config_id)
          .map(s => s.provider_config_id!)
      );
      for (const providerId of configuredProviderIds) {
        await loadModelsForProvider(providerId);
      }
    } catch (err: any) {
      console.error(t('failed') + " to load agent models:", err);
      error(t('agentModels'), err?.message || t('failed') + " to load agent model settings");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleToggleByok(enabled: boolean) {
    setIsTogglingByok(true);
    try {
      const result = await apiClient.toggleByokMode(enabled);
      setUseOwnLlmKeys(result.use_own_llm_keys);
      success(t('agentModels'), result.message);
    } catch (err: any) {
      console.error("Failed to toggle BYOK mode:", err);
      error(t('agentModels'), err?.message || "Failed to toggle BYOK mode");
    } finally {
      setIsTogglingByok(false);
    }
  }

  async function loadModelsForProvider(providerId: number) {
    if (models[providerId]) return; // Already loaded

    setLoadingModels(providerId);
    try {
      const modelList = await apiClient.getAgentModelProviderModels(providerId);
      setModels(prev => ({ ...prev, [providerId]: modelList }));
    } catch (err: any) {
      console.error(t('failed') + " to load models for provider " + providerId + ":", err);
    } finally {
      setLoadingModels(null);
    }
  }

  async function handleProviderChange(scenario: string, providerId: number | null) {
    setForms(prev => ({
      ...prev,
      [scenario]: {
        ...prev[scenario],
        provider_config_id: providerId,
        model_config_id: null, // Reset model when provider changes
        volcengine_endpoint: "",
      },
    }));

    if (providerId && !models[providerId]) {
      await loadModelsForProvider(providerId);
    }
  }

  function handleModelChange(scenario: string, modelConfigId: number | null) {
    const form = forms[scenario];
    const providerId = form?.provider_config_id;

    // For Volcano Engine, auto-fill endpoint from model
    let endpoint = "";
    if (providerId && modelConfigId) {
      const modelList = models[providerId] || [];
      const selectedModel = modelList.find(m => m.model_config_id === modelConfigId);
      if (selectedModel?.volcengine_endpoint_id) {
        endpoint = selectedModel.volcengine_endpoint_id;
      }
    }

    setForms(prev => ({
      ...prev,
      [scenario]: {
        ...prev[scenario],
        model_config_id: modelConfigId,
        volcengine_endpoint: endpoint,
      },
    }));
  }

  async function handleSave(scenario: string) {
    const form = forms[scenario];
    if (!form.provider_config_id || !form.model_config_id) {
      error(t('agentModels'), "Please select a provider and model");
      return;
    }

    setSavingScenario(scenario);
    try {
      // First, save the configuration (with enabled=false initially)
      await apiClient.updateAgentModelScenario(scenario, {
        provider_config_id: form.provider_config_id,
        model_config_id: form.model_config_id,
        volcengine_endpoint: form.volcengine_endpoint || null,
        enabled: false, // Will be enabled after successful test
      });

      // Then test the configuration
      const testResult = await apiClient.testAgentModelScenario(scenario);

      if (testResult.success) {
        // Test passed - enable the configuration
        await apiClient.updateAgentModelScenario(scenario, {
          provider_config_id: form.provider_config_id,
          model_config_id: form.model_config_id,
          volcengine_endpoint: form.volcengine_endpoint || null,
          enabled: true,
        });
        success(t('agentModels'), "Configuration saved and verified successfully");
      } else {
        // Test failed - show error, configuration remains disabled
        error(t('agentModels'), "Test failed: " + testResult.message + ". Configuration not enabled.");
      }

      await loadData(); // Refresh to get updated status
    } catch (err: any) {
      console.error(t('failed') + " to save " + scenario + ":", err);
      error(t('agentModels'), err?.message || t('failed') + " to save " + scenario);
    } finally {
      setSavingScenario(null);
    }
  }

  function getStatusIcon(scenario: AgentModelConfig) {
    if (!scenario.provider_config_id) {
      return <AlertCircle className="w-4 h-4 text-zinc-500" />;
    }
    if (scenario.last_test_status === "pass") {
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    }
    if (scenario.last_test_status === "fail") {
      return <XCircle className="w-4 h-4 text-red-500" />;
    }
    return <AlertCircle className="w-4 h-4 text-yellow-500" />;
  }

  function getStatusText(scenario: AgentModelConfig) {
    if (!scenario.provider_config_id) {
      return "Not configured";
    }
    if (scenario.last_test_status === "pass") {
      const time = scenario.last_tested_at
        ? new Date(scenario.last_tested_at).toLocaleString()
        : "";
      return `Verified ${time}`;
    }
    if (scenario.last_test_status === "fail") {
      return scenario.last_test_message || "Test failed";
    }
    return "Not tested";
  }

  function isVolcengine(providerId: number | null): boolean {
    if (!providerId) return false;
    const provider = providers.find(p => p.config_id === providerId);
    return provider?.provider_key === "volcengine";
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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold mb-1">{t('agentModels')}</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            {t('configure')} which models to use for different agent scenarios.
          </p>
        </div>
        <button
          onClick={loadData}
          className="text-xs flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          {t('refresh')}
        </button>
      </div>

      {/* BYOK Global Toggle */}
      <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
              <Key className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <div className="font-medium">Use Your Own API Keys</div>
              <div className="text-xs text-[var(--text-secondary)]">
                {useOwnLlmKeys
                  ? "Your configured API keys will be used for agent LLM calls"
                  : "Using official system models for agent LLM calls"
                }
              </div>
            </div>
          </div>
          <button
            onClick={() => handleToggleByok(!useOwnLlmKeys)}
            disabled={isTogglingByok}
            className={`
              relative w-12 h-6 rounded-full transition-colors duration-200 ease-in-out
              ${useOwnLlmKeys
                ? 'bg-blue-500'
                : 'bg-zinc-600'
              }
              ${isTogglingByok ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            <span
              className={`
                absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-sm
                transition-transform duration-200 ease-in-out
                ${useOwnLlmKeys ? 'translate-x-6' : 'translate-x-0'}
              `}
            />
          </button>
        </div>
      </div>

      {providers.length === 0 && (
        <div className="p-4 bg-yellow-900/10 border border-yellow-900/30 rounded-lg text-sm text-yellow-200">
          <p>No validated API keys found. Please add and verify your API keys in the <strong>API Keys</strong> tab first.</p>
        </div>
      )}

      {scenarios.map((scenario) => {
        const form = forms[scenario.scenario] || {
          provider_config_id: null,
          model_config_id: null,
          volcengine_endpoint: "",
        };
        const providerModels = form.provider_config_id ? models[form.provider_config_id] || [] : [];
        const showEndpoint = isVolcengine(form.provider_config_id);
        const isDisabled = !useOwnLlmKeys;

        return (
          <div
            key={scenario.scenario}
            className={`p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg space-y-4 ${
              isDisabled ? 'opacity-50' : ''
            }`}
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{scenario.scenario_icon}</span>
                <div>
                  <div className="font-medium">{scenario.scenario_name}</div>
                  <div className="text-xs text-[var(--text-secondary)]">
                    {scenario.scenario_description}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {getStatusIcon(scenario)}
                <span className="text-xs text-[var(--text-secondary)]">
                  {getStatusText(scenario)}
                </span>
              </div>
            </div>

            {/* Form */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Provider Select */}
              <div>
                <label className="text-xs text-[var(--text-secondary)] block mb-1">
                  Provider
                </label>
                <select
                  value={form.provider_config_id || ""}
                  onChange={(e) =>
                    handleProviderChange(
                      scenario.scenario,
                      e.target.value ? parseInt(e.target.value) : null
                    )
                  }
                  disabled={isDisabled}
                  className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm disabled:cursor-not-allowed"
                >
                  <option value="">{t('selectProvider')}</option>
                  {providers.map((provider) => (
                    <option key={provider.config_id} value={provider.config_id}>
                      {provider.provider_name} ({provider.model_count} models)
                    </option>
                  ))}
                </select>
              </div>

              {/* Model Select */}
              <div>
                <label className="text-xs text-[var(--text-secondary)] block mb-1">
                  Model
                </label>
                <select
                  value={form.model_config_id || ""}
                  onChange={(e) =>
                    handleModelChange(
                      scenario.scenario,
                      e.target.value ? parseInt(e.target.value) : null
                    )
                  }
                  disabled={isDisabled || !form.provider_config_id || loadingModels === form.provider_config_id}
                  className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="">
                    {loadingModels === form.provider_config_id
                      ? "Loading models..."
                      : "Select model..."}
                  </option>
                  {providerModels.map((model) => (
                    <option key={model.model_config_id} value={model.model_config_id}>
                      {model.model_name}
                      {model.context_length ? ` (${Math.round(model.context_length / 1000)}K)` : ""}
                    </option>
                  ))}
                </select>
              </div>

              {/* Endpoint (for Volcano Engine) */}
              {showEndpoint && (
                <div>
                  <label className="text-xs text-[var(--text-secondary)] block mb-1">
                    Endpoint
                  </label>
                  <input
                    type="text"
                    value={form.volcengine_endpoint}
                    onChange={(e) =>
                      setForms((prev) => ({
                        ...prev,
                        [scenario.scenario]: {
                          ...prev[scenario.scenario],
                          volcengine_endpoint: e.target.value,
                        },
                      }))
                    }
                    placeholder="ep-20250101..."
                    disabled={isDisabled}
                    className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end pt-2">
              <button
                onClick={() => handleSave(scenario.scenario)}
                disabled={isDisabled || savingScenario === scenario.scenario || !form.provider_config_id || !form.model_config_id}
                className="px-4 py-1.5 bg-[var(--accent-blue)] text-white rounded text-sm font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {savingScenario === scenario.scenario ? "Saving & Testing..." : "Save"}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
