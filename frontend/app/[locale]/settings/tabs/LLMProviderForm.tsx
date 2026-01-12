"use client";

import React, { useState } from "react";
import { Trash2, Check, Loader2 } from "lucide-react";
import { useToast } from "@/lib/toast";
import { useTranslations } from "next-intl";

import apiClient from "@/lib/api";

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

interface LLMProviderFormProps {
  onSave: (data: any) => void;
  onCancel: () => void;
  providers: Provider[];
  editMode?: boolean;
  initialProvider?: SavedProvider | null;
}

export function LLMProviderForm({
  onSave,
  onCancel,
  providers,
  editMode = false,
  initialProvider = null
}: LLMProviderFormProps) {
  const t = useTranslations("settings");
  const { error, success } = useToast();
  // 从 provider.key 或 provider_key 获取 provider key
  const initialProviderKey = initialProvider?.provider?.key || initialProvider?.provider_key || "";
  const [provider, setProvider] = useState(editMode && initialProvider ? initialProviderKey : providers[0]?.provider_key || "");
  const [apiKey, setApiKey] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [verified, setVerified] = useState(false);
  // 从 volcengine_endpoints 字符串数组转换为内部格式
  const [endpoints, setEndpoints] = useState(() => {
    if (editMode && initialProvider?.volcengine_endpoints && initialProvider.volcengine_endpoints.length > 0) {
      return initialProvider.volcengine_endpoints.map((ep, idx) => ({
        id: idx + 1,
        value: ep,
        verified: true,
        verifying: false
      }));
    }
    return [{ id: 1, value: "", verified: false, verifying: false }];
  });

  const handleVerify = async () => {
    if (!provider || !apiKey) return;
    setIsVerifying(true);
    try {
      const verifyResult = await apiClient.verifyProviderConfig(
        provider,
        apiKey,
        undefined,
        provider === "volcengine" ? endpoints.map(e => e.value) : undefined
      );
      setVerified(verifyResult.valid);
      if (!verifyResult.valid) {
        let errorMessage = verifyResult.error || verifyResult.message || "Verification failed";
        if (verifyResult.error_details) {
          const details = verifyResult.error_details;
          errorMessage += "\n\nError details:\n";
          if (details.status_code) errorMessage += `• HTTP Status: ${details.status_code}\n`;
          if (details.error_code) errorMessage += `• Error Code: ${details.error_code}\n`;
          if (details.provider) errorMessage += `• Provider: ${details.provider}\n`;
        }
        if (provider === 'google_gemini') {
          errorMessage += "\nGoogle Gemini Troubleshooting:\n";
          errorMessage += `• Get API Key from: https://aistudio.google.com/apikey\n`;
          errorMessage += `• Ensure API Key has Generative Language API enabled\n`;
          errorMessage += `• Check if your region supports Google AI Studio\n`;
          errorMessage += `• Verify API Key format: AIza... (39 characters)\n`;
        }
        error(t('failed'), errorMessage);
      } else {
        success("Verification Successful", "API key is valid");
      }
    } catch (err: any) {
      let errorMessage = err.message || "Verification failed";
      if (err.message && err.message.includes('fetch')) {
        errorMessage += "\n\nThis appears to be a network error. Please check:\n";
        errorMessage += "• Your internet connection\n";
        errorMessage += "• If the backend server is running\n";
        errorMessage += "• If there are any firewall restrictions\n";
      }
      error("Verification Error", errorMessage);
      setVerified(false);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleEndpointVerify = (id: number) => {
    setEndpoints((prev) => prev.map((ep) => (ep.id === id ? { ...ep, verifying: true } : ep)));
    setTimeout(() => {
      setEndpoints((prev) => prev.map((ep) => (ep.id === id ? { ...ep, verifying: false, verified: true } : ep)));
    }, 1000);
  };

  const addEndpoint = () => setEndpoints((prev) => [...prev, { id: Date.now(), value: "", verified: false, verifying: false }]);
  const removeEndpoint = (id: number) => setEndpoints((prev) => prev.filter((ep) => ep.id !== id));

  const handleSave = async () => {
    const selectedProvider = providers.find((p) => p.provider_key === provider);
    setIsVerifying(true);
    try {
      const saveRes = await apiClient.saveProviderConfig({
        provider_key: provider,
        api_key: apiKey,
        endpoints: provider === "volcengine" ? endpoints.map(e => e.value) : undefined,
        config_id: editMode ? initialProvider?.id : undefined,
      });

      const verifyRes = await apiClient.verifyProviderConfig(
        provider,
        apiKey,
        undefined,
        provider === "volcengine" ? endpoints.map(e => e.value) : undefined
      );

      if (!verifyRes.valid) {
        error("Save {t('failed')}", verifyRes.message || "Verification failed");
      }

      onSave({
        provider_key: provider,
        provider_name: selectedProvider?.display_name || provider || "Provider",
        apiKey,
        config_id: (saveRes as any)?.id,
        endpoints: provider === "volcengine" ? endpoints : undefined
      });
    } catch (err: any) {
      error("Save {t('failed')}", err?.message || "An error occurred while saving");
    } finally {
      setIsVerifying(false);
    }
  };

  const canSave = () => {
    if (!apiKey || !provider) return false;
    if (provider === "volcengine") return endpoints.length > 0 && endpoints.every((ep) => ep.verified);
    return verified;
  };

  // 使用 is_china_provider 或 region 来分组
  const globalProviders = providers.filter(p => !p.is_china_provider && p.region !== "china");
  const chinaProviders = providers.filter(p => p.is_china_provider || p.region === "china");

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-6 animate-in fade-in zoom-in-95 duration-200">
      <h3 className="text-lg font-bold mb-4">{editMode ? "Update Model Provider" : "Add New Model Provider"}</h3>
      {editMode && initialProvider && (
        <div className="mb-4 p-3 bg-blue-900/10 border border-blue-900/30 rounded-lg">
          <p className="text-xs text-blue-200">Updating: <strong>{initialProvider.name}</strong></p>
          <p className="text-xs text-[var(--text-secondary)] mt-1">Current key: <span className="font-mono">{initialProvider.key}</span></p>
          <p className="text-[10px] text-[var(--text-secondary)] mt-1">For security reasons, you must re-enter the complete API Key to save changes.</p>
        </div>
      )}
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-[var(--text-secondary)] uppercase mb-1">Provider</label>
          <select
            value={provider}
            onChange={(e) => { setProvider(e.target.value); setVerified(false); setEndpoints([{ id: 1, value: "", verified: false, verifying: false }]); }}
            className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm focus:border-[var(--accent-blue)] outline-none"
          >
            {globalProviders.length > 0 && <optgroup label="Global">{globalProviders.map((p) => (<option key={p.provider_key} value={p.provider_key}>{p.display_name}</option>))}</optgroup>}
            {chinaProviders.length > 0 && <optgroup label="China">{chinaProviders.map((p) => (<option key={p.provider_key} value={p.provider_key}>{p.display_name}</option>))}</optgroup>}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-[var(--text-secondary)] uppercase mb-1">API Key</label>
          <div className="flex gap-2">
            <input
              type="password"
              value={apiKey}
              onChange={(e) => { setApiKey(e.target.value); setVerified(false); }}
              placeholder="sk-..."
              className="flex-1 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm focus:border-[var(--accent-blue)] outline-none font-mono"
            />
            {provider !== "volcengine" && (
              <button
                onClick={handleVerify}
                disabled={!apiKey || isVerifying || verified}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors border ${verified ? "bg-green-900/20 border-green-500 text-green-400" : "border-[var(--border-color)] hover:bg-[var(--bg-panel)]"}`}
              >
                {isVerifying ? "Checking..." : verified ? "Verified" : "Verify"}
              </button>
            )}
          </div>
        </div>
        {provider === "volcengine" && (
          <div className="space-y-3 pt-2 border-t border-[var(--border-color)]">
            <div className="flex justify-between items-center">
              <label className="text-xs font-medium text-[var(--text-secondary)] uppercase">Model Endpoints</label>
              <button onClick={addEndpoint} className="text-xs text-[var(--accent-blue)] hover:underline">+ Add Endpoint</button>
            </div>
            {endpoints.map((ep, idx) => (
              <div key={ep.id} className="flex gap-2 items-center animate-in slide-in-from-left-2">
                <span className="text-xs text-[var(--text-secondary)] font-mono w-4">{idx + 1}.</span>
                <input
                  type="text"
                  value={ep.value}
                  onChange={(e) => { const newVal = e.target.value; setEndpoints((prev) => prev.map((item) => (item.id === ep.id ? { ...item, value: newVal, verified: false } : item))); }}
                  placeholder="ep-20250101..."
                  className="flex-1 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-xs focus:border-[var(--accent-blue)] outline-none font-mono"
                />
                <button
                  onClick={() => handleEndpointVerify(ep.id)}
                  disabled={!ep.value || ep.verifying || ep.verified}
                  className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors border ${ep.verified ? "bg-green-900/20 border-green-500 text-green-400" : "border-[var(--border-color)] hover:bg-[var(--bg-panel)]"}`}
                >
                  {ep.verifying ? "..." : ep.verified ? "OK" : "Test"}
                </button>
                {endpoints.length > 1 && (<button onClick={() => removeEndpoint(ep.id)} className="p-2 text-[var(--text-secondary)] hover:text-red-400"><Trash2 className="w-3 h-3" /></button>)}
              </div>
            ))}
            <p className="text-[10px] text-[var(--text-secondary)]">For Volcano Engine, verify each endpoint ID connected to your Doubao models.</p>
          </div>
        )}
        <div className="flex justify-end gap-3 pt-4">
          <button onClick={onCancel} className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-white transition-colors">{t('cancel')}</button>
          <button
            onClick={handleSave}
            disabled={!canSave()}
            className={`px-4 py-2 rounded-lg text-sm font-bold text-black transition-colors ${canSave() ? "bg-[var(--accent-green)] hover:bg-emerald-400" : "bg-zinc-700 text-zinc-500 cursor-not-allowed"}`}
          >
            {t('saveProvider')}
          </button>
        </div>
      </div>
    </div>
  );
}
