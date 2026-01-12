"use client";

import React, { useState, useEffect } from "react";
import { X, Loader2, Check, ShieldCheck } from "lucide-react";
import apiClient from "@/lib/api";

interface ModelConfig {
  id: number;
  model: {
    key: string;
    display_name: string;
    context_length?: number;
    category: string;
    performance_level?: string;
  };
  is_active: boolean;
  is_available: boolean;
}

interface ModelSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  configId: number;
  providerName: string;
  onUpdate: () => void;
}

export function ModelSelectorModal({ isOpen, onClose, configId, providerName, onUpdate }: ModelSelectorModalProps) {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchModels();
    }
  }, [isOpen, configId]);

  const fetchModels = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.listConfigModels(configId, true);
      setModels(data);
    } catch (error) {
      console.error("Failed to fetch models:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleModelStatus = async (modelId: number, currentStatus: boolean) => {
    setUpdatingId(modelId);
    try {
      await apiClient.updateModelStatus(modelId, !currentStatus);
      setModels(models.map(m => m.id === modelId ? { ...m, is_active: !currentStatus } : m));
      onUpdate();
    } catch (error) {
      console.error("Failed to update model status:", error);
    } finally {
      setUpdatingId(null);
    }
  };

  const sortModels = (modelList: ModelConfig[]) => {
    return [...modelList].sort((a, b) => {
      // 1. Prioritize active models
      if (a.is_active !== b.is_active) {
        return a.is_active ? -1 : 1;
      }

      const nameA = (a.model?.display_name || '').toLowerCase();
      const nameB = (b.model?.display_name || '').toLowerCase();
      const keyA = (a.model?.key || '').toLowerCase();
      const keyB = (b.model?.key || '').toLowerCase();

      // 2. Check date (YYYYMMDD format) - Descending
      const dateRegex = /\d{8}/;
      const dateA = nameA.match(dateRegex) || keyA.match(dateRegex);
      const dateB = nameB.match(dateRegex) || keyB.match(dateRegex);
      
      if (dateA || dateB) {
        if (dateA && dateB) {
          const res = dateB[0].localeCompare(dateA[0]);
          if (res !== 0) return res;
        } else if (dateA) {
          return -1;
        } else if (dateB) {
          return 1;
        }
      }

      // 3. Check model size (xxxB format, e.g., 70B, 8B) - Descending
      const sizeRegex = /(\d+)b/;
      const sizeA = nameA.match(sizeRegex) || keyA.match(sizeRegex);
      const sizeB = nameB.match(sizeRegex) || keyB.match(sizeRegex);
      if (sizeA || sizeB) {
        if (sizeA && sizeB) {
          const res = parseInt(sizeB[1]) - parseInt(sizeA[1]);
          if (res !== 0) return res;
        } else if (sizeA) {
          return -1;
        } else if (sizeB) {
          return 1;
        }
      }

      // 4. Default to alphabetical
      return nameA.localeCompare(nameB);
    });
  };

  const sortedModels = sortModels(models);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] w-full max-w-lg rounded-xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200 flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[var(--border-color)]">
          <div>
            <h2 className="text-lg font-bold text-[var(--text-primary)]">Enable Models</h2>
            <p className="text-xs text-[var(--text-secondary)]">{providerName} - Only enabled models will appear in Crew Builder</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-[var(--bg-card)] rounded-lg transition-colors">
            <X className="w-5 h-5 text-[var(--text-secondary)] hover:text-white" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
              <p className="text-sm text-[var(--text-secondary)]">Loading model list...</p>
            </div>
          ) : sortedModels.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-sm text-[var(--text-secondary)]">No models available. Please verify configuration first.</p>
            </div>
          ) : (
            <div className="grid gap-3">
              {sortedModels.map((model) => (
                <div 
                  key={model.id}
                  onClick={() => !updatingId && toggleModelStatus(model.id, model.is_active)}
                  className={`flex items-center justify-between p-4 rounded-xl border transition-all cursor-pointer group ${
                    model.is_active 
                      ? 'bg-[var(--accent-blue)]/5 border-[var(--accent-blue)]/30' 
                      : 'bg-[var(--bg-card)] border-[var(--border-color)] hover:border-[var(--text-secondary)]/30'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
                      model.is_active ? 'bg-[var(--accent-blue)] text-white' : 'bg-[var(--bg-panel)] text-[var(--text-secondary)]'
                    }`}>
                      {model.is_active ? <ShieldCheck className="w-5 h-5" /> : <Check className="w-5 h-5 opacity-20" />}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-[var(--text-primary)]">{model.model.display_name}</div>
                      <div className="text-[10px] text-[var(--text-secondary)] font-mono flex gap-2">
                        <span>{model.model.key}</span>
                        {model.model.context_length && <span>• {Math.round(model.model.context_length / 1024)}k tokens</span>}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {updatingId === model.id ? (
                      <Loader2 className="w-4 h-4 animate-spin text-[var(--accent-blue)]" />
                    ) : (
                      <div className={`w-10 h-5 rounded-full p-1 transition-colors duration-200 ${model.is_active ? 'bg-[var(--accent-blue)]' : 'bg-[var(--border-color)]'}`}>
                        <div className={`w-3 h-3 bg-white rounded-full transition-transform duration-200 ${model.is_active ? 'translate-x-5' : 'translate-x-0'}`} />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[var(--border-color)] bg-[var(--bg-card)]/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 rounded-lg text-sm font-bold bg-[var(--accent-blue)] text-white hover:bg-blue-600 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
