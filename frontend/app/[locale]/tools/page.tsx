"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { AppLayout } from "@/components/layout";
import { useTranslations } from "next-intl";

import { withAuth } from "@/contexts/AuthContext";
import {
  Loader2,
  Database,
  Sparkles,
  BookOpen,
} from "lucide-react";
import {
  ProvidersTab,
  SkillsTab,
  KnowledgeTab,
} from "./components";

type MainTabType = "providers" | "skills" | "knowledge";

function ToolsPage() {
  const t = useTranslations("tools");
  const searchParams = useSearchParams();
  const categoryParam = searchParams.get("category");

  // Initialize activeMainTab from URL param or default to "providers"
  const [activeMainTab, setActiveMainTab] = useState<MainTabType>(() => {
    if (categoryParam === "knowledge") return "knowledge";
    if (categoryParam === "skills") return "skills";
    return "providers";
  });
  const [loading, setLoading] = useState(false);

  // Update tab when URL param changes
  useEffect(() => {
    if (categoryParam === "knowledge") setActiveMainTab("knowledge");
    else if (categoryParam === "skills") setActiveMainTab("skills");
    else if (categoryParam === "providers") setActiveMainTab("providers");
  }, [categoryParam]);

  if (loading) {
    return (
      <AppLayout>
        <div className="p-8 max-w-7xl mx-auto animate-in fade-in duration-500">
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
            <span className="ml-3 text-sm text-[var(--text-secondary)]">{t('loading')}</span>
          </div>
        </div>
      </AppLayout>
    );
  }

  const mainTabs = [
    { key: "providers" as MainTabType, label: "Providers", icon: Database },
    { key: "skills" as MainTabType, label: "Skills", icon: Sparkles },
    { key: "knowledge" as MainTabType, label: "Knowledge", icon: BookOpen },
  ];

  const getDescription = () => {
    switch (activeMainTab) {
      case "providers":
        return "Configure data providers and map their tools to standard capabilities.";
      case "skills":
        return "Browse and manage skills built on capabilities.";
      case "knowledge":
        return "Discover, add, and manage knowledge packs for your AI agents.";
      default:
        return "";
    }
  };

  return (
    <AppLayout>
      <div className="p-8 max-w-7xl mx-auto animate-in fade-in duration-500 min-h-screen">
        <div className="flex justify-between items-end mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">Capability Management</h1>
            <p className="text-[var(--text-secondary)]">{getDescription()}</p>
          </div>
        </div>

        {/* Main Tab Navigation */}
        <div className="mb-6 border-b border-[var(--border-color)]">
          <div className="flex gap-1">
            {mainTabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveMainTab(tab.key)}
                  className={`px-6 py-3 font-medium text-sm transition-all flex items-center gap-2 border-b-2 ${
                    activeMainTab === tab.key
                      ? "border-[var(--accent-blue)] text-[var(--accent-blue)]"
                      : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-color)]"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Tab Content */}
        {activeMainTab === "providers" ? (
          <ProvidersTab />
        ) : activeMainTab === "skills" ? (
          <SkillsTab />
        ) : (
          <KnowledgeTab />
        )}
      </div>
    </AppLayout>
  );
}

export default withAuth(ToolsPage);
