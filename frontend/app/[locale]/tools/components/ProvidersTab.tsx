"use client";

import React, { useState, useEffect } from "react";
import { Plus, RefreshCw, Loader2, Check, X, AlertCircle, Activity, Settings, Key, Database } from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import type { Provider } from "@/types/skills";
import { AddProviderModal } from "./AddProviderModal";
import { CapabilityMappingModal } from "./CapabilityMappingModal";
import { ApiKeyConfigModal } from "./ApiKeyConfigModal";
import { CredentialsModal } from "./CredentialsModal";

// Credential status type for builtin providers (single credential)
interface CredentialStatus {
  has_credential: boolean;
  is_verified: boolean;
  requires_credential: boolean;
  uses_env_var: boolean;
}

export function ProvidersTab() {
  const t = useTranslations("tools");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [toggling, setToggling] = useState<Record<number, boolean>>({});
  const [healthchecking, setHealthchecking] = useState<Record<number, boolean>>({});
  // Credential status cache per provider (for builtin providers)
  const [credentialStatuses, setCredentialStatuses] = useState<Record<number, CredentialStatus>>({});

  const [isAddProviderOpen, setIsAddProviderOpen] = useState(false);
  const [isMappingOpen, setIsMappingOpen] = useState(false);
  const [mappingProviderId, setMappingProviderId] = useState<number | null>(null);
  const [mappingProviderKey, setMappingProviderKey] = useState("");
  // API Key config modal state (for builtin providers)
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  // Credentials modal state (for MCP providers with multi-credential)
  const [isCredentialsModalOpen, setIsCredentialsModalOpen] = useState(false);

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const data = await apiClient.listProviders();
      setProviders(data);
    } catch (error) {
      console.error("Failed to load providers:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleProvider = async (providerId: number, currentlyEnabled: boolean) => {
    try {
      setToggling((prev) => ({ ...prev, [providerId]: true }));

      if (currentlyEnabled) {
        await apiClient.disableProvider(providerId);
      } else {
        await apiClient.enableProvider(providerId);
      }

      setProviders((prev) =>
        prev.map((p) =>
          p.id === providerId ? { ...p, enabled: !currentlyEnabled } : p
        )
      );

      if (selectedProvider?.id === providerId) {
        setSelectedProvider((prev) =>
          prev ? { ...prev, enabled: !currentlyEnabled } : null
        );
      }
    } catch (error) {
      console.error("Failed to toggle provider:", error);
      alert("Failed to toggle provider status");
    } finally {
      setToggling((prev) => ({ ...prev, [providerId]: false }));
    }
  };

  const handleProviderCreated = (providerId: number) => {
    loadProviders();
    const provider = providers.find((p) => p.id === providerId);
    if (provider) {
      setMappingProviderId(providerId);
      setMappingProviderKey(provider.provider_key);
      setIsMappingOpen(true);
    }
  };

  const handleOpenMapping = (provider: Provider) => {
    setMappingProviderId(provider.id);
    setMappingProviderKey(provider.provider_key);
    setIsMappingOpen(true);
  };

  const handleMappingSuccess = () => {
    loadProviders();
  };

  const handleDeleteProvider = async (providerId: number) => {
    if (!confirm("Are you sure you want to delete this provider?")) {
      return;
    }

    try {
      await apiClient.deleteProvider(providerId);
      setProviders((prev) => prev.filter((p) => p.id !== providerId));
      if (selectedProvider?.id === providerId) {
        setSelectedProvider(null);
      }
    } catch (error) {
      console.error("Failed to delete provider:", error);
      alert("Failed to delete provider");
    }
  };

  const handleHealthcheck = async (providerId: number) => {
    try {
      setHealthchecking((prev) => ({ ...prev, [providerId]: true }));
      const result = await apiClient.healthcheckProvider(providerId);

      // Update credential status if returned (for builtin providers)
      if (result.credential_status) {
        setCredentialStatuses((prev) => ({
          ...prev,
          [providerId]: result.credential_status!,
        }));
      }

      if (result.healthy) {
        alert(`✓ Provider is healthy (${result.latency_ms}ms)`);
      } else {
        alert(`✗ Provider unhealthy: ${result.error || 'Unknown error'}`);
      }

      // Refresh provider list to update health status
      await loadProviders();
    } catch (error: any) {
      console.error("Healthcheck failed:", error);
      alert(`Healthcheck failed: ${error.message || 'Unknown error'}`);
    } finally {
      setHealthchecking((prev) => ({ ...prev, [providerId]: false }));
    }
  };

  const getStatusBadge = (provider: Provider) => {
    if (!provider.enabled) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
          <X className="w-3 h-3 mr-1" />
          Disabled
        </span>
      );
    }

    if (provider.healthy) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-900/20 text-green-400 border border-green-900/30">
          <Check className="w-3 h-3 mr-1" />
          Healthy
        </span>
      );
    }

    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-900/20 text-red-400 border border-red-900/30">
        <AlertCircle className="w-3 h-3 mr-1" />
        Unhealthy
      </span>
    );
  };

  // Get credential badge for builtin providers that require credentials
  const getCredentialBadge = (provider: Provider) => {
    if (!provider.provider_type.startsWith("builtin")) {
      return null;
    }

    const status = credentialStatuses[provider.id];

    // If we don't have status yet, don't show badge (user needs to run healthcheck first)
    if (!status) {
      return null;
    }

    // If provider doesn't require credentials, don't show badge
    if (!status.requires_credential) {
      return null;
    }

    // Using environment variable
    if (status.uses_env_var) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-900/20 text-green-400 border border-green-900/30">
          <Key className="w-3 h-3 mr-1" />
          Env
        </span>
      );
    }

    // Has verified credential
    if (status.has_credential && status.is_verified) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-900/20 text-green-400 border border-green-900/30">
          <Key className="w-3 h-3 mr-1" />
          {t('configured')}
        </span>
      );
    }

    // Has credential but not verified
    if (status.has_credential && !status.is_verified) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-amber-900/20 text-amber-400 border border-amber-900/30">
          <Key className="w-3 h-3 mr-1" />
          Unverified
        </span>
      );
    }

    // Requires credential but not configured
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-900/20 text-red-400 border border-red-900/30">
        <Key className="w-3 h-3 mr-1" />
        Required
      </span>
    );
  };

  // Handle API key config success (for builtin providers)
  const handleApiKeySuccess = async () => {
    await loadProviders();
    if (selectedProvider) {
      await handleHealthcheck(selectedProvider.id);
    }
  };

  // Handle credentials modal changes (for MCP providers)
  const handleCredentialsChanged = () => {
    loadProviders();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-[var(--text-primary)]">
              Capability Providers
            </h2>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Manage MCP and builtin providers that implement capabilities
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={loadProviders}
              className="px-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-sm hover:text-white text-[var(--text-secondary)] transition-colors flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
            <button
              onClick={() => setIsAddProviderOpen(true)}
              className="px-4 py-2 bg-[var(--accent-blue)] hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              {t('addProvider')}
            </button>
          </div>
        </div>

        {providers.length === 0 ? (
          <div className="text-center py-12 bg-[var(--bg-card)] border border-dashed border-[var(--border-color)] rounded-xl">
            <Activity className="w-12 h-12 mx-auto text-[var(--text-secondary)] mb-4" />
            <h3 className="text-lg font-medium text-[var(--text-primary)] mb-2">
              No providers configured
            </h3>
            <p className="text-sm text-[var(--text-secondary)] mb-4">
              Add an MCP provider to start using external capabilities
            </p>
            <button
              onClick={() => setIsAddProviderOpen(true)}
              className="px-4 py-2 bg-[var(--accent-blue)] hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 mx-auto"
            >
              <Plus className="w-4 h-4" />
              Add Your First Provider
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {providers.map((provider) => (
              <div
                key={provider.id}
                className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-5 hover:border-[var(--text-secondary)] transition-colors cursor-pointer"
                onClick={() => setSelectedProvider(provider)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-[var(--text-primary)] truncate">
                      {provider.provider_key}
                    </h3>
                    <p className="text-xs text-[var(--text-secondary)] mt-0.5 uppercase tracking-wider">
                      {provider.provider_type}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {getStatusBadge(provider)}
                    {getCredentialBadge(provider)}
                  </div>
                </div>

                <div className="mb-3">
                  <span className="text-sm text-[var(--text-secondary)]">
                    <span className="font-medium text-[var(--text-primary)]">
                      {provider.capabilities?.length || 0}
                    </span>{" "}
                    capabilities
                  </span>
                </div>

                {provider.url && (
                  <div className="mb-3 text-xs text-[var(--text-secondary)] truncate">
                    {provider.url}
                  </div>
                )}

                <div className="flex items-center justify-between pt-3 border-t border-[var(--border-color)]">
                  <span className="text-sm text-[var(--text-secondary)]">
                    {provider.enabled ? "Enabled" : "Disabled"}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleProvider(provider.id, provider.enabled);
                    }}
                    disabled={toggling[provider.id]}
                    className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)] focus:ring-offset-2 ${
                      provider.enabled
                        ? "bg-[var(--accent-green)]"
                        : "bg-zinc-700"
                    } ${toggling[provider.id] ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        provider.enabled ? "translate-x-5" : "translate-x-0"
                      }`}
                    />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {selectedProvider && (
          <div className="fixed inset-y-0 right-0 w-96 bg-[var(--bg-panel)] shadow-xl border-l border-[var(--border-color)] overflow-y-auto z-40 animate-in slide-in-from-right duration-300">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                  Provider Details
                </h3>
                <button
                  onClick={() => setSelectedProvider(null)}
                  className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-5">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-1 block">
                    Provider Key
                  </label>
                  <p className="text-[var(--text-primary)] font-mono text-sm bg-[var(--bg-card)] p-2 rounded border border-[var(--border-color)]">
                    {selectedProvider.provider_key}
                  </p>
                </div>

                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-1 block">
                    {t('type')}
                  </label>
                  <p className="text-[var(--text-primary)]">
                    {selectedProvider.provider_type}
                  </p>
                </div>

                {selectedProvider.url && (
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-1 block">
                      URL
                    </label>
                    <p className="text-[var(--text-primary)] text-sm break-all">
                      {selectedProvider.url}
                    </p>
                  </div>
                )}

                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block">
                    {t('status')}
                  </label>
                  <div className="flex items-center gap-2">
                    {getStatusBadge(selectedProvider)}
                    {getCredentialBadge(selectedProvider)}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block">
                    Capabilities
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {selectedProvider.capabilities?.map((cap, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[var(--accent-blue)]/10 text-[var(--accent-blue)] border border-[var(--accent-blue)]/20"
                      >
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-[var(--border-color)] space-y-3">
                {/* Data Source API Keys button for MCP providers */}
                {selectedProvider.provider_type === "mcp" && (
                  <button
                    onClick={() => setIsCredentialsModalOpen(true)}
                    className="w-full px-4 py-2 bg-amber-900/10 border border-amber-900/30 rounded-lg text-sm font-medium text-amber-400 hover:bg-amber-900/20 transition-colors flex items-center justify-center gap-2"
                  >
                    <Database className="w-4 h-4" />
                    Data Source API Keys
                  </button>
                )}

                {/* API Key Configuration for builtin providers that require credentials */}
                {selectedProvider.provider_type.startsWith("builtin") &&
                 credentialStatuses[selectedProvider.id]?.requires_credential && (
                  <button
                    onClick={() => setIsApiKeyModalOpen(true)}
                    className="w-full px-4 py-2 bg-amber-900/10 border border-amber-900/30 rounded-lg text-sm font-medium text-amber-400 hover:bg-amber-900/20 transition-colors flex items-center justify-center gap-2"
                  >
                    <Key className="w-4 h-4" />
                    Configure API Key
                  </button>
                )}

                <button
                  onClick={() => handleOpenMapping(selectedProvider)}
                  className="w-full px-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--bg-panel)] transition-colors flex items-center justify-center gap-2"
                >
                  <Settings className="w-4 h-4" />
                  Map Capabilities
                </button>

                <button
                  onClick={() => handleHealthcheck(selectedProvider.id)}
                  disabled={healthchecking[selectedProvider.id]}
                  className={`w-full px-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--bg-panel)] transition-colors flex items-center justify-center gap-2 ${
                    healthchecking[selectedProvider.id] ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                >
                  {healthchecking[selectedProvider.id] ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Activity className="w-4 h-4" />
                  )}
                  {healthchecking[selectedProvider.id] ? "Checking..." : "Run Healthcheck"}
                </button>

                <button
                  onClick={() => handleDeleteProvider(selectedProvider.id)}
                  className="w-full px-4 py-2 bg-red-900/10 border border-red-900/30 rounded-lg text-sm font-medium text-red-400 hover:bg-red-900/20 transition-colors flex items-center justify-center gap-2"
                >
                  Delete Provider
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <AddProviderModal
        isOpen={isAddProviderOpen}
        onClose={() => setIsAddProviderOpen(false)}
        onSuccess={handleProviderCreated}
      />

      <CapabilityMappingModal
        isOpen={isMappingOpen}
        onClose={() => setIsMappingOpen(false)}
        providerId={mappingProviderId!}
        providerKey={mappingProviderKey}
        onSuccess={handleMappingSuccess}
      />

      {/* Builtin provider single API key modal */}
      {selectedProvider && selectedProvider.provider_type.startsWith("builtin") && (
        <ApiKeyConfigModal
          isOpen={isApiKeyModalOpen}
          onClose={() => setIsApiKeyModalOpen(false)}
          provider={selectedProvider}
          credentialStatus={credentialStatuses[selectedProvider.id]}
          onSuccess={handleApiKeySuccess}
        />
      )}

      {/* MCP provider multi-credential modal */}
      {selectedProvider && selectedProvider.provider_type === "mcp" && (
        <CredentialsModal
          isOpen={isCredentialsModalOpen}
          onClose={() => setIsCredentialsModalOpen(false)}
          provider={selectedProvider}
          onCredentialsChanged={handleCredentialsChanged}
        />
      )}
    </>
  );
}
