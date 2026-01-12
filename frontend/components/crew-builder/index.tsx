"use client";

import React, { useState, useEffect, useCallback } from "react";
import { CrewList } from "./CrewList";
import { BuilderCanvas } from "./BuilderCanvas";
import { ToastProvider } from "./Toast";
import { SavedCrew } from "./types";
import apiClient from "@/lib/api";
import { CrewDefinition, MCPToolDetail, UnifiedTool } from "@/lib/types";

interface CrewBuilderNewProps {
  onCrewCreated?: () => void;
}

export function CrewBuilderNew({ onCrewCreated }: CrewBuilderNewProps) {
  const [currentView, setCurrentView] = useState<'list' | 'builder'>('list');
  const [activeCrewId, setActiveCrewId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [crews, setCrews] = useState<SavedCrew[]>([]);
  const [mcpTools, setMcpTools] = useState<MCPToolDetail[]>([]);

  // Load crews and tools (tolerate 404 by returning empty lists)
  const loadData = useCallback(async () => {
    setIsLoading(true);
    console.log("[CrewBuilder] Loading data...");
    try {
      const [crewsResult, toolsResult] = await Promise.allSettled([
        apiClient.listCrewDefinitions(true), // Include system templates
        apiClient.listUnifiedTools()
      ]);

      console.log("[CrewBuilder] crewsResult:", crewsResult);
      console.log("[CrewBuilder] toolsResult:", toolsResult);

      if (crewsResult.status === "fulfilled") {
        console.log("[CrewBuilder] Raw crews data:", crewsResult.value);
        const mappedCrews: SavedCrew[] = crewsResult.value.map((crew: any) => ({
          id: crew.id,
          name: crew.name,
          description: crew.description || "",
          agents: crew.structure?.filter((s: any) => s.agent_id || s.agentId).length || 0, // Count only agent entries (exclude summary/router)
          lastRun: crew.created_at ? new Date(crew.created_at).toLocaleDateString() : "Never",
          status: 'active' as const,
          isTemplate: crew.is_template || false
        }));
        console.log("[CrewBuilder] Mapped crews:", mappedCrews);
        setCrews(mappedCrews);
      } else {
        console.warn("listCrewDefinitions failed, using empty list:", crewsResult.reason);
        setCrews([]);
      }

      if (toolsResult.status === "fulfilled") {
        // 将新 API 返回的工具列表映射为 MCPToolDetail 格式
        const allTools: MCPToolDetail[] = [];
        toolsResult.value.tiers.forEach(tier => {
          tier.tools.forEach(tool => {
            allTools.push({
              id: allTools.length + 1,  // 生成临时 ID（用于向后兼容）
              server_id: 0,  // 统一工具没有 server_id
              server_key: tool.server_key || tool.key.split(':')[0],
              server_name: tool.server_name || tier.title,
              tool_name: tool.name,
              display_name: tool.name,
              description: tool.description,
              category: tool.category,
              input_schema: null,  // 统一工具没有 input_schema
              requires_api_key: tool.requires_api_key,
              api_key_provider: tool.api_key_provider,
              is_active: tool.is_active,
              tags: null,
              user_enabled: tool.user_enabled,
              user_configured: tool.is_configured,
              is_validated: tool.is_configured,
            });
          });
        });
        setMcpTools(allTools);
      } else {
        console.warn("listUnifiedTools failed, using empty tools:", toolsResult.reason);
        setMcpTools([]);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSelectCrew = (id: number | 'new') => {
    if (id === 'new') {
      setActiveCrewId(null);
    } else {
      setActiveCrewId(id);
    }
    setCurrentView('builder');
  };

  const handleBackToList = () => {
    setCurrentView('list');
    setActiveCrewId(null);
  };

  const handleSaveCrew = async (crewData: any) => {
    setIsLoading(true);
    try {
      if (activeCrewId) {
        await apiClient.updateCrewDefinition(activeCrewId, crewData);
      } else {
        await apiClient.createCrewDefinition(crewData);
      }
      await loadData();
      setCurrentView('list');
      onCrewCreated?.();
    } catch (err) {
      console.error("Failed to save crew:", err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteCrew = async (crewId?: number | null) => {
    if (!crewId) return;
    setIsLoading(true);
    try {
      await apiClient.deleteCrewDefinition(crewId);
      await loadData();
      setCurrentView('list');
      setActiveCrewId(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ToastProvider>
      {currentView === 'list' && (
        <CrewList 
          crews={crews} 
          onSelectCrew={handleSelectCrew} 
          isLoading={isLoading}
        />
      )}
      {currentView === 'builder' && (
        <BuilderCanvas 
          onBack={handleBackToList}
          onSave={handleSaveCrew}
          onDelete={() => handleDeleteCrew(activeCrewId)}
          mcpTools={mcpTools}
          isLoading={isLoading}
          crewId={activeCrewId}
        />
      )}
    </ToastProvider>
  );
}

// Re-export components for external use
export { CrewList } from "./CrewList";
export { BuilderCanvas } from "./BuilderCanvas";
export { ToastProvider, useToast } from "./Toast";
export * from "./types";
export * from "./constants";
