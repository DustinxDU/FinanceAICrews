"use client";

import React, { useState, useEffect } from "react";
import { X, Database, Loader2, RefreshCw } from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import type { Provider } from "@/types/skills";
import { CredentialsList, type CredentialRequirement } from "./CredentialsList";
import { ApiKeyConfigModal } from "./ApiKeyConfigModal";

interface CredentialsModalProps {
  isOpen: boolean;
  onClose: () => void;
  provider: Provider;
  onCredentialsChanged: () => void;
}

/**
 * Modal for managing multiple credentials for MCP providers.
 *
 * MCP providers like OpenBB can require multiple API keys from different
 * data sources (e.g., Polygon, FMP, Benzinga). This modal allows users
 * to view and configure each credential individually.
 */
export function CredentialsModal({
  isOpen,
  onClose,
  provider,
  onCredentialsChanged,
}: CredentialsModalProps) {
  const t = useTranslations("tools");
  const [credentials, setCredentials] = useState<CredentialRequirement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected credential for configuration
  const [selectedCredential, setSelectedCredential] = useState<CredentialRequirement | null>(null);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);

  // Load credentials when modal opens
  useEffect(() => {
    if (isOpen) {
      loadCredentials();
    }
  }, [isOpen, provider.id]);

  const loadCredentials = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getProviderCredentials(provider.id);
      setCredentials(response.credentials);
    } catch (err: any) {
      console.error("Failed to load credentials:", err);
      setError(err.message || "Failed to load credentials");
    } finally {
      setLoading(false);
    }
  };

  const handleConfigureCredential = (credential: CredentialRequirement) => {
    setSelectedCredential(credential);
    setIsApiKeyModalOpen(true);
  };

  const handleApiKeySuccess = () => {
    loadCredentials();
    onCredentialsChanged();
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
        <div className="bg-[var(--bg-panel)] rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-[var(--border-color)]">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-900/20 rounded-lg border border-amber-500/30">
                <Database className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-[var(--text-primary)]">
                  Data Source API Keys
                </h2>
                <p className="text-sm text-[var(--text-secondary)]">
                  {provider.provider_key}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={loadCredentials}
                disabled={loading}
                className="p-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors rounded-lg hover:bg-[var(--bg-card)]"
                title="Refresh"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              </button>
              <button
                onClick={onClose}
                className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
              </div>
            ) : error ? (
              <div className="bg-red-900/10 border border-red-500/30 rounded-lg p-4">
                <p className="text-sm text-red-400">{error}</p>
                <button
                  onClick={loadCredentials}
                  className="mt-2 text-sm text-[var(--accent-blue)] hover:underline"
                >
                  Try again
                </button>
              </div>
            ) : (
              <>
                <p className="text-sm text-[var(--text-secondary)] mb-4">
                  Configure API keys for the data sources used by this provider.
                  Some credentials may be optional depending on which features you need.
                </p>
                <CredentialsList
                  credentials={credentials}
                  onConfigureCredential={handleConfigureCredential}
                />
              </>
            )}
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-[var(--border-color)]">
            <button
              onClick={onClose}
              className="w-full px-4 py-2.5 border border-[var(--border-color)] rounded-lg text-sm font-medium text-[var(--text-secondary)] bg-[var(--bg-card)] hover:bg-[var(--bg-panel)] transition-colors"
            >
              {t("close")}
            </button>
          </div>
        </div>
      </div>

      {/* Nested API Key Configuration Modal */}
      {selectedCredential && (
        <ApiKeyConfigModal
          isOpen={isApiKeyModalOpen}
          onClose={() => {
            setIsApiKeyModalOpen(false);
            setSelectedCredential(null);
          }}
          provider={provider}
          credentialRequirement={selectedCredential}
          onSuccess={handleApiKeySuccess}
        />
      )}
    </>
  );
}
