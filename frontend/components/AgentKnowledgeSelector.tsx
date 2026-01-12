"use client";

import { useState, useCallback } from "react";
import { Link } from "@/i18n/routing";
import useSWR from "swr";
import {
  BookOpen,
  Plus,
  X,
  Check,
  ChevronDown,
  History,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { getToken } from "@/lib/auth";
import { buildApiUrl } from "@/lib/apiClient";

const fetcher = async (url: string) => {
  const token = getToken();
  if (!token) throw new Error("No token");
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch");
  return res.json();
};

interface KnowledgeSource {
  id: number;
  source_key: string;
  display_name: string;
  description?: string;
  category: string;
  knowledge_scope: string;  // crew, agent, both
  source_type: string;
}

interface AgentKnowledgeSelectorProps {
  agentName: string;
  crewName: string;
  selectedSourceIds?: number[];
  selectedUserSourceIds?: number[];
  includeTradingLessons?: boolean;
  onSelectionChange?: (config: AgentKnowledgeConfig) => void;
}

export interface AgentKnowledgeConfig {
  agent_name: string;
  source_ids: number[];
  user_source_ids: number[];
  include_trading_lessons: boolean;
  max_lessons: number;
}

const getCategoryColor = (category: string) => {
  const colors: Record<string, string> = {
    market_history: "bg-red-100 text-red-700",
    strategy: "bg-purple-100 text-purple-700",
    macro: "bg-blue-100 text-blue-700",
    sector: "bg-green-100 text-green-700",
    custom: "bg-gray-100 text-gray-700",
  };
  return colors[category] || "bg-gray-100 text-gray-700";
};

const getCategoryLabel = (category: string) => {
  const labels: Record<string, string> = {
    market_history: "Market History",
    strategy: "Investment Strategy",
    macro: "Macroeconomics",
    sector: "Sector Research",
    custom: "Custom",
  };
  return labels[category] || category;
};

export function AgentKnowledgeSelector({
  agentName,
  crewName,
  selectedSourceIds = [],
  selectedUserSourceIds = [],
  includeTradingLessons = true,
  onSelectionChange,
}: AgentKnowledgeSelectorProps) {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(
    new Set(selectedSourceIds)
  );
  const [selectedUserIds, setSelectedUserIds] = useState<Set<number>>(
    new Set(selectedUserSourceIds)
  );
  const [includeLessons, setIncludeLessons] = useState(includeTradingLessons);
  const [expanded, setExpanded] = useState(false);

  // Use SWR to cache knowledge source data, avoiding refetching on every expansion
  const { data, isLoading: loading } = useSWR<{
    subscribed_sources: KnowledgeSource[];
    custom_sources: KnowledgeSource[];
  }>(
    getToken() ? buildApiUrl("/api/v1/knowledge/my-sources") : null,
    fetcher,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      dedupingInterval: 60000, // No duplicate requests within 60 seconds
    }
  );

  const mySources: KnowledgeSource[] = [
    ...(data?.subscribed_sources || []),
    ...(data?.custom_sources || []),
  ];

  const toggleSource = (id: number, isUserSource: boolean = false) => {
    if (isUserSource) {
      const newIds = new Set(selectedUserIds);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      setSelectedUserIds(newIds);
      emitChange(selectedIds, newIds, includeLessons);
    } else {
      const newIds = new Set(selectedIds);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      setSelectedIds(newIds);
      emitChange(newIds, selectedUserIds, includeLessons);
    }
  };

  const handleLessonsToggle = (value: boolean) => {
    setIncludeLessons(value);
    emitChange(selectedIds, selectedUserIds, value);
  };

  const emitChange = (
    sysIds: Set<number>,
    userIds: Set<number>,
    lessons: boolean
  ) => {
    if (onSelectionChange) {
      onSelectionChange({
        agent_name: agentName,
        source_ids: Array.from(sysIds),
        user_source_ids: Array.from(userIds),
        include_trading_lessons: lessons,
        max_lessons: 5,
      });
    }
  };

  // Show only agent-level or both-level knowledge sources
  const agentScopeSources = mySources.filter(
    (s) => !s.knowledge_scope || s.knowledge_scope === "agent" || s.knowledge_scope === "both"
  );
  const systemSources = agentScopeSources.filter((s) => !s.source_type || s.source_type !== "custom");
  const customSources = agentScopeSources.filter((s) => s.source_type === "custom");

  const totalSelected = selectedIds.size + selectedUserIds.size + (includeLessons ? 1 : 0);

  return (
    <Card className="border-purple-200">
      <Collapsible open={expanded} onOpenChange={setExpanded}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-purple-500" />
              Knowledge sources for {agentName}
              {totalSelected > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {totalSelected}
                </Badge>
              )}
            </CardTitle>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm">
                <ChevronDown
                  className={`h-4 w-4 transition-transform ${
                    expanded ? "rotate-180" : ""
                  }`}
                />
              </Button>
            </CollapsibleTrigger>
          </div>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="space-y-4">
            {loading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                <span className="text-sm text-muted-foreground">Loading...</span>
              </div>
            ) : mySources.length === 0 ? (
              <div className="text-center py-6 text-sm text-muted-foreground border rounded-lg border-dashed">
                <p className="mb-2">No knowledge sources yet</p>
                <Link href="/tools?category=knowledge">
                  <Button variant="outline" size="sm" className="h-7 text-xs">
                    Get Knowledge Packs
                  </Button>
                </Link>
              </div>
            ) : (
              <>
                {/* Historical Trading Lessons */}
                <div className="p-3 border rounded-lg bg-amber-50 dark:bg-amber-900/20">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Checkbox
                        id={`lessons-${agentName}`}
                        checked={includeLessons}
                        onCheckedChange={handleLessonsToggle}
                      />
                      <Label
                        htmlFor={`lessons-${agentName}`}
                        className="text-sm font-medium cursor-pointer flex items-center gap-2">
                        <History className="h-4 w-4 text-amber-600" />
                        Historical Trading Lessons
                      </Label>
                    </div>
                    {includeLessons && (
                      <Check className="h-4 w-4 text-green-600" />
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 ml-6">
                    Automatically load relevant historical experience from the database
                    <span className="text-green-600 ml-1">(Enabled by default)</span>
                  </p>
                </div>

                {/* System Knowledge Sources */}
                {systemSources.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground mb-2">
                      System Knowledge Sources
                    </h4>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {systemSources.map((source) => (
                        <div
                          key={source.id}
                          className="flex items-start gap-2 p-2 border rounded hover:bg-muted transition-colors">
                          <Checkbox
                            id={`source-${source.id}`}
                            checked={selectedIds.has(source.id)}
                            onCheckedChange={() => toggleSource(source.id, false)}
                            className="mt-1"
                          />
                          <div className="flex-1 min-w-0">
                            <Label
                              htmlFor={`source-${source.id}`}
                              className="text-sm font-medium cursor-pointer block">
                              {source.display_name}
                            </Label>
                            <Badge
                              variant="outline"
                              className={`text-xs mt-1 ${getCategoryColor(source.category)}`}>
                              {getCategoryLabel(source.category)}
                            </Badge>
                            {source.description && (
                              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                {source.description}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Custom Knowledge Sources */}
                {customSources.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground mb-2">
                      Custom Knowledge Sources
                    </h4>
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {customSources.map((source) => (
                        <div
                          key={source.id}
                          className="flex items-start gap-2 p-2 border rounded hover:bg-muted transition-colors">
                          <Checkbox
                            id={`user-source-${source.id}`}
                            checked={selectedUserIds.has(source.id)}
                            onCheckedChange={() => toggleSource(source.id, true)}
                            className="mt-1"
                          />
                          <div className="flex-1 min-w-0">
                            <Label
                              htmlFor={`user-source-${source.id}`}
                              className="text-sm font-medium cursor-pointer block">
                              {source.display_name}
                            </Label>
                            <p className="text-xs text-muted-foreground">
                              {source.source_type}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}

export default AgentKnowledgeSelector;
