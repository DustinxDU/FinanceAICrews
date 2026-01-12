"use client";

import React, { useState, useEffect } from "react";
import { X, Loader2 } from "lucide-react";
import apiClient from "@/lib/api";

interface EditProviderModalProps {
  isOpen: boolean;
  onClose: () => void;
  provider: {
    id: number;
    name: string;
    key: string;
    provider_key?: string;
    config_id?: number;
    endpoints?: Array<{ id: number; value: string; verified: boolean }>;
  } | null;
  onSave: () => void;
}

export function EditProviderModal({ isOpen, onClose, provider, onSave }: EditProviderModalProps) {
  const [apiKey, setApiKey] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [verifyMessage, setVerifyMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && provider) {
      setApiKey("");
      setVerifyMessage(null);
    }
  }, [isOpen, provider]);

  if (!isOpen || !provider) return null;

  const handleVerify = async () => {
    if (!apiKey) {
      setVerifyMessage("Please enter an API Key");
      return;
    }
    
    if (!provider.provider_key) {
      setVerifyMessage("Provider key is missing");
      return;
    }
    
    setIsVerifying(true);
    try {
      const result = await apiClient.verifyProviderConfig(
        provider.provider_key!,
        apiKey,
        undefined, // base_url not needed - editing existing provider
        provider.endpoints?.map(e => e.value)  // Pass endpoints if available
      );
      if (result.valid) {
        setVerifyMessage("✅ Verification Successful");
      } else {
        let errorMessage = result.error || result.message || "Verification Failed";
        
        // 添加错误详情
        if (result.error_details) {
          const details = result.error_details;
          errorMessage += `\n\nDetails: HTTP ${details.status_code}`;
          if (details.error_code) {
            errorMessage += `, Code: ${details.error_code}`;
          }
        }
        
        // Google Gemini特定帮助
        if (provider.provider_key === 'google_gemini') {
          errorMessage += `\n\n📋 Troubleshooting:\n• Verify API Key from aistudio.google.com\n• Check API permissions and quotas`;
        }
        
        setVerifyMessage(errorMessage);
      }
    } catch (error: any) {
      let errorMessage = error?.message || "Verification Failed";
      if (error?.message?.includes('fetch')) {
        errorMessage += "\n🌐 Network error - check connection";
      }
      setVerifyMessage(errorMessage);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleSave = async () => {
    if (!apiKey) {
      setVerifyMessage("Please enter a new API Key");
      return;
    }
    setIsSaving(true);
    try {
      await apiClient.saveProviderConfig({
        provider_key: provider.provider_key!,
        api_key: apiKey,
        endpoints: provider.endpoints?.map(e => e.value),
        config_id: provider.config_id,
      });
      onSave();
      onClose();
    } catch (error: any) {
      setVerifyMessage(error?.message || "Failed to save");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] w-full max-w-md rounded-xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[var(--border-color)]">
          <div>
            <h2 className="text-lg font-bold text-[var(--text-primary)]">Configure {provider.name}</h2>
            <p className="text-xs text-[var(--text-secondary)]">Update API Key and re-verify</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-[var(--bg-card)] rounded-lg transition-colors">
            <X className="w-5 h-5 text-[var(--text-secondary)] hover:text-white" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-[var(--text-secondary)] uppercase mb-2">Provider</label>
            <div className="text-sm font-medium text-[var(--text-primary)]">{provider.name}</div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[var(--text-secondary)] uppercase mb-2">Current API Key</label>
            <div className="text-xs font-mono text-[var(--text-secondary)] bg-[var(--bg-card)] px-3 py-2 rounded border border-[var(--border-color)]">
              {provider.key}
            </div>
            <p className="text-[10px] text-amber-500/80 mt-1">
              * Must re-enter full API Key to save
            </p>
          </div>

          {provider.endpoints && provider.endpoints.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)] uppercase mb-2">Endpoints</label>
              <div className="space-y-1">
                {provider.endpoints.map((ep, i) => (
                  <div key={i} className="text-xs font-mono text-[var(--text-secondary)] bg-[var(--bg-card)] px-3 py-2 rounded border border-[var(--border-color)]">
                    {ep.value}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-[var(--text-secondary)] uppercase mb-2">New API Key</label>
            <div className="flex gap-2">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => { setApiKey(e.target.value); setVerifyMessage(null); }}
                placeholder="Enter new API Key..."
                className="flex-1 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm focus:border-[var(--accent-blue)] outline-none font-mono"
              />
              <button
                onClick={handleVerify}
                disabled={!apiKey || isVerifying}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-colors border border-[var(--border-color)] hover:bg-[var(--bg-panel)] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isVerifying ? <Loader2 className="w-4 h-4 animate-spin" /> : "Verify"}
              </button>
            </div>
            {verifyMessage && (
              <p className={`text-xs mt-2 ${verifyMessage.includes("Success") ? "text-green-400" : "text-red-400"}`}>
                {verifyMessage}
              </p>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[var(--border-color)] bg-[var(--bg-card)]/50 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!apiKey || isSaving}
            className="px-4 py-2 rounded-lg text-sm font-bold bg-[var(--accent-blue)] text-white hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Configuration
          </button>
        </div>
      </div>
    </div>
  );
}
