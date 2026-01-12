"use client";

import React, { useState, useEffect } from "react";
import { Plus, RefreshCw, Loader2, Search, Filter } from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import type { Skill, SkillKind } from "@/types/skills";
import { SkillCard } from "./SkillCard";
import { SkillDetailView } from "./SkillDetailView";
import { CreateSkillModal } from "./CreateSkillModal";

export function SkillsTab() {
  const t = useTranslations("tools");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [activeKindFilter, setActiveKindFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const [isCreateSkillOpen, setIsCreateSkillOpen] = useState(false);

  useEffect(() => {
    loadSkills();
  }, [activeKindFilter, searchQuery]);

  const loadSkills = async () => {
    try {
      setLoading(true);
      const params: { kind?: string; search?: string } = {};

      if (activeKindFilter !== "all") {
        params.kind = activeKindFilter;
      }

      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }

      const data = await apiClient.listSkills(params);
      setSkills(data);
    } catch (error) {
      console.error("Failed to load skills:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSkillCreated = () => {
    loadSkills();
  };

  const handleToggleActive = async (skillKey: string, currentState: boolean) => {
    try {
      await apiClient.toggleSkill(skillKey, !currentState);

      setSkills((prev) =>
        prev.map((s) =>
          s.skill_key === skillKey ? { ...s, is_enabled: !currentState } : s
        )
      );

      if (selectedSkill?.skill_key === skillKey) {
        setSelectedSkill((prev) =>
          prev ? { ...prev, is_enabled: !currentState } : null
        );
      }
    } catch (error) {
      console.error("Failed to toggle skill:", error);
      alert("Failed to toggle skill status");
    }
  };

  const kindFilters = [
    { key: "all", label: "All Skills" },
    { key: "capability", label: "Capabilities" },
    { key: "preset", label: "Presets" },
    { key: "strategy", label: "Strategies" },
    { key: "skillset", label: "Skillsets" },
  ];

  const filteredSkills = skills;

  const systemSkillsCount = skills.filter((s) => s.is_system).length;
  const userSkillsCount = skills.filter((s) => !s.is_system).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">
            Skills Catalog
          </h2>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            {systemSkillsCount} system skills, {userSkillsCount} custom skills
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadSkills}
            className="px-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-sm hover:text-white text-[var(--text-secondary)] transition-colors flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={() => setIsCreateSkillOpen(true)}
            className="px-4 py-2 bg-[var(--accent-blue)] hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            {t('createSkill')}
          </button>
        </div>
      </div>

      <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex gap-2 flex-wrap">
            {kindFilters.map((filter) => (
              <button
                key={filter.key}
                onClick={() => setActiveKindFilter(filter.key)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeKindFilter === filter.key
                    ? "bg-[var(--accent-blue)] text-white"
                    : "bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]"
                }`}
              >
                {filter.label}
              </button>
            ))}
          </div>

          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-secondary)]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search skills..."
                className="w-full pl-10 pr-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-sm focus:border-[var(--accent-blue)] outline-none"
              />
            </div>
          </div>
        </div>
      </div>

      {filteredSkills.length === 0 ? (
        <div className="text-center py-12 bg-[var(--bg-card)] border border-dashed border-[var(--border-color)] rounded-xl">
          <Filter className="w-12 h-12 mx-auto text-[var(--text-secondary)] mb-4" />
          <h3 className="text-lg font-medium text-[var(--text-primary)] mb-2">
            {t('noSkillsFound')}
          </h3>
          <p className="text-sm text-[var(--text-secondary)] mb-4">
            {searchQuery || activeKindFilter !== "all"
              ? "Try adjusting your filters or search query"
              : "Create your first skill to get started"}
          </p>
          {!searchQuery && activeKindFilter === "all" && (
            <button
              onClick={() => setIsCreateSkillOpen(true)}
              className="px-4 py-2 bg-[var(--accent-blue)] hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 mx-auto"
            >
              <Plus className="w-4 h-4" />
              Create Your First Skill
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSkills.map((skill) => (
            <SkillCard
              key={skill.skill_key}
              skill={skill}
              onClick={() => setSelectedSkill(skill)}
            />
          ))}
        </div>
      )}

      {selectedSkill && (
        <SkillDetailView
          skill={selectedSkill}
          onClose={() => setSelectedSkill(null)}
          onToggleActive={handleToggleActive}
        />
      )}

      <CreateSkillModal
        isOpen={isCreateSkillOpen}
        onClose={() => setIsCreateSkillOpen(false)}
        onSuccess={handleSkillCreated}
      />
    </div>
  );
}
