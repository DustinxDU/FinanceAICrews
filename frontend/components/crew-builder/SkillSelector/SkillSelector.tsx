"use client";

import React, { useState, useMemo } from "react";
import { Search, Loader2, Zap, Target, Workflow, Database } from "lucide-react";
import type { Skill, SkillKind } from "@/types/skills";
import { useSkillCatalog } from "@/hooks/useSkillCatalog";
import { SkillCardEnhanced } from "../SkillCardEnhanced/SkillCardEnhanced";
import { SkillDetailPanel } from "../SkillDetailPanel";

interface SkillSelectorProps {
  // Current selection
  selectedSkillKeys: string[];

  // Event callbacks
  onChange: (skillKeys: string[]) => void;
  onClose?: () => void;
}

/**
 * Three-panel skill selector
 *
 * Left: Kind navigation (Presets | Strategies | Workflows | Capabilities)
 * Middle: Skill card list (with search, filter)
 * Right: Detail panel (full skill info)
 */
export function SkillSelector({
  selectedSkillKeys = [],
  onChange,
  onClose,
}: SkillSelectorProps) {
  const [activeKind, setActiveKind] = useState<SkillKind>("preset");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);

  // Load skill catalog
  const { catalog, allSkills, isLoading, isError } = useSkillCatalog();

  // Map kind to catalog key (handle irregular plurals) - defined outside for reuse
  const kindKeyMap: Record<SkillKind, string> = {
    capability: 'capabilities',
    preset: 'presets',
    strategy: 'strategies',  // Special case: strategies not strategys
    skillset: 'skillsets',
  };

  // Filter skills by Kind + Search
  const filteredSkills = useMemo(() => {
    if (!catalog) return [];

    const kindKey = kindKeyMap[activeKind] || `${activeKind}s`;
    const kindSkills = catalog[kindKey as keyof typeof catalog] || [];

    return kindSkills.filter((skill) => {
      if (!searchQuery) return true;

      const query = searchQuery.toLowerCase();
      return (
        skill.title.toLowerCase().includes(query) ||
        skill.skill_key.toLowerCase().includes(query) ||
        skill.description?.toLowerCase().includes(query) ||
        skill.tags.some((tag: string) => tag.toLowerCase().includes(query))
      );
    });
  }, [catalog, activeKind, searchQuery]);

  // Toggle skill selection
  const handleToggleSkill = (skillKey: string) => {
    const isSelected = selectedSkillKeys.includes(skillKey);
    const newKeys = isSelected
      ? selectedSkillKeys.filter(k => k !== skillKey)
      : [...selectedSkillKeys, skillKey];

    onChange(newKeys);
  };

  // Kind filter configuration
  const kindFilters = [
    { key: "preset" as SkillKind, label: "Presets", icon: Zap, color: "purple" },
    { key: "skillset" as SkillKind, label: "Skillsets", icon: Workflow, color: "orange" },
    { key: "strategy" as SkillKind, label: "Strategies", icon: Target, color: "green" },
    { key: "capability" as SkillKind, label: "Capabilities", icon: Database, color: "blue" },
  ];

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
        <span className="ml-3 text-sm text-[var(--text-secondary)]">Loading skill catalog...</span>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-sm text-red-400 mb-2">Failed to load</p>
          <button
            onClick={() => window.location.reload()}
            className="text-xs px-3 py-1 bg-red-900/30 text-red-400 rounded border border-red-500/30"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left: Kind Navigation */}
      <div className="w-48 border-r border-[var(--border-color)] p-4">
        <h3 className="text-xs font-bold uppercase text-[var(--text-secondary)] mb-4">
          Skill Types
        </h3>
        <div className="space-y-2">
          {kindFilters.map((filter) => {
            const Icon = filter.icon;
            const isActive = activeKind === filter.key;
            const kindKey = kindKeyMap[filter.key] || `${filter.key}s`;
            const count = catalog?.[kindKey as keyof typeof catalog]?.length || 0;

            return (
              <button
                key={filter.key}
                onClick={() => setActiveKind(filter.key)}
                className={`
                  w-full flex items-center gap-2 px-3 py-2 rounded text-sm transition-all
                  ${isActive
                    ? "bg-blue-900/30 text-blue-400 border border-blue-500/30"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-zinc-800"
                  }
                `}
              >
                <Icon className="w-4 h-4" />
                <span className="flex-1 text-left">{filter.label}</span>
                <span className="text-xs opacity-60">({count})</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Middle: Skill List */}
      <div className="flex-1 p-4 overflow-y-auto">
        {/* Search box */}
        <div className="mb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-[var(--text-secondary)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search skills..."
              className="w-full pl-10 pr-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded text-sm text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {/* Skill card grid */}
        {filteredSkills.length === 0 ? (
          <div className="text-center py-12 text-[var(--text-secondary)]">
            <p className="text-sm">No matching skills found</p>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="text-xs text-blue-400 underline mt-2"
              >
                Clear search
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {filteredSkills.map((skill) => (
              <SkillCardEnhanced
                key={skill.skill_key}
                skill={skill}
                isSelected={selectedSkillKeys.includes(skill.skill_key)}
                onToggle={() => handleToggleSkill(skill.skill_key)}
                onSelect={() => setSelectedSkill(skill)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Right: Detail Panel */}
      <div className="w-80 border-l border-[var(--border-color)]">
        {selectedSkill ? (
          <SkillDetailPanel
            skill={selectedSkill}
            onClose={() => setSelectedSkill(null)}
            onToggle={(skill) => handleToggleSkill(skill.skill_key)}
          />
        ) : (
          <div className="h-full flex items-center justify-center p-4 text-center">
            <div>
              <Database className="w-12 h-12 text-[var(--text-secondary)] mx-auto mb-3" />
              <p className="text-sm text-[var(--text-secondary)]">
                Select a skill to view details
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
