"use client";

import React, { useState } from "react";
import { X, Database, HelpCircle } from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import type { ProviderType } from "@/types/skills";

interface AddProviderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (providerId: number) => void;
}

export function AddProviderModal({
  isOpen, onClose, onSuccess }: AddProviderModalProps) {
  const t = useTranslations("tools");
  const [providerKey, setProviderKey] = useState("");
  const [providerType, setProviderType] = useState<ProviderType>("mcp");
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await apiClient.createProvider({
        provider_key: providerKey,
        provider_type: providerType,
        url: providerType === "mcp" ? url : undefined,
      });

      setProviderKey("");
      setUrl("");
      setProviderType("mcp");

      onSuccess(response.provider_id);
    } catch (err: any) {
      setError(err.message || "Failed to create provider");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
      <div className="bg-[var(--bg-panel)] rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-900/20 rounded-lg border border-blue-500/30">
              <Database className="w-5 h-5 text-blue-400" />
            </div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">{t('addProvider')}</h2>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              Provider {t('type')}
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setProviderType("mcp")}
                className={`px-4 py-2.5 rounded-lg border transition-all ${
                  providerType === "mcp"
                    ? "bg-[var(--accent-blue)]/10 border-[var(--accent-blue)]/30 text-[var(--accent-blue)]"
                    : "bg-[var(--bg-card)] border-[var(--border-color)] text-[var(--text-secondary)] hover:border-[var(--text-secondary)]"
                }`}
              >
                MCP Server
              </button>
              <button
                type="button"
                onClick={() => setProviderType("builtin")}
                className={`px-4 py-2.5 rounded-lg border transition-all ${
                  providerType === "builtin"
                    ? "bg-[var(--accent-blue)]/10 border-[var(--accent-blue)]/30 text-[var(--accent-blue)]"
                    : "bg-[var(--bg-card)] border-[var(--border-color)] text-[var(--text-secondary)] hover:border-[var(--text-secondary)]"
                }`}
              >
                Builtin
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              Provider Key <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={providerKey}
              onChange={(e) => setProviderKey(e.target.value)}
              placeholder="e.g., akshare_mcp, yfinance_mcp"
              required
              className="w-full px-3 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:border-[var(--accent-blue)] outline-none transition-colors"
            />
            <p className="mt-1.5 text-xs text-[var(--text-secondary)]">
              Unique identifier for this provider (lowercase, underscores allowed)
            </p>
          </div>

          {providerType === "mcp" && (
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                MCP Server URL <span className="text-red-400">*</span>
              </label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="http://localhost:8001"
                required={providerType === "mcp"}
                className="w-full px-3 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:border-[var(--accent-blue)] outline-none transition-colors"
              />
              <p className="mt-1.5 text-xs text-[var(--text-secondary)]">
                HTTP endpoint of the MCP server
              </p>
            </div>
          )}

          <div className="bg-blue-900/10 border border-blue-500/30 rounded-lg p-4">
            <div className="flex items-start gap-2.5">
              <HelpCircle className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-blue-300/80 leading-relaxed">
                After creating the provider, you will need to map its capabilities.
                {providerType === "mcp" && " The system will discover available tools from the MCP server."}
              </p>
            </div>
          </div>

          {error && (
            <div className="bg-red-900/10 border border-red-500/30 rounded-lg p-3">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 border border-[var(--border-color)] rounded-lg text-sm font-medium text-[var(--text-secondary)] bg-[var(--bg-card)] hover:bg-[var(--bg-panel)] transition-colors"
            >
              {t('cancel')}
            </button>
            <button
              type="submit"
              disabled={loading || !providerKey || (providerType === "mcp" && !url)}
              className="flex-1 px-4 py-2.5 border border-transparent rounded-lg text-sm font-medium text-white bg-[var(--accent-blue)] hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Creating..." : "Create Provider"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
