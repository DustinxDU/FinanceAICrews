"use client";

import React, { useState } from "react";
import { X, Zap, Target, Layers, HelpCircle, Plus, Trash2 } from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import { ALL_CAPABILITIES, CAPABILITY_METADATA } from "@/lib/taxonomy";
import type { SkillKind } from "@/types/skills";

interface CreateSkillModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

type SkillType = 'preset' | 'strategy' | 'skillset';

const SKILL_TYPE_CONFIG: Record<SkillType, {
  label: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  borderColor: string;
  description: string;
}> = {
  preset: {
    label: "Preset",
    icon: <Zap className="w-5 h-5" />,
    color: "text-purple-400",
    bgColor: "bg-purple-900/20",
    borderColor: "border-purple-500/30",
    description: "Reusable skill template with predefined parameters for a single capability.",
  },
  strategy: {
    label: "Strategy",
    icon: <Target className="w-5 h-5" />,
    color: "text-green-400",
    bgColor: "bg-green-900/20",
    borderColor: "border-green-500/30",
    description: "Trading rule or formula that can be evaluated against market data.",
  },
  skillset: {
    label: "Skillset",
    icon: <Layers className="w-5 h-5" />,
    color: "text-orange-400",
    bgColor: "bg-orange-900/20",
    borderColor: "border-orange-500/30",
    description: "Bundle of multiple capabilities for a specific analysis workflow.",
  },
};

export function CreateSkillModal({
  isOpen,
  onClose,
  onSuccess
}: CreateSkillModalProps) {
  const t = useTranslations("tools");
  const [skillType, setSkillType] = useState<SkillType>('preset');
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Preset-specific state
  const [capabilityId, setCapabilityId] = useState("");
  const [defaultsJson, setDefaultsJson] = useState("{}");

  // Strategy-specific state
  const [formula, setFormula] = useState("");

  // Skillset specific state
  const [selectedCapabilities, setSelectedCapabilities] = useState<string[]>([]);

  const config = SKILL_TYPE_CONFIG[skillType];

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setCapabilityId("");
    setDefaultsJson("{}");
    setFormula("");
    setSelectedCapabilities([]);
    setError(null);
  };

  const handleTypeChange = (type: SkillType) => {
    setSkillType(type);
    resetForm();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      let skill_key: string;
      let invocation: Record<string, any>;
      let kind: SkillKind;

      if (skillType === 'preset') {
        // Validate JSON
        try {
          JSON.parse(defaultsJson);
        } catch {
          setError("Invalid JSON in default parameters");
          setLoading(false);
          return;
        }

        skill_key = `preset:${title.toLowerCase().replace(/\s+/g, "_")}`;
        kind = 'preset';
        invocation = {
          capability_id: capabilityId,
          defaults: JSON.parse(defaultsJson),
          required_capabilities: [capabilityId],
        };
      } else if (skillType === 'strategy') {
        skill_key = `strategy:${title.toLowerCase().replace(/\s+/g, "_")}`;
        kind = 'strategy';
        invocation = {
          type: 'strategy',
          formula: formula,
          required_capabilities: ['equity_history', 'indicator_calc', 'strategy_eval'],
        };
      } else {
        // Skillset
        if (selectedCapabilities.length === 0) {
          setError("Please select at least one capability");
          setLoading(false);
          return;
        }
        skill_key = `skillset:${title.toLowerCase().replace(/\s+/g, "_")}`;
        kind = 'skillset';
        invocation = {
          required_capabilities: selectedCapabilities,
        };
      }

      await apiClient.createSkill({
        skill_key,
        kind,
        capability_id: skillType === 'preset' ? capabilityId : undefined,
        title,
        description,
        invocation,
        args_schema: null,
      });

      resetForm();
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || `Failed to create ${skillType}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleCapability = (cap: string) => {
    setSelectedCapabilities(prev =>
      prev.includes(cap) ? prev.filter(c => c !== cap) : [...prev, cap]
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
      <div className="bg-[var(--bg-panel)] rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-3">
            <div className={`p-2 ${config.bgColor} rounded-lg border ${config.borderColor}`}>
              {config.icon}
            </div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">{t('createSkill')}</h2>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* {t('type')} Selector */}
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-3">
              Skill {t('type')} <span className="text-red-400">*</span>
            </label>
            <div className="grid grid-cols-3 gap-3">
              {(Object.keys(SKILL_TYPE_CONFIG) as SkillType[]).map((type) => {
                const typeConfig = SKILL_TYPE_CONFIG[type];
                const isSelected = skillType === type;
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => handleTypeChange(type)}
                    className={`p-4 rounded-lg border-2 transition-all text-left ${
                      isSelected
                        ? `${typeConfig.bgColor} ${typeConfig.borderColor.replace('/30', '')} ${typeConfig.color}`
                        : 'border-[var(--border-color)] hover:border-[var(--text-secondary)]'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {typeConfig.icon}
                      <span className="font-medium">{typeConfig.label}</span>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] line-clamp-2">
                      {type === 'skillset' ? 'Capability bundle' : typeConfig.label}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* {t('type')} Description */}
          <div className={`${config.bgColor} border ${config.borderColor} rounded-lg p-4`}>
            <div className="flex items-start gap-2.5">
              <HelpCircle className={`w-4 h-4 ${config.color} mt-0.5 flex-shrink-0`} />
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                {config.description}
              </p>
            </div>
          </div>

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              Title <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={
                skillType === 'preset' ? "e.g., RSI(14), MACD Default" :
                skillType === 'strategy' ? "e.g., Golden Cross, RSI Oversold" :
                "e.g., Fundamental Analysis Skillset"
              }
              required
              className="w-full px-3 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:border-[var(--accent-blue)] outline-none transition-colors"
            />
            {title && (
              <p className="mt-1.5 text-xs text-[var(--text-secondary)]">
                Skill key:{" "}
                <code className={`${config.color} font-mono`}>
                  {skillType === 'skillset'
                    ? `skillset:${title.toLowerCase().replace(/\s+/g, "_")}`
                    : `${skillType}:${title.toLowerCase().replace(/\s+/g, "_")}`}
                </code>
              </p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe this skill and when to use it"
              rows={2}
              className="w-full px-3 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:border-[var(--accent-blue)] outline-none transition-colors resize-none"
            />
          </div>

          {/* {t('type')}-specific fields */}
          {skillType === 'preset' && (
            <>
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
                    return (
                      <option key={cap} value={cap}>
                        {meta.display_name || cap} ({cap})
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
                  onChange={(e) => setDefaultsJson(e.target.value)}
                  placeholder='{"indicator": "rsi", "period": 14}'
                  rows={4}
                  className="w-full px-3 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:border-[var(--accent-blue)] outline-none transition-colors font-mono text-sm resize-none"
                />
              </div>
            </>
          )}

          {skillType === 'strategy' && (
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                Strategy Formula <span className="text-red-400">*</span>
              </label>
              <textarea
                value={formula}
                onChange={(e) => setFormula(e.target.value)}
                placeholder="e.g., SMA(50) > SMA(200) AND RSI(14) < 30"
                rows={4}
                required
                className="w-full px-3 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:border-[var(--accent-blue)] outline-none transition-colors font-mono text-sm resize-none"
              />
              <p className="mt-1.5 text-xs text-[var(--text-secondary)]">
                Use indicators like SMA(), EMA(), RSI(), MACD() with comparison operators.
              </p>
            </div>
          )}

          {skillType === 'skillset' && (
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                Required Capabilities <span className="text-red-400">*</span>
                <span className="ml-2 text-xs font-normal">({selectedCapabilities.length} selected)</span>
              </label>
              <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto p-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg">
                {ALL_CAPABILITIES.map((cap) => {
                  const meta = CAPABILITY_METADATA[cap] || {};
                  const isSelected = selectedCapabilities.includes(cap);
                  return (
                    <button
                      key={cap}
                      type="button"
                      onClick={() => toggleCapability(cap)}
                      className={`p-2 rounded text-left text-sm transition-all ${
                        isSelected
                          ? 'bg-orange-900/30 border border-orange-500/50 text-orange-300'
                          : 'hover:bg-[var(--bg-panel)] border border-transparent'
                      }`}
                    >
                      {meta.display_name || cap}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-900/10 border border-red-500/30 rounded-lg p-3">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
        </form>

        {/* Footer */}
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
            disabled={loading || !title || (skillType === 'preset' && !capabilityId) || (skillType === 'strategy' && !formula) || (skillType === 'skillset' && selectedCapabilities.length === 0)}
            className={`flex-1 px-4 py-2.5 border border-transparent rounded-lg text-sm font-medium text-white ${
              skillType === 'preset' ? 'bg-purple-600 hover:bg-purple-700' :
              skillType === 'strategy' ? 'bg-green-600 hover:bg-green-700' :
              'bg-orange-600 hover:bg-orange-700'
            } disabled:opacity-50 disabled:cursor-not-allowed transition-colors`}
          >
            {loading ? "Creating..." : `Create ${config.label}`}
          </button>
        </div>
      </div>
    </div>
  );
}
