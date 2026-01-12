"use client";

import { useState, useEffect, useCallback } from "react";
import { Link } from "@/i18n/routing";
import {
  Brain,
  BookOpen,
  Plus,
  Check,
  ChevronDown,
  History,
  Settings2,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { getToken } from "@/lib/auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

interface KnowledgeSource {
  id: number;
  source_key: string;
  display_name: string;
  description?: string;
  category: string;
  knowledge_scope: string;  // crew, agent, both
  source_type: string;
  is_system: boolean;
}

interface KnowledgeConfig {
  enabled: boolean;
  source_ids: number[];
  user_source_ids: number[];
  include_trading_lessons: boolean;
  max_lessons: number;
}

interface CrewKnowledgePanelProps {
  crewName: string;
  onConfigChange?: (config: KnowledgeConfig) => void;
}

export function CrewKnowledgePanel({
  crewName,
  onConfigChange,
}: CrewKnowledgePanelProps) {
  const [enabled, setEnabled] = useState(true);
  const [mySources, setMySources] = useState<KnowledgeSource[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [includeLessons, setIncludeLessons] = useState(true);
  const [maxLessons, setMaxLessons] = useState(5);
  const [lessonsCount, setLessonsCount] = useState(0);
  const [expanded, setExpanded] = useState(true);
  const [loading, setLoading] = useState(true);

  const loadMySources = useCallback(async () => {
    try {
      const token = getToken();
      if (!token) return;

      const res = await fetch(`${API_BASE_URL}/api/v1/knowledge/my-sources`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;

      const data = await res.json();
      const allSources: KnowledgeSource[] = [
        ...(data.subscribed_sources || []).map((s: KnowledgeSource) => ({
          ...s,
          is_system: true,
        })),
        ...(data.custom_sources || []).map((s: KnowledgeSource) => ({
          ...s,
          is_system: false,
        })),
      ];
      // Show only crew-level or both-level knowledge sources
      const crewScopeSources = allSources.filter(
        (s) => !s.knowledge_scope || s.knowledge_scope === "crew" || s.knowledge_scope === "both"
      );
      setMySources(crewScopeSources);
      setLessonsCount(data.legacy_lessons?.count || 0);
    } catch (err) {
      console.error("Failed to load knowledge sources:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadBinding = useCallback(async () => {
    if (!crewName) return;

    try {
      const token = getToken();
      if (!token) return;

      const res = await fetch(
        `${API_BASE_URL}/api/v1/knowledge/bindings/${encodeURIComponent(crewName)}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!res.ok) return;

      const data = await res.json();
      if (!data.is_default) {
        setSelectedIds([...(data.source_ids || []), ...(data.user_source_ids || [])]);
        setIncludeLessons(data.include_trading_lessons ?? true);
        setMaxLessons(data.max_lessons || 5);
      }
    } catch (err) {
      console.error("Failed to load knowledge binding:", err);
    }
  }, [crewName]);

  useEffect(() => {
    loadMySources();
  }, [loadMySources]);

  useEffect(() => {
    if (crewName) {
      loadBinding();
    }
  }, [crewName, loadBinding]);

  const toggleSource = (id: number) => {
    const newIds = selectedIds.includes(id)
      ? selectedIds.filter((i) => i !== id)
      : [...selectedIds, id];
    setSelectedIds(newIds);
    emitChange(newIds, includeLessons, maxLessons);
  };

  const handleLessonsToggle = (value: boolean) => {
    setIncludeLessons(value);
    emitChange(selectedIds, value, maxLessons);
  };

  const handleMaxLessonsChange = (value: number[]) => {
    const newMax = value[0];
    setMaxLessons(newMax);
    emitChange(selectedIds, includeLessons, newMax);
  };

  const emitChange = (ids: number[], lessons: boolean, max: number) => {
    if (onConfigChange) {
      onConfigChange({
        enabled,
        source_ids: ids.filter((id) =>
          mySources.find((s) => s.id === id && s.is_system)
        ),
        user_source_ids: ids.filter((id) =>
          mySources.find((s) => s.id === id && !s.is_system)
        ),
        include_trading_lessons: lessons,
        max_lessons: max,
      });
    }
  };

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

  return (
    <Card>
      <Collapsible open={expanded} onOpenChange={setExpanded}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Brain className="h-4 w-4 text-purple-500" />
              Knowledge Configuration
            </CardTitle>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Enable Knowledge</span>
                <Switch
                  checked={enabled}
                  onCheckedChange={(v) => {
                    setEnabled(v);
                    if (onConfigChange) {
                      onConfigChange({
                        enabled: v,
                        source_ids: selectedIds.filter((id) =>
                          mySources.find((s) => s.id === id && s.is_system)
                        ),
                        user_source_ids: selectedIds.filter((id) =>
                          mySources.find((s) => s.id === id && !s.is_system)
                        ),
                        include_trading_lessons: includeLessons,
                        max_lessons: maxLessons,
                      });
                    }
                  }}
                />
              </div>
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
          </div>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="space-y-4">
            {/* Legacy Trading Lessons */}
            <div className="p-3 border rounded-lg bg-amber-50 dark:bg-amber-900/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <History className="h-4 w-4 text-amber-600" />
                  <span className="font-medium">Historical Trading Lessons</span>
                  <Badge variant="secondary">{lessonsCount} items</Badge>
                </div>
                <Switch
                  checked={includeLessons}
                  onCheckedChange={handleLessonsToggle}
                />
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Automatically load historical lessons learned from the database
              </p>

              {includeLessons && (
                <div className="mt-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <Label className="text-xs">Max Lessons</Label>
                    <span className="text-xs text-muted-foreground">
                      {maxLessons}
                    </span>
                  </div>
                  <Slider
                    value={[maxLessons]}
                    onValueChange={handleMaxLessonsChange}
                    min={1}
                    max={10}
                    step={1}
                    className="w-full"
                  />
                </div>
              )}
            </div>

            {/* Knowledge Sources */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Subscribed Knowledge Cartridges</span>
                <Link href="/tools?category=knowledge">
                  <Button variant="outline" size="sm">
                    <Plus className="h-3 w-3 mr-1" />
                    Add More
                    <ExternalLink className="h-3 w-3 ml-1" />
                  </Button>
                </Link>
              </div>

              {loading ? (
                <div className="text-sm text-muted-foreground text-center py-4">
                  Loading...
                </div>
              ) : mySources.length === 0 ? (
                <div className="text-center py-6 border rounded-lg border-dashed">
                  <BookOpen className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                  <p className="text-sm text-muted-foreground mb-3">
                    No knowledge sources yet
                  </p>
                  <Link href="/tools?category=knowledge">
                    <Button variant="outline" size="sm">
                      Browse Marketplace
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {mySources.map((source) => (
                    <div
                      key={source.id}
                      className={`p-2 border rounded cursor-pointer transition-colors ${
                        selectedIds.includes(source.id)
                          ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20"
                          : "hover:bg-muted"
                      }`}
                      onClick={() => toggleSource(source.id)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <BookOpen className="h-4 w-4 text-purple-500" />
                          <span className="text-sm font-medium">
                            {source.display_name}
                          </span>
                          <Badge
                            variant="outline"
                            className={`text-xs ${getCategoryColor(source.category)}`}
                          >
                            {source.category}
                          </Badge>
                        </div>
                        {selectedIds.includes(source.id) && (
                          <Check className="h-4 w-4 text-purple-500" />
                        )}
                      </div>
                      {source.description && (
                        <p className="text-xs text-muted-foreground mt-1 ml-6 line-clamp-1">
                          {source.description}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Memory Settings */}
            <div className="pt-2 border-t">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Settings2 className="h-4 w-4" />
                <span>CrewAI native memory is enabled by default</span>
              </div>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}

export default CrewKnowledgePanel;
