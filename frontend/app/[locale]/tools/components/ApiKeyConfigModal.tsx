"use client";

import React, { useState, useEffect } from "react";
import { X, Key, Loader2, Check, AlertCircle, Trash2, ExternalLink } from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import type { Provider } from "@/types/skills";
import type { CredentialRequirement } from "./CredentialsList";

interface ApiKeyConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  provider: Provider;
  // For builtin providers (single credential)
  credentialStatus?: {
    has_credential: boolean;
    is_verified: boolean;
    requires_credential: boolean;
    uses_env_var: boolean;
  };
  // For MCP providers (multi-credential) - pass specific credential info
  credentialRequirement?: CredentialRequirement;
  onSuccess: () => void;
}

// Provider-specific configuration for builtin providers
const PROVIDER_CONFIG: Record<string, { displayName: string; getKeyUrl: string; placeholder: string }> = {
  "builtin:serper_dev_tool": {
    displayName: "Serper API Key",
    getKeyUrl: "https://serper.dev/api-key",
    placeholder: "Enter your Serper API key...",
  },
  "builtin:firecrawl_tool": {
    displayName: "Firecrawl API Key",
    getKeyUrl: "https://firecrawl.dev/app/api-keys",
    placeholder: "Enter your Firecrawl API key...",
  },
};

export function ApiKeyConfigModal({
  isOpen,
  onClose,
  provider,
  credentialStatus,
  credentialRequirement,
  onSuccess,
}: ApiKeyConfigModalProps) {
  const t = useTranslations("tools");
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Determine if this is a multi-credential (MCP) or single-credential (builtin) flow
  const isMultiCredential = !!credentialRequirement;

  // Get display config based on mode
  const getConfig = () => {
    if (isMultiCredential && credentialRequirement) {
      return {
        displayName: credentialRequirement.display_name,
        getKeyUrl: credentialRequirement.get_key_url || "",
        placeholder: `Enter your ${credentialRequirement.display_name}...`,
        description: credentialRequirement.description,
      };
    }
    // Builtin provider config
    const builtinConfig = PROVIDER_CONFIG[provider.provider_key] || {
      displayName: "API Key",
      getKeyUrl: "",
      placeholder: "Enter your API key...",
    };
    return { ...builtinConfig, description: null };
  };

  const config = getConfig();

  // Get current credential status
  const getCurrentStatus = () => {
    if (isMultiCredential && credentialRequirement) {
      return {
        has_credential: credentialRequirement.has_credential,
        is_verified: credentialRequirement.is_verified,
        uses_env_var: credentialRequirement.uses_env_var,
      };
    }
    return credentialStatus || { has_credential: false, is_verified: false, uses_env_var: false };
  };

  const currentStatus = getCurrentStatus();

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setApiKey("");
      setError(null);
      setSuccess(false);
      setShowDeleteConfirm(false);
    }
  }, [isOpen]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) {
      setError("API key cannot be empty");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      let result;
      if (isMultiCredential && credentialRequirement) {
        // Multi-credential flow (MCP providers)
        result = await apiClient.saveProviderCredential(
          provider.id,
          credentialRequirement.key,
          apiKey.trim()
        );
      } else {
        // Single-credential flow (builtin providers)
        result = await apiClient.saveProviderApiKey(provider.id, apiKey.trim());
      }

      if (result.is_verified) {
        setSuccess(true);
        // Auto-close after success
        setTimeout(() => {
          onSuccess();
          onClose();
        }, 1500);
      } else {
        setError("API key saved but verification failed. Please check your key.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to save API key");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    setLoading(true);
    setError(null);

    try {
      if (isMultiCredential && credentialRequirement) {
        // Multi-credential flow (MCP providers)
        await apiClient.deleteProviderCredential(provider.id, credentialRequirement.key);
      } else {
        // Single-credential flow (builtin providers)
        await apiClient.deleteProviderApiKey(provider.id);
      }
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to delete API key");
    } finally {
      setLoading(false);
      setShowDeleteConfirm(false);
    }
  };

  if (!isOpen) return null;

  // If using environment variable, show info message
  if (currentStatus.uses_env_var) {
    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
        <div className="bg-[var(--bg-panel)] rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
          <div className="flex items-center justify-between p-6 border-b border-[var(--border-color)]">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-900/20 rounded-lg border border-green-500/30">
                <Key className="w-5 h-5 text-green-400" />
              </div>
              <h2 className="text-xl font-semibold text-[var(--text-primary)]">{config.displayName}</h2>
            </div>
            <button
              onClick={onClose}
              className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-6">
            <div className="bg-green-900/10 border border-green-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm text-green-300 font-medium">Using Environment Variable</p>
                  <p className="text-xs text-green-300/70 mt-1">
                    This credential is configured via environment variable. No additional configuration needed.
                  </p>
                </div>
              </div>
            </div>

            <button
              onClick={onClose}
              className="w-full mt-4 px-4 py-2.5 border border-[var(--border-color)] rounded-lg text-sm font-medium text-[var(--text-secondary)] bg-[var(--bg-card)] hover:bg-[var(--bg-panel)] transition-colors"
            >
              {t('close')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
      <div className="bg-[var(--bg-panel)] rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-900/20 rounded-lg border border-amber-500/30">
              <Key className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-[var(--text-primary)]">{config.displayName}</h2>
              {isMultiCredential && (
                <p className="text-xs text-[var(--text-secondary)] mt-0.5">{provider.provider_key}</p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {showDeleteConfirm ? (
          <div className="p-6">
            <div className="bg-red-900/10 border border-red-500/30 rounded-lg p-4 mb-4">
              <p className="text-sm text-red-300">
                Are you sure you want to delete this API key? {isMultiCredential ? "This data source will become unavailable." : "The provider will become unhealthy."}
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={loading}
                className="flex-1 px-4 py-2.5 border border-[var(--border-color)] rounded-lg text-sm font-medium text-[var(--text-secondary)] bg-[var(--bg-card)] hover:bg-[var(--bg-panel)] transition-colors"
              >
                {t('cancel')}
              </button>
              <button
                onClick={handleDelete}
                disabled={loading}
                className="flex-1 px-4 py-2.5 border border-transparent rounded-lg text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                Delete
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSave} className="p-6 space-y-5">
            {/* Description for multi-credential */}
            {config.description && (
              <p className="text-sm text-[var(--text-secondary)]">{config.description}</p>
            )}

            {/* Current status */}
            {currentStatus.has_credential && (
              <div className={`rounded-lg p-3 ${
                currentStatus.is_verified
                  ? "bg-green-900/10 border border-green-500/30"
                  : "bg-amber-900/10 border border-amber-500/30"
              }`}>
                <div className="flex items-center gap-2">
                  {currentStatus.is_verified ? (
                    <>
                      <Check className="w-4 h-4 text-green-400" />
                      <span className="text-sm text-green-300">API key configured and verified</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-4 h-4 text-amber-400" />
                      <span className="text-sm text-amber-300">API key saved but not verified</span>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* API Key input */}
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                {currentStatus.has_credential ? "Update API Key" : "Enter API Key"} <span className="text-red-400">*</span>
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={config.placeholder}
                required
                autoFocus
                className="w-full px-3 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:border-[var(--accent-blue)] outline-none transition-colors font-mono"
              />
            </div>

            {/* Get API Key link */}
            {config.getKeyUrl && (
              <a
                href={config.getKeyUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-[var(--accent-blue)] hover:underline"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Get your API key
              </a>
            )}

            {/* Success message */}
            {success && (
              <div className="bg-green-900/10 border border-green-500/30 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-400" />
                  <span className="text-sm text-green-300">API key verified and saved successfully!</span>
                </div>
              </div>
            )}

            {/* Error message */}
            {error && (
              <div className="bg-red-900/10 border border-red-500/30 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-red-400" />
                  <span className="text-sm text-red-400">{error}</span>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              {currentStatus.has_credential && (
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(true)}
                  disabled={loading}
                  className="px-4 py-2.5 border border-red-500/30 rounded-lg text-sm font-medium text-red-400 bg-red-900/10 hover:bg-red-900/20 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                disabled={loading}
                className="flex-1 px-4 py-2.5 border border-[var(--border-color)] rounded-lg text-sm font-medium text-[var(--text-secondary)] bg-[var(--bg-card)] hover:bg-[var(--bg-panel)] transition-colors"
              >
                {t('cancel')}
              </button>
              <button
                type="submit"
                disabled={loading || !apiKey.trim() || success}
                className="flex-1 px-4 py-2.5 border border-transparent rounded-lg text-sm font-medium text-white bg-[var(--accent-blue)] hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  "Verify & Save"
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
