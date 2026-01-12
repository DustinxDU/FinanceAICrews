"use client";

import React, { useState } from "react";
import { Link } from "@/i18n/routing";
import type { Skill } from "@/types/skills";
import {
  X,
  Database,
  Zap,
  Target,
  Layers,
  CheckCircle,
  AlertCircle,
  ExternalLink,
} from "lucide-react";

interface SkillDetailPanelProps {
  skill: Skill;
  onClose: () => void;
  onToggle?: (skill: Skill) => void;
}

const kindIcons = {
  capability: Database,
  preset: Zap,
  strategy: Target,
  skillset: Layers,
};

/**
 * Skill detail panel - Right sidebar in Crew Builder
 *
 * Shows:
 * - Skill description
 * - Parameter schema (args_schema)
 * - Call examples
 * - Failure mode hints
 * - Dependency info + jump button
 *
 * NOTE: Provider priority configuration has been moved to
 * /tools?category=skills → SkillDetailView as it's a global setting.
 */
export function SkillDetailPanel({
  skill,
  onClose,
  onToggle,
}: SkillDetailPanelProps) {
  const [showSchema, setShowSchema] = useState(true);
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
    <div className="h-full flex flex-col bg-[var(--bg-panel)] border-l border-[var(--border-color)]">
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-color)]">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className={`p-2.5 rounded-lg ${kindStyle.bg} border ${kindStyle.border} flex-shrink-0`}>
              <KindIcon className={`w-6 h-6 ${kindStyle.text}`} />
            </div>
            <div className="min-w-0">
              <h3 className="text-lg font-semibold text-[var(--text-primary)] truncate">
                {skill.title}
              </h3>
              <p className="text-xs text-[var(--text-secondary)] truncate">
                {skill.skill_key}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors flex-shrink-0 ml-2"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Status */}
        <div>
          <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block">
            Status
          </label>
          {skill.is_ready ? (
            <div className="flex items-center gap-2 p-3 bg-green-900/20 border border-green-500/30 rounded">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span className="text-sm text-green-400">Available</span>
            </div>
          ) : (
            <div className="p-3 bg-red-900/20 border border-red-500/30 rounded">
              <div className="flex items-center gap-2 mb-2">
                <AlertCircle className="w-4 h-4 text-red-400" />
                <span className="text-sm text-red-400 font-medium">Locked</span>
              </div>
              {skill.blocked_reason && (
                <p className="text-xs text-red-400 mb-2">{skill.blocked_reason}</p>
              )}
              <Link
                href="/tools?category=providers"
                className="flex items-center gap-1 text-xs text-red-400 underline hover:text-red-300"
              >
                <ExternalLink className="w-3 h-3" />
                Go to Tools → Providers to enable
              </Link>
            </div>
          )}
        </div>

        {/* Description */}
        {skill.description && (
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block">
              Description
            </label>
            <p className="text-sm text-[var(--text-primary)]">{skill.description}</p>
          </div>
        )}

        {/* Kind */}
        <div>
          <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block">
            Type
          </label>
          <span className={`inline-flex items-center px-2 py-1 rounded text-sm ${kindStyle.bg} ${kindStyle.text} border ${kindStyle.border}`}>
            {skill.kind}
          </span>
        </div>

        {/* Capability */}
        {skill.capability_id && (
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block">
              Underlying Capability
            </label>
            <code className="text-sm font-mono bg-[var(--bg-card)] px-2 py-1 rounded border border-[var(--border-color)] text-[var(--text-primary)] block">
              {skill.capability_id}
            </code>
            {/* Link to configure priority in Tools page */}
            <Link
              href={`/tools?category=skills`}
              className="flex items-center gap-1 mt-2 text-xs text-blue-400 hover:text-blue-300"
            >
              <ExternalLink className="w-3 h-3" />
              Configure provider priority in Tools → Skills
            </Link>
          </div>
        )}

        {/* Tags */}
        {skill.tags && skill.tags.length > 0 && (
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block">
              Tags
            </label>
            <div className="flex flex-wrap gap-1">
              {skill.tags.map((tag, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)]"
                >
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Parameter Schema */}
        {skill.args_schema && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                Parameter Schema
              </label>
              <button
                onClick={() => setShowSchema(!showSchema)}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                {showSchema ? "Hide" : "Show"}
              </button>
            </div>
            {showSchema && (
              <div className="bg-zinc-900 p-3 rounded border border-zinc-700 overflow-x-auto">
                <pre className="text-xs text-zinc-300 font-mono">
                  {JSON.stringify(skill.args_schema, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Call Examples */}
        {skill.examples && skill.examples.length > 0 && (
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block">
              Call Examples
            </label>
            {skill.examples.map((example, idx) => (
              <div
                key={idx}
                className="mb-2 p-3 bg-blue-900/20 border border-blue-500/30 rounded"
              >
                <pre className="text-xs text-blue-300 font-mono overflow-x-auto">
                  {JSON.stringify(example, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        )}

        {/* Failure Mode Hints */}
        <div>
          <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2 block">
            Failure Handling
          </label>
          <div className="p-3 bg-yellow-900/20 border border-yellow-500/30 rounded">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-yellow-300">
                <p className="font-medium mb-1">When agent call fails:</p>
                <ol className="list-decimal list-inside space-y-1 text-yellow-200/80">
                  <li>Check if parameters match schema requirements</li>
                  <li>Check provider status (Tools → Providers)</li>
                  <li>Retry or fallback to alternative skill</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
