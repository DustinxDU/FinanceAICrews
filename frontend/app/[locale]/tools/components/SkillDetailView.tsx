"use client";

import React, { useState, useEffect, useCallback } from "react";
import type { Skill, CapabilityProviderInfo } from "@/types/skills";
import { useTranslations } from "next-intl";
import { apiClient } from "@/lib/api";
import { Link } from "@/i18n/routing";

import {
  X,
  Database,
  Zap,
  Target,
  Layers,
  Check,
  AlertCircle,
  Code,
  FileText,
  GripVertical,
  Server,
  Loader2,
  Save,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

/**
 * Provider Priority Configuration Component
 *
 * Displays all providers implementing a capability and allows
 * users to adjust their routing priority (higher = tried first).
 *
 * This is a GLOBAL configuration - changes affect all Crews.
 */
function ProviderPriorityConfig({ capabilityId }: { capabilityId: string }) {
  const [providers, setProviders] = useState<CapabilityProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [originalPriorities, setOriginalPriorities] = useState<Map<number, number>>(new Map());

  const fetchProviders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getCapabilityProviders(capabilityId);
      setProviders(response.providers);
      // Store original priorities for change detection
      const priorities = new Map<number, number>();
      response.providers.forEach((p: CapabilityProviderInfo) => priorities.set(p.provider_id, p.priority));
      setOriginalPriorities(priorities);
      setHasChanges(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load providers");
    } finally {
      setLoading(false);
    }
  }, [capabilityId]);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const handlePriorityChange = (providerId: number, newPriority: number) => {
    // Clamp to 0-100
    const clampedPriority = Math.max(0, Math.min(100, newPriority));

    setProviders(prev => {
      const updated = prev.map(p =>
        p.provider_id === providerId ? { ...p, priority: clampedPriority } : p
      );
      // Re-sort by priority (descending)
      return updated.sort((a, b) => b.priority - a.priority);
    });

    // Check if there are changes
    setHasChanges(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const priorities = providers.map(p => ({
        provider_id: p.provider_id,
        priority: p.priority,
      }));
      await apiClient.updateCapabilityPriorities(capabilityId, priorities);
      // Update original priorities after successful save
      const newOriginal = new Map<number, number>();
      providers.forEach(p => newOriginal.set(p.provider_id, p.priority));
      setOriginalPriorities(newOriginal);
      setHasChanges(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save priorities");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setProviders(prev =>
      prev
        .map(p => ({ ...p, priority: originalPriorities.get(p.provider_id) ?? p.priority }))
        .sort((a, b) => b.priority - a.priority)
    );
    setHasChanges(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-4">
        <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
        <span className="ml-2 text-sm text-[var(--text-secondary)]">Loading providers...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-3 bg-red-900/20 border border-red-500/30 rounded">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <span className="text-sm text-red-400">{error}</span>
        </div>
        <button
          onClick={fetchProviders}
          className="mt-2 text-xs text-red-400 underline hover:text-red-300"
        >
          Retry
        </button>
      </div>
    );
  }

  if (providers.length === 0) {
    return (
      <div className="p-3 bg-zinc-800/50 border border-zinc-700 rounded">
        <p className="text-sm text-[var(--text-secondary)]">
          No providers implement this capability yet.
        </p>
        <Link
          href="/tools?category=providers"
          className="flex items-center gap-1 mt-2 text-xs text-blue-400 underline hover:text-blue-300"
        >
          <ExternalLink className="w-3 h-3" />
          Configure providers
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Global config notice */}
      <div className="p-2 bg-blue-900/20 border border-blue-500/30 rounded">
        <p className="text-xs text-blue-300">
          <strong>Global Setting:</strong> Priority changes apply to all Crews using this capability.
        </p>
      </div>

      {/* Provider List */}
      <div className="space-y-2">
        {providers.map((provider, index) => (
          <div
            key={provider.provider_id}
            className="flex items-center gap-3 p-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded group hover:border-blue-500/30 transition-colors"
          >
            {/* Rank indicator */}
            <div className="flex items-center justify-center w-6 h-6 rounded bg-zinc-700 text-xs font-mono text-zinc-300">
              {index + 1}
            </div>

            {/* Drag handle (visual only for now) */}
            <GripVertical className="w-4 h-4 text-zinc-500 cursor-grab" />

            {/* Provider info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <Server className="w-3.5 h-3.5 text-zinc-400" />
                <span className="text-sm font-medium text-[var(--text-primary)] truncate">
                  {provider.provider_key}
                </span>
                {/* Health indicator */}
                <span
                  className={`w-2 h-2 rounded-full ${
                    provider.healthy ? "bg-green-400" : "bg-red-400"
                  }`}
                  title={provider.healthy ? "Healthy" : "Unhealthy"}
                />
              </div>
              {provider.raw_tool_name && (
                <p className="text-xs text-[var(--text-secondary)] truncate mt-0.5">
                  → {provider.raw_tool_name}
                </p>
              )}
            </div>

            {/* Priority input */}
            <div className="flex items-center gap-1">
              <input
                type="number"
                min={0}
                max={100}
                value={provider.priority}
                onChange={(e) =>
                  handlePriorityChange(provider.provider_id, parseInt(e.target.value) || 0)
                }
                className="w-14 px-2 py-1 text-sm text-center bg-zinc-800 border border-zinc-600 rounded focus:border-blue-500 focus:outline-none text-[var(--text-primary)]"
              />
              <span className="text-xs text-[var(--text-secondary)]">%</span>
            </div>
          </div>
        ))}
      </div>

      {/* Action buttons */}
      {hasChanges && (
        <div className="flex items-center gap-2 pt-2 border-t border-[var(--border-color)]">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded transition-colors"
          >
            {saving ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            Save
          </button>
          <button
            onClick={handleReset}
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Reset
          </button>
        </div>
      )}

      {/* Help text */}
      <p className="text-xs text-[var(--text-secondary)]">
        Higher priority (0-100) = tried first. Drag to reorder or edit values directly.
      </p>
    </div>
  );
}

interface SkillDetailViewProps {
  skill: Skill;
  onClose: () => void;
  onToggleActive?: (skillKey: string, currentState: boolean) => void;
}

const kindIcons = {
  capability: Database,
  preset: Zap,
  strategy: Target,
  skillset: Layers,
};

export function SkillDetailView({
  skill,
  onClose,
  onToggleActive,
}: SkillDetailViewProps) {
  const t = useTranslations("tools");
  const KindIcon = kindIcons[skill.kind];

  const getKindStyle = (kind: string) => {
    switch (kind) {
      case "capability":
        return { bg: "bg-blue-900/20", text: "text-blue-400", border: "border-blue-500/30" };
      case "preset":
        return { bg: "bg-purple-900/20", text: "text-purple-400", border: "border-purple-500/30" };
      case "strategy":
        return { bg: "bg-green-900/20", text: "text-green-400", border: "border-green-500/30" };
      case "skillset":
        return { bg: "bg-orange-900/20", text: "text-orange-400", border: "border-orange-500/30" };
      default:
        return { bg: "bg-zinc-800", text: "text-zinc-400", border: "border-zinc-700" };
    }
  };

  const kindStyle = getKindStyle(skill.kind);

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-[var(--bg-panel)] shadow-xl border-l border-[var(--border-color)] overflow-y-auto z-50 animate-in slide-in-from-right duration-300">
      <div className="p-6">
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-lg ${kindStyle.bg} border ${kindStyle.border}`}>
              <KindIcon className={`w-6 h-6 ${kindStyle.text}`} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                {skill.title}
              </h3>
              <p className="text-sm text-[var(--text-secondary)]">{skill.skill_key}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-5">
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-1 block">
              Kind
            </label>
            <p className="text-[var(--text-primary)] capitalize">{skill.kind}</p>
          </div>

          {/* Capabilities Section - show capability_id OR required_capabilities */}
          {(skill.capability_id || skill.invocation?.required_capabilities?.length > 0) && (
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-1 block">
                {skill.capability_id ? 'Capability' : 'Required Capabilities'}
              </label>
              <div className="flex flex-wrap gap-2">
                {skill.capability_id ? (
                  <code className="text-sm font-mono bg-[var(--bg-card)] px-2 py-1 rounded border border-[var(--border-color)] text-[var(--text-primary)]">
                    {skill.capability_id}
                  </code>
                ) : (
                  skill.invocation?.required_capabilities?.map((cap: string, idx: number) => (
                    <code key={idx} className="text-sm font-mono bg-[var(--bg-card)] px-2 py-1 rounded border border-[var(--border-color)] text-[var(--text-primary)]">
                      {cap}
                    </code>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Provider Priority Configuration - Only for capability-based skills */}
          {skill.capability_id && (
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block">
                Provider Routing Priority
              </label>
              <ProviderPriorityConfig capabilityId={skill.capability_id} />
            </div>
          )}

          {skill.description && (
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-1 block">
                Description
              </label>
              <p className="text-[var(--text-primary)] text-sm">{skill.description}</p>
            </div>
          )}

          {skill.tags && skill.tags.length > 0 && (
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block">
                Tags
              </label>
              <div className="flex flex-wrap gap-2">
                {skill.tags.map((tag, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)]"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {skill.args_schema && (
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block flex items-center gap-2">
                <Code className="w-4 h-4" />
                Arguments Schema
              </label>
              <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]">
                <pre className="text-xs text-[var(--text-primary)] overflow-x-auto">
                  {JSON.stringify(skill.args_schema, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {skill.examples && skill.examples.length > 0 && (
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Examples
              </label>
              <div className="space-y-2">
                {skill.examples.map((example, idx) => (
                  <div
                    key={idx}
                    className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]"
                  >
                    <p className="text-sm text-[var(--text-primary)]">
                      {typeof example === "string" ? example : JSON.stringify(example)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!skill.is_ready && skill.blocked_reason && (
            <div className="bg-yellow-900/10 rounded-lg p-3 border border-yellow-900/30">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-yellow-400 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-yellow-200">Skill Blocked</p>
                  <p className="text-sm text-yellow-400/80 mt-1">{skill.blocked_reason}</p>
                </div>
              </div>
            </div>
          )}

          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block">
              {t('status')}
            </label>
            <div className="flex gap-2 flex-wrap">
              {skill.is_enabled ? (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-900/20 text-green-400 border border-green-900/30">
                  <Check className="w-4 h-4 mr-1" />
                  Enabled
                </span>
              ) : (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
                  <X className="w-4 h-4 mr-1" />
                  Disabled
                </span>
              )}
              {skill.is_ready ? (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-[var(--accent-blue)]/10 text-[var(--accent-blue)] border border-[var(--accent-blue)]/20">
                  Ready
                </span>
              ) : (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-900/20 text-yellow-400 border border-yellow-900/30">
                  {t('notReady')}
                </span>
              )}
            </div>
          </div>

          {skill.is_system && (
            <div className="bg-[var(--accent-blue)]/5 rounded-lg p-3 border border-[var(--accent-blue)]/10">
              <p className="text-sm text-[var(--accent-blue)]">
                <span className="font-medium">{t('systemSkill')}</span> - This skill is provided by the system.
              </p>
            </div>
          )}
        </div>

        <div className="mt-6 pt-6 border-t border-[var(--border-color)] space-y-3">
          {onToggleActive && (
            <button
              onClick={() => onToggleActive(skill.skill_key, skill.is_enabled)}
              className="w-full px-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--bg-panel)] transition-colors flex items-center justify-center gap-2"
            >
              {skill.is_enabled ? "Disable Skill" : "Enable Skill"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
