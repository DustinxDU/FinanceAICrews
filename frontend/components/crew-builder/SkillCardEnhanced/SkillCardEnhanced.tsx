"use client";

import React from "react";
import { Link } from "@/i18n/routing";
import type { Skill } from "@/types/skills";
import {
  Check,
  Sparkles,
  Tag,
  ExternalLink,
} from "lucide-react";

interface SkillCardEnhancedProps {
  skill: Skill;
  isSelected: boolean;
  isRecommended?: boolean;
  onToggle: () => void;
  onSelect: () => void;
}

const kindIcons = {
  capability: <span className="text-blue-400">🔧</span>,
  preset: <span className="text-purple-400">⚡</span>,
  strategy: <span className="text-green-400">🎯</span>,
  skillset: <span className="text-orange-400">📦</span>,
};

const kindColors: Record<string, { bg: string; text: string; border: string }> = {
  capability: {
    bg: "bg-blue-900/20",
    text: "text-blue-400",
    border: "border-blue-500/30",
  },
  preset: {
    bg: "bg-purple-900/20",
    text: "text-purple-400",
    border: "border-purple-500/30",
  },
  strategy: {
    bg: "bg-green-900/20",
    text: "text-green-400",
    border: "border-green-500/30",
  },
  skillset: {
    bg: "bg-orange-900/20",
    text: "text-orange-400",
    border: "border-orange-500/30",
  },
};

// Type guard for skill kind
function isValidKind(kind: string): kind is keyof typeof kindColors {
  return kind in kindColors;
}

export function SkillCardEnhanced({
  skill,
  isSelected,
  isRecommended = false,
  onToggle,
  onSelect,
}: SkillCardEnhancedProps) {
  const kindStyle = isValidKind(skill.kind)
    ? kindColors[skill.kind]
    : kindColors.capability;

  // Status indicator
  const StatusIndicator = () => {
    if (skill.is_ready) {
      return (
        <span className="flex items-center gap-1 text-xs text-green-400">
          <span data-testid="status-indicator" className="w-2 h-2 rounded-full bg-green-500" />
          Available
        </span>
      );
    }

    return (
      <span className="flex items-center gap-1 text-xs text-red-400">
        <span data-testid="status-indicator" className="w-2 h-2 rounded-full bg-red-400" />
        Locked
      </span>
    );
  };

  return (
    <div
      onClick={onSelect}
      className={`
        p-4 rounded-lg border cursor-pointer transition-all relative
        ${isSelected
          ? "border-blue-500 bg-blue-900/20"
          : "border-zinc-700 bg-zinc-900 hover:border-zinc-500"
        }
        ${!skill.is_ready ? "opacity-60" : ""}
      `}
    >
      {/* Recommendation tag */}
      {isRecommended && !isSelected && (
        <div className="absolute top-2 right-2 z-10">
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-yellow-900/50 text-yellow-400 border border-yellow-500/30">
            <Sparkles className="w-3 h-3" />
            Recommended
          </div>
        </div>
      )}

      {/* Header: icon + name + status */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div
            data-testid="kind-icon"
            className={`p-2 rounded-lg ${kindStyle.bg} border ${kindStyle.border}`}
          >
            {isValidKind(skill.kind) ? kindIcons[skill.kind] : kindIcons.capability}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-zinc-100 truncate">
              {skill.title}
            </h3>
            <p className="text-[10px] text-zinc-400 truncate">
              {skill.skill_key}
            </p>
          </div>
        </div>

        {/* Selection toggle button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggle();
          }}
          className={`
            w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 ml-2
            ${isSelected
              ? "bg-blue-500 border-blue-500"
              : "border-zinc-600 hover:border-zinc-500"
            }
          `}
        >
          {isSelected && <Check className="w-3 h-3 text-white" />}
        </button>
      </div>

      {/* Description */}
      <p className="text-xs text-zinc-400 line-clamp-2 mb-3">
        {skill.description || "No description"}
      </p>

      {/* Status indicator */}
      <div className="mb-3">
        <StatusIndicator />
      </div>

      {/* Block reason + jump button */}
      {!skill.is_ready && skill.blocked_reason && (
        <div className="p-2 bg-red-900/20 border border-red-500/30 rounded mb-3">
          <p className="text-[10px] text-red-400 mb-1">
            {skill.blocked_reason}
          </p>
          <Link
            href="/tools?tab=providers"
            className="flex items-center gap-1 text-[10px] text-red-400 underline hover:text-red-300"
          >
            <ExternalLink className="w-3 h-3" />
            Enable →
          </Link>
        </div>
      )}

      {/* Tags */}
      {skill.tags && skill.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {skill.tags.slice(0, 3).map((tag, idx) => (
            <span
              key={idx}
              className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-zinc-800 text-zinc-400 border border-zinc-700"
            >
              <Tag className="w-3 h-3 mr-0.5" />
              {tag}
            </span>
          ))}
          {skill.tags.length > 3 && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-zinc-800 text-zinc-400">
              +{skill.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Selected marker (bottom) */}
      {isSelected && (
        <div className="mt-3 pt-3 border-t border-blue-500/30 flex items-center justify-center">
          <span className="text-[10px] text-blue-400">Selected</span>
        </div>
      )}
    </div>
  );
}
