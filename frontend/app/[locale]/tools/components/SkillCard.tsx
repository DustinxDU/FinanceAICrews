"use client";

import React from "react";
import type { Skill, SkillKind } from "@/types/skills";
import { useTranslations } from "next-intl";

import {
  Database,
  Zap,
  Target,
  Layers,
  Tag
} from "lucide-react";

interface SkillCardProps {
  skill: Skill;
  onClick: () => void;
}

const kindIcons: Record<SkillKind, React.ReactNode> = {
  capability: <Database className="w-5 h-5" />,
  preset: <Zap className="w-5 h-5" />,
  strategy: <Target className="w-5 h-5" />,
  skillset: <Layers className="w-5 h-5" />,
};

const kindColors: Record<SkillKind, { bg: string; text: string; border: string }> = {
  capability: { bg: "bg-blue-900/20", text: "text-blue-400", border: "border-blue-500/30" },
  preset: { bg: "bg-purple-900/20", text: "text-purple-400", border: "border-purple-500/30" },
  strategy: { bg: "bg-green-900/20", text: "text-green-400", border: "border-green-500/30" },
  skillset: { bg: "bg-orange-900/20", text: "text-orange-400", border: "border-orange-500/30" },
};

export function SkillCard({
  skill, onClick }: SkillCardProps) {
  const t = useTranslations("tools");
  const kindStyle = kindColors[skill.kind];

  return (
    <div
      onClick={onClick}
      className="bg-[var(--bg-panel)] rounded-lg border border-[var(--border-color)] p-4 hover:shadow-md transition-all cursor-pointer hover:border-[var(--text-secondary)] hover:shadow-black/20"
    >
      {/* Header with Icon and Kind Badge */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 flex-1">
          <div className={`p-2 rounded-lg ${kindStyle.bg} border ${kindStyle.border}`}>
            {kindIcons[skill.kind]}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-[var(--text-primary)] truncate">
              {skill.title}
            </h3>
            <p className="text-xs text-[var(--text-secondary)] truncate">{skill.skill_key}</p>
          </div>
        </div>
        <span
          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${kindStyle.bg} ${kindStyle.text} border ${kindStyle.border}`}
        >
          {skill.kind}
        </span>
      </div>

      {/* Description */}
      <p className="text-sm text-[var(--text-secondary)] mb-3 line-clamp-2">
        {skill.description || "No description provided"}
      </p>

      {/* Tags */}
      {skill.tags && skill.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {skill.tags.slice(0, 3).map((tag, idx) => (
            <span
              key={idx}
              className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)]"
            >
              <Tag className="w-3 h-3 mr-1" />
              {tag}
            </span>
          ))}
          {skill.tags.length > 3 && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[var(--bg-card)] text-[var(--text-secondary)]">
              +{skill.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Footer with Capabilities and Status */}
      <div className="flex items-center justify-between pt-3 border-t border-[var(--border-color)]">
        <div className="text-xs text-[var(--text-secondary)] truncate flex-1">
          <span className="font-medium">Capabilities:</span>{' '}
          {skill.capability_id
            ? skill.capability_id
            : skill.invocation?.required_capabilities?.length
              ? skill.invocation.required_capabilities.slice(0, 3).join(', ') +
                (skill.invocation.required_capabilities.length > 3 ? '...' : '')
              : 'N/A'}
        </div>
        {!skill.is_enabled && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-zinc-800 text-zinc-500">
            Disabled
          </span>
        )}
      </div>
    </div>
  );
}
