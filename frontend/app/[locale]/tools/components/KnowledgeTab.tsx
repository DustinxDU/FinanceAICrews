"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import {
  ShoppingCart,
  Library,
  Info,
  Search,
  Filter,
  Plus,
  Check,
  Lock,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetcher, buildApiUrl } from "@/lib/api";

interface KnowledgeSource {
  id: number;
  source_key: string;
  display_name: string;
  description?: string;
  category?: string;
  tags?: string[];
  knowledge_scope?: "crew" | "agent" | "both";
  tier?: "free" | "premium";
  price?: number;
  is_subscribed?: boolean;
  subscriber_count?: number;
  usage_count?: number;
}

interface MarketplaceResponse {
  sources: KnowledgeSource[];
}

interface MySourcesResponse {
  subscribed_sources: KnowledgeSource[];
  custom_sources: KnowledgeSource[];
  legacy_lessons?: {
    count: number;
    description: string;
  };
}

type KnowledgeView = "marketplace" | "owned" | "detail";

export function KnowledgeTab() {
  const t = useTranslations("tools");
  const searchParams = useSearchParams();
  const sourceKeyParam = searchParams.get("source_key");

  const [activeView, setActiveView] = useState<KnowledgeView>(
    sourceKeyParam ? "detail" : "marketplace"
  );
  const [selectedSource, setSelectedSource] = useState<KnowledgeSource | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [scopeFilter, setScopeFilter] = useState<string>("all");

  // Fetch marketplace data
  const { data: marketplaceData, mutate: mutateMarketplace } = useSWR<MarketplaceResponse>(
    buildApiUrl("/api/v1/knowledge/marketplace"),
    fetcher
  );

  // Fetch owned sources
  const { data: mySourcesData, mutate: mutateMySources } = useSWR<MySourcesResponse>(
    buildApiUrl("/api/v1/knowledge/my-sources"),
    fetcher
  );

  // Handle source_key param for deep linking
  useEffect(() => {
    if (sourceKeyParam && marketplaceData) {
      const source = marketplaceData.sources.find((s) => s.source_key === sourceKeyParam);
      if (source) {
        setSelectedSource(source);
        setActiveView("detail");
      }
    }
  }, [sourceKeyParam, marketplaceData]);

  const subViews = [
    { key: "marketplace" as KnowledgeView, label: "Marketplace", icon: ShoppingCart },
    { key: "owned" as KnowledgeView, label: "My Knowledge", icon: Library },
  ];

  const filteredMarketplaceSources = marketplaceData?.sources.filter((source) => {
    const matchesSearch =
      !searchQuery ||
      source.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      source.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === "all" || source.category === categoryFilter;
    const matchesScope =
      scopeFilter === "all" ||
      source.knowledge_scope === scopeFilter ||
      source.knowledge_scope === "both";
    return matchesSearch && matchesCategory && matchesScope;
  });

  const ownedSources = [
    ...(mySourcesData?.subscribed_sources || []),
    ...(mySourcesData?.custom_sources || []),
  ];

  const handleAddSource = async (sourceKey: string) => {
    try {
      const response = await fetch(
        buildApiUrl(`/api/v1/knowledge/marketplace/${sourceKey}/subscribe`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        }
      );

      if (!response.ok) throw new Error("Failed to add knowledge pack");

      // Refresh both marketplace and owned sources
      mutateMarketplace();
      mutateMySources();
    } catch (error) {
      console.error("Error adding knowledge pack:", error);
    }
  };

  const renderKnowledgeCard = (source: KnowledgeSource) => {
    const isOwned = source.is_subscribed;
    const isPremium = source.tier === "premium";

    return (
      <Card
        key={source.id}
        className="hover:shadow-md transition-shadow cursor-pointer"
        onClick={() => {
          setSelectedSource(source);
          setActiveView("detail");
        }}
      >
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CardTitle className="text-lg flex items-center gap-2">
                {source.display_name}
                {isPremium && <Lock className="w-4 h-4 text-amber-600" />}
              </CardTitle>
              <div className="flex gap-2 mt-2">
                {source.category && (
                  <Badge variant="outline" className="text-xs">
                    {source.category}
                  </Badge>
                )}
                {source.knowledge_scope && (
                  <Badge variant="secondary" className="text-xs">
                    {source.knowledge_scope}
                  </Badge>
                )}
              </div>
            </div>
            <div className="ml-4">
              {isOwned ? (
                <Badge className="bg-green-100 text-green-700 border-green-200">
                  <Check className="w-3 h-3 mr-1" />
                  Owned
                </Badge>
              ) : (
                <Button
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAddSource(source.source_key);
                  }}
                >
                  <Plus className="w-4 h-4 mr-1" />
                  {isPremium ? `Buy $${source.price}` : "Add"}
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground line-clamp-2">{source.description}</p>
          <div className="flex gap-4 mt-4 text-xs text-muted-foreground">
            {source.subscriber_count !== undefined && (
              <span>{source.subscriber_count} users</span>
            )}
            {source.usage_count !== undefined && <span>{source.usage_count} uses</span>}
          </div>
        </CardContent>
      </Card>
    );
  };

  const renderMarketplace = () => (
    <div>
      {/* Filters */}
      <div className="mb-6 flex gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <Input
              placeholder="Search knowledge packs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-4 py-2 border rounded-md"
        >
          <option value="all">{t('allCategories')}</option>
          <option value="market_history">{t('marketHistory')}</option>
          <option value="strategy">Strategy</option>
          <option value="macro">Macro</option>
          <option value="sector">Sector</option>
        </select>
        <select
          value={scopeFilter}
          onChange={(e) => setScopeFilter(e.target.value)}
          className="px-4 py-2 border rounded-md"
        >
          <option value="all">{t('allScopes')}</option>
          <option value="crew">{t('crew')}</option>
          <option value="agent">{t('agent')}</option>
          <option value="both">Both</option>
        </select>
      </div>

      {/* Knowledge Cards Grid */}
      {!filteredMarketplaceSources ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : filteredMarketplaceSources.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <p>{t('noKnowledgePacksFound')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredMarketplaceSources.map(renderKnowledgeCard)}
        </div>
      )}
    </div>
  );

  const renderOwned = () => (
    <div>
      {!mySourcesData ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : ownedSources.length === 0 ? (
        <div className="text-center py-20">
          <Library className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">{t('noKnowledgePacksYet')}</h3>
          <p className="text-muted-foreground mb-4">
            Add knowledge packs from the marketplace to enhance your AI agents
          </p>
          <Button onClick={() => setActiveView("marketplace")}>
            Browse Marketplace
          </Button>
        </div>
      ) : (
        <div>
          {mySourcesData.legacy_lessons && mySourcesData.legacy_lessons.count > 0 && (
            <Card className="mb-6 border-blue-200 bg-blue-50">
              <CardHeader>
                <CardTitle className="text-lg">Historical Trading Lessons</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-2">
                  {mySourcesData.legacy_lessons.description}
                </p>
                <p className="text-sm font-medium">
                  {mySourcesData.legacy_lessons.count} lessons available
                </p>
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {ownedSources.map(renderKnowledgeCard)}
          </div>
        </div>
      )}
    </div>
  );

  const renderDetail = () => {
    if (!selectedSource) return null;

    const isOwned = selectedSource.is_subscribed;
    const isPremium = selectedSource.tier === "premium";

    return (
      <div>
        <Button
          variant="ghost"
          onClick={() => setActiveView("marketplace")}
          className="mb-6"
        >
          ← Back to Marketplace
        </Button>

        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <CardTitle className="text-2xl flex items-center gap-3">
                  {selectedSource.display_name}
                  {isPremium && <Lock className="w-5 h-5 text-amber-600" />}
                </CardTitle>
                <div className="flex gap-2 mt-3">
                  {selectedSource.category && (
                    <Badge variant="outline">{selectedSource.category}</Badge>
                  )}
                  {selectedSource.knowledge_scope && (
                    <Badge variant="secondary">{selectedSource.knowledge_scope}</Badge>
                  )}
                  {selectedSource.tags?.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                {isOwned ? (
                  <Badge className="bg-green-100 text-green-700 border-green-200 text-base px-4 py-2">
                    <Check className="w-4 h-4 mr-2" />
                    Owned
                  </Badge>
                ) : (
                  <Button
                    size="lg"
                    onClick={() => handleAddSource(selectedSource.source_key)}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    {isPremium ? `Buy for $${selectedSource.price}` : "Add to My Knowledge"}
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <h3 className="font-semibold mb-2">Description</h3>
              <p className="text-muted-foreground">{selectedSource.description}</p>
            </div>

            <div className="grid grid-cols-3 gap-4 pt-4 border-t">
              <div>
                <p className="text-sm text-muted-foreground">{t('users')}</p>
                <p className="text-2xl font-bold">
                  {selectedSource.subscriber_count || 0}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('totalUses')}</p>
                <p className="text-2xl font-bold">{selectedSource.usage_count || 0}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('type')}</p>
                <p className="text-2xl font-bold capitalize">
                  {selectedSource.tier || "free"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <div>
      {/* Sub-view Navigation (only show when not in detail view) */}
      {activeView !== "detail" && (
        <div className="mb-6 flex gap-2">
          {subViews.map((view) => {
            const Icon = view.icon;
            return (
              <button
                key={view.key}
                onClick={() => setActiveView(view.key)}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-all flex items-center gap-2 ${
                  activeView === view.key
                    ? "bg-blue-100 text-blue-700"
                    : "text-muted-foreground hover:bg-muted"
                }`}
              >
                <Icon className="w-4 h-4" />
                {view.label}
              </button>
            );
          })}
        </div>
      )}

      {/* View Content */}
      {activeView === "marketplace" && renderMarketplace()}
      {activeView === "owned" && renderOwned()}
      {activeView === "detail" && renderDetail()}
    </div>
  );
}
