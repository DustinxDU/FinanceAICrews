"use client";

import React, { useState } from "react";
import { X, Zap, HelpCircle } from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import { ALL_CAPABILITIES, CAPABILITY_METADATA } from "@/lib/taxonomy";

interface CreatePresetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function CreatePresetModal({
  isOpen,
  onClose,
  onSuccess
}: CreatePresetModalProps) {
  const t = useTranslations("tools");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [capabilityId, setCapabilityId] = useState("");
  const [defaults, setDefaults] = useState<Record<string, any>>({});
  const [defaultsJson, setDefaultsJson] = useState("{}");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDefaultsChange = (value: string) => {
    setDefaultsJson(value);
    try {
      const parsed = JSON.parse(value);
      setDefaults(parsed);
      setError(null);
    } catch {
      // Invalid JSON, will show error on submit
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      JSON.parse(defaultsJson);
    } catch {
      setError("Invalid JSON in default parameters");
      return;
    }

    setLoading(true);

    try {
      const skill_key = `preset:${title.toLowerCase().replace(/\s+/g, "_")}`;

      await apiClient.createSkill({
        skill_key,
        kind: "preset",
        capability_id: capabilityId,
        title,
        description,
        invocation: {
          capability_id: capabilityId,
          defaults: JSON.parse(defaultsJson),
        },
        args_schema: null,
      });

      setTitle("");
      setDescription("");
      setCapabilityId("");
      setDefaultsJson("{}");

      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to create preset");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
      <div className="bg-[var(--bg-panel)] rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-900/20 rounded-lg border border-purple-500/30">
              <Zap className="w-5 h-5 text-purple-400" />
            </div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">{t('createPreset')}</h2>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">
          <div className="bg-purple-900/10 border border-purple-500/30 rounded-lg p-4">
            <div className="flex items-start gap-2.5">
              <HelpCircle className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-purple-300/80 leading-relaxed">
                Presets are reusable skill templates with predefined parameters.
                Example: "RSI(14)" preset wraps indicator_calc capability with period=14.
              </p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              Preset Title <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., RSI(14), MACD Default"
              required
              className="w-full px-3 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:border-[var(--accent-blue)] outline-none transition-colors"
            />
            {title && (
              <p className="mt-1.5 text-xs text-[var(--text-secondary)]">
                Skill key:{" "}
                <code className="text-[var(--accent-blue)] font-mono">
                  preset:{title.toLowerCase().replace(/\s+/g, "_")}
                </code>
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe this preset and when to use it"
              rows={3}
              className="w-full px-3 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:border-[var(--accent-blue)] outline-none transition-colors resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              Base Capability <span className="text-red-400">*</span>
            </label>
            <select
              value={capabilityId}
              onChange={(e) => setCapabilityId(e.target.value)}
              required
              className="w-full px-3 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] focus:border-[var(--accent-blue)] outline-none transition-colors"
            >
              <option value="">{t('selectCapabilityShort')}</option>
              {ALL_CAPABILITIES.map((cap) => {
                const meta = CAPABILITY_METADATA[cap] || {};
                const displayName = meta.display_name || cap;
                return (
                  <option key={cap} value={cap}>
                    {displayName} ({cap})
                  </option>
                );
              })}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              {t('defaultParameters')} <span className="text-red-400">*</span>
            </label>
            <textarea
              value={defaultsJson}
              onChange={(e) => handleDefaultsChange(e.target.value)}
              placeholder='{"indicator": "rsi", "period": 14}'
              rows={6}
              className="w-full px-3 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:border-[var(--accent-blue)] outline-none transition-colors font-mono text-sm resize-none"
            />
            <p className="mt-1.5 text-xs text-[var(--text-secondary)]">
              Enter parameters as JSON object. These will be the default values when this preset is used.
            </p>
          </div>

          {capabilityId && (
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4">
              <p className="text-xs font-medium text-[var(--text-secondary)] mb-2">
                Example parameters for {capabilityId}:
              </p>
              <pre className="text-xs text-[var(--accent-blue)] font-mono">
                {capabilityId === "indicator_calc" && '{"indicator": "rsi", "period": 14}'}
                {capabilityId === "equity_quote" && '{"exchange": "NASDAQ", "extended_hours": false}'}
                {capabilityId === "equity_history" && '{"interval": "1d", "period": "1y"}'}
                {!["indicator_calc", "equity_quote", "equity_history"].includes(capabilityId) && "{}"}
              </pre>
            </div>
          )}

          {error && (
            <div className="bg-red-900/10 border border-red-500/30 rounded-lg p-3">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
        </form>

        <div className="flex gap-3 p-6 border-t border-[var(--border-color)]">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-2.5 border border-[var(--border-color)] rounded-lg text-sm font-medium text-[var(--text-secondary)] bg-[var(--bg-card)] hover:bg-[var(--bg-panel)] transition-colors"
          >
            {t('cancel')}
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !title || !capabilityId}
            className="flex-1 px-4 py-2.5 border border-transparent rounded-lg text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Creating..." : t('createPreset')}
          </button>
        </div>
      </div>
    </div>
  );
}
