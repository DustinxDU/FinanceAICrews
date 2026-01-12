"use client";

import React, { useState } from "react";
import { Plus, Trash2, Info, Loader2, Settings } from "lucide-react";
import { useTranslations } from "next-intl";
import { LLMProviderForm } from "./LLMProviderForm";

interface SavedProvider {
  id: number;
  config_name?: string;
  name?: string;
  api_key?: string;
  key?: string;
  provider?: {
    key: string;
    display_name: string;
    type?: string;
  };
  provider_key?: string;
  volcengine_endpoints?: string[];
  is_validated?: boolean;
  model_count?: number;
}

interface Provider {
  provider_key: string;
  display_name: string;
  description?: string;
  region?: string;
  is_china_provider?: boolean;
  requires_api_key: boolean;
  supports_streaming?: boolean;
  capabilities?: any;
}

interface APIKeysTabProps {
  savedProviders: SavedProvider[];
  availableProviders: Provider[];
  isLoadingProviders: boolean;
  isDeleting: boolean;
  onSaveProvider: (data: any) => void;
  onDeleteProvider: (provider: SavedProvider) => void;
  onEditProvider: (provider: SavedProvider) => void;
  refreshModels: () => void;
}

export function APIKeysTab({
  savedProviders,
  availableProviders,
  isLoadingProviders,
  isDeleting,
  onSaveProvider,
  onDeleteProvider,
  onEditProvider,
  refreshModels
}: APIKeysTabProps) {
  const t = useTranslations('settings');
  const [showAddProvider, setShowAddProvider] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editProvider, setEditProvider] = useState<SavedProvider | null>(null);

  if (isLoadingProviders) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
      </div>
    );
  }

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold mb-1">API Keys</h2>
          <p className="text-sm text-[var(--text-secondary)]">Manage your LLM provider connections and API keys.</p>
        </div>
        {!showAddProvider && (
          <button
            onClick={() => setShowAddProvider(true)}
            className="bg-[var(--accent-blue)] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> {t('addProvider')}
          </button>
        )}
      </div>

      {showAddProvider ? (
        <LLMProviderForm
          onSave={(data) => {
            onSaveProvider(data);
            setShowAddProvider(false);
          }}
          onCancel={() => setShowAddProvider(false)}
          providers={availableProviders}
        />
      ) : showEditModal ? (
        <LLMProviderForm
          onSave={async (data: any) => {
            onSaveProvider(data);
            setShowEditModal(false);
            setEditProvider(null);
          }}
          onCancel={() => {
            setShowEditModal(false);
            setEditProvider(null);
          }}
          providers={availableProviders}
          editMode={true}
          initialProvider={editProvider}
        />
      ) : (
        <div className="space-y-4">
          {savedProviders.map((p) => {
            // 使用 provider.display_name 或 config_name 作为显示名称
            const displayName = p.provider?.display_name || p.config_name || p.name || "Provider";
            const initials = displayName.slice(0, 2).toUpperCase();
            // 遮罩 API Key：显示前4位 + •••• + 后4位
            const rawKey = p.api_key || p.key || "";
            const maskedKey = rawKey.length > 12
              ? `${rawKey.slice(0, 4)}••••••••${rawKey.slice(-4)}`
              : rawKey.length > 0
                ? "••••••••"
                : "No key";
            const isValidated = p.is_validated !== false;
            const modelCount = p.model_count || 0;

            return (
              <div key={p.id} className="flex items-center justify-between p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg group">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded bg-white text-black flex items-center justify-center font-bold text-xs">{initials}</div>
                  <div>
                    <div className="font-medium flex items-center gap-2">
                      {displayName}
                      <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
                        isValidated
                          ? "bg-green-900/30 text-green-400 border-green-900/50"
                          : "bg-yellow-900/30 text-yellow-400 border-yellow-900/50"
                      }`}>
                        {isValidated ? "{t('active')}" : "Not Verified"}
                      </span>
                      {modelCount > 0 && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                          {modelCount} models
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-[var(--text-secondary)] font-mono">{maskedKey}</div>
                    {p.volcengine_endpoints && p.volcengine_endpoints.length > 0 && (
                      <div className="mt-1 flex gap-1">
                        {p.volcengine_endpoints.map((ep, i) => (
                          <span key={i} className="text-[10px] bg-zinc-800 px-1 rounded text-zinc-400 border border-zinc-700" title={ep}>
                            {ep.substring(0, 8)}...
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => {
                      setEditProvider(p);
                      setShowEditModal(true);
                    }}
                    className="px-3 py-1.5 border border-[var(--border-color)] rounded text-xs font-medium hover:bg-[var(--bg-panel)] flex items-center gap-1.5"
                  >
                    <Settings className="w-3.5 h-3.5" />
                    {t('configure')}
                  </button>
                  <button
                    onClick={() => onDeleteProvider(p)}
                    disabled={isDeleting}
                    className="p-2 text-[var(--text-secondary)] hover:text-red-400 hover:bg-[var(--bg-panel)] rounded disabled:opacity-50"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
          <div className="mt-4 p-4 bg-blue-900/10 border border-blue-900/30 rounded-lg text-xs text-blue-200 flex gap-3">
            <Info className="w-4 h-4 shrink-0" />
            <p>{t('configure')} your API keys here. Model selection for different agent scenarios is managed in the <strong>{t('agentModels')}</strong> tab.</p>
          </div>
        </div>
      )}
    </div>
  );
}
