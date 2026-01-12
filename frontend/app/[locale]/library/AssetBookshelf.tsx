"use client";

import React, { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useRouter } from "@/i18n/routing";
import { useTranslations } from 'next-intl';
import apiClient, { LibraryAssetGroup } from "@/lib/api";

// 筛选类型
type FilterType = "all" | "favorites" | "recent";

// 情绪配置
interface SentimentConfig {
  icon: string;
  color: string;
  bg: string;
  bgSelected: string;
  bgHover: string;
  border: string;
  borderSelected: string;
  label: string;
  variant: "success" | "destructive" | "secondary" | "default";
}

// 信号配置
interface SignalConfig {
  icon: string;
  color: string;
  bg: string;
  variant: "success" | "destructive" | "warning" | "secondary";
}

// 情绪配置工厂
const getSentimentConfig = (sentiment?: string): SentimentConfig => {
  switch (sentiment) {
    case "bullish":
      return {
        icon: "📈",
        color: "text-[var(--accent-green)]",
        bg: "bg-[var(--accent-green)]/10",
        bgSelected: "bg-[var(--accent-green)]/15",
        bgHover: "bg-[var(--accent-green)]/15",
        border: "border-[var(--accent-green)]/20",
        borderSelected: "border-[var(--accent-green)]",
        label: "Bullish",
        variant: "success",
      };
    case "bearish":
      return {
        icon: "📉",
        color: "text-red-400",
        bg: "bg-red-400/10",
        bgSelected: "bg-red-400/15",
        bgHover: "bg-red-400/15",
        border: "border-red-400/20",
        borderSelected: "border-red-400",
        label: "Bearish",
        variant: "destructive",
      };
    default:
      return {
        icon: "📊",
        color: "text-[var(--text-secondary)]",
        bg: "bg-[var(--bg-card)]",
        bgSelected: "bg-[var(--bg-card)]",
        bgHover: "bg-[var(--bg-card)]/80",
        border: "border-[var(--border-color)]",
        borderSelected: "border-[var(--border-color)]",
        label: "Neutral",
        variant: "secondary",
      };
  }
};

// 信号配置工厂
const getSignalConfig = (signal?: string): SignalConfig => {
  switch (signal) {
    case "buy":
      return {
        icon: "🟢",
        color: "text-[var(--accent-green)]",
        bg: "bg-[var(--accent-green)]/20",
        variant: "success",
      };
    case "sell":
      return {
        icon: "🔴",
        color: "text-red-400",
        bg: "bg-red-400/20",
        variant: "destructive",
      };
    case "hold":
      return {
        icon: "🟡",
        color: "text-[var(--accent-yellow)]",
        bg: "bg-[var(--accent-yellow)]/20",
        variant: "warning",
      };
    default:
      return {
        icon: "⚪",
        color: "text-[var(--text-secondary)]",
        bg: "bg-[var(--bg-card)]",
        variant: "secondary",
      };
  }
};

// 格式化相对时间
const formatRelativeTime = (dateStr?: string): string => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return `${Math.floor(diffDays / 30)} months ago`;
};

// 判断是否为最近（7天内）
const isRecent = (dateStr?: string): boolean => {
  if (!dateStr) return false;
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  return diffDays < 7;
};

interface AssetBookshelfProps {
  onAssetSelect?: (ticker: string) => void;
  selectedTicker?: string | null;
}

export default function AssetBookshelf({ onAssetSelect, selectedTicker }: AssetBookshelfProps) {
  const t = useTranslations('library');
  const router = useRouter();
  const [assets, setAssets] = useState<LibraryAssetGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filter, setFilter] = useState<FilterType>("all");
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const searchInputRef = useRef<HTMLInputElement>(null);

  const loadAssets = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.getLibraryAssets();
      setAssets(data);
      setError(null);
    } catch (err) {
      console.error("Failed to load assets:", err);
      setError(t('loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  // 根据筛选条件过滤资产
  const filteredAssets = useMemo(() => {
    return assets.filter((asset) => {
      const matchesSearch =
        asset.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
        asset.asset_name?.toLowerCase().includes(searchQuery.toLowerCase());

      if (filter === "favorites" && !favorites.has(asset.ticker)) return false;
      if (filter === "recent" && !isRecent(asset.last_analysis_at)) return false;

      return matchesSearch;
    });
  }, [assets, searchQuery, filter, favorites]);

  // 按资产类型分组
  const groupedAssets = useMemo(() => {
    const groups: Record<string, LibraryAssetGroup[]> = {};
    filteredAssets.forEach((asset) => {
      const type = asset.asset_type || "Other";
      if (!groups[type]) groups[type] = [];
      groups[type].push(asset);
    });
    return groups;
  }, [filteredAssets]);

  // 统计信息
  const stats = useMemo(() => {
    const totalInsights = assets.reduce((sum, a) => sum + a.insights_count, 0);
    const bullishCount = assets.filter((a) => a.latest_sentiment === "bullish").length;
    const bearishCount = assets.filter((a) => a.latest_sentiment === "bearish").length;
    const neutralCount = assets.filter((a) => !a.latest_sentiment || a.latest_sentiment === "neutral").length;
    const favoritesCount = assets.filter((a) => favorites.has(a.ticker)).length;
    const recentCount = assets.filter((a) => isRecent(a.last_analysis_at)).length;

    return {
      totalAssets: assets.length,
      totalInsights,
      bullishCount,
      bearishCount,
      neutralCount,
      favoritesCount,
      recentCount,
    };
  }, [assets, favorites]);

  // 处理收藏切换（本地状态，用于过滤）
  const handleToggleFavorite = (e: React.MouseEvent, ticker: string) => {
    e.stopPropagation();
    const newFavorites = new Set(favorites);
    if (favorites.has(ticker)) {
      newFavorites.delete(ticker);
    } else {
      newFavorites.add(ticker);
    }
    setFavorites(newFavorites);
  };

  const handleAssetClick = (asset: LibraryAssetGroup) => {
    if (onAssetSelect) {
      onAssetSelect(asset.ticker);
    } else {
      router.push(`/library?asset=${asset.ticker}`);
    }
  };

  // 加载骨架屏
  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b border-[var(--border-color)]">
          <div className="h-7 w-32 bg-[var(--bg-card)] rounded animate-pulse"></div>
        </div>
        <div className="p-3 border-b border-[var(--border-color)] flex gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 flex-1 bg-[var(--bg-card)] rounded animate-pulse"></div>
          ))}
        </div>
        <div className="p-3 border-b border-[var(--border-color)]">
          <div className="h-10 bg-[var(--bg-card)] rounded animate-pulse"></div>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-[var(--bg-card)] rounded-lg animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div className="flex flex-col h-full items-center justify-center p-8">
        <div className="text-red-400 mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" x2="12" y1="8" y2="12"></line>
            <line x1="12" x2="12.01" y1="16" y2="16"></line>
          </svg>
        </div>
        <p className="text-[var(--text-secondary)] mb-4">{error}</p>
        <button
          onClick={loadAssets}
          className="px-4 py-2 bg-[var(--accent-blue)] text-white rounded-lg hover:bg-[var(--accent-blue)]/80 transition-colors"
        >
          {t('retry')}
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[var(--bg-panel)]">
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-color)]">
        <h2 className="text-lg font-bold flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--accent-blue)]">
            <path d="m16 6 4 14"></path>
            <path d="M12 6v14"></path>
            <path d="M8 8v12"></path>
            <path d="M4 4v16"></path>
          </svg>
          {t('assetBookshelf')}
        </h2>
        <p className="text-sm text-[var(--text-secondary)] mt-1">
          {stats.totalAssets} {t('assets')} · {stats.totalInsights} {t('analyses')}
        </p>
      </div>

      {/* Quick Filters */}
      <div className="flex gap-1 p-3 border-b border-[var(--border-color)]">
        {[
          { key: "all" as FilterType, label: t('filterAll'), count: stats.totalAssets },
          { key: "favorites" as FilterType, label: t('filterFavorites'), count: stats.favoritesCount },
          { key: "recent" as FilterType, label: t('filterRecent'), count: stats.recentCount },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              filter === tab.key
                ? "bg-[var(--accent-blue)]/20 text-[var(--accent-blue)] border border-[var(--accent-blue)]/30"
                : "bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-card)]/80 border border-transparent"
            }`}
          >
            {tab.label}
            <span className="ml-1.5 opacity-60">({tab.count})</span>
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="p-3 border-b border-[var(--border-color)]">
        <div className="relative">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.3-4.3"></path>
          </svg>
          <input
            ref={searchInputRef}
            type="text"
            placeholder={t('searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg
              focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)]/50 focus:border-[var(--accent-blue)]
              text-sm placeholder:text-[var(--text-secondary)]/50 transition-all"
          />
        </div>
      </div>

      {/* Asset List - 分组展示 */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {Object.keys(groupedAssets).length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center px-4">
            <div className="w-16 h-16 rounded-full bg-[var(--bg-card)] flex items-center justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--text-secondary)]">
                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                <polyline points="13 2 13 9 20 9"></polyline>
              </svg>
            </div>
            <p className="text-[var(--text-secondary)]">
              {searchQuery ? t('noMatchingAssets') : t('noAnalysisRecords')}
            </p>
            <p className="text-xs text-[var(--text-secondary)]/60 mt-1">
              {t('createAnalysisHint')}
            </p>
          </div>
        ) : (
          Object.entries(groupedAssets).map(([category, categoryAssets]) => (
            <div key={category} className="mb-2">
              <div className="sticky top-0 z-10 bg-[var(--bg-panel)]/95 backdrop-blur-sm px-4 py-2 border-b border-[var(--border-color)]/50">
                <div className="flex items-center gap-2 text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                  <span className="w-2 h-2 rounded-full bg-[var(--accent-blue)]" />
                  {category}
                  <span className="ml-1 opacity-60">({categoryAssets.length})</span>
                </div>
              </div>

              {categoryAssets.map((asset) => (
                <AssetCard
                  key={asset.ticker}
                  asset={asset}
                  isFavorite={favorites.has(asset.ticker)}
                  isSelected={selectedTicker === asset.ticker}
                  onFavoriteToggle={(e) => handleToggleFavorite(e, asset.ticker)}
                  onClick={() => handleAssetClick(asset)}
                />
              ))}
            </div>
          ))
        )}
      </div>

      {/* Stats Footer */}
      <div className="p-4 border-t border-[var(--border-color)] bg-[var(--bg-panel)]">
        <div className="grid grid-cols-5 gap-2">
          <StatItem label={t('statAssets')} value={stats.totalAssets} />
          <StatItem label={t('statAnalyses')} value={stats.totalInsights} />
          <StatItem label="Bullish" value={stats.bullishCount} color="text-[var(--accent-green)]" />
          <StatItem label="Neutral" value={stats.neutralCount} color="text-[var(--text-secondary)]" />
          <StatItem label="Bearish" value={stats.bearishCount} color="text-red-400" />
        </div>
      </div>
    </div>
  );
}

// 资产卡片组件
interface AssetCardProps {
  asset: LibraryAssetGroup;
  isFavorite: boolean;
  isSelected: boolean;
  onFavoriteToggle: (e: React.MouseEvent) => void;
  onClick: () => void;
}

function AssetCard({ asset, isFavorite, isSelected, onFavoriteToggle, onClick }: AssetCardProps) {
  const t = useTranslations('library');
  const sentimentConfig = getSentimentConfig(asset.latest_sentiment);
  const signalConfig = getSignalConfig(asset.latest_signal);

  return (
    <div
      onClick={onClick}
      className={`mx-3 my-2 p-4 rounded-xl border cursor-pointer transition-all duration-200 ${
        isSelected
          ? "bg-[var(--bg-card)] border-[var(--border-color)] shadow-lg"
          : `${sentimentConfig.bg} ${sentimentConfig.border} hover:${sentimentConfig.bgHover}`
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-lg font-bold ${isSelected ? 'text-white' : 'text-[var(--text-primary)]'}`}>{asset.ticker}</span>
            <button
              onClick={onFavoriteToggle}
              className={`p-1 rounded transition-colors ${
                isFavorite
                  ? "text-yellow-400"
                  : "text-[var(--text-secondary)] hover:text-yellow-400 opacity-0 group-hover:opacity-100"
              }`}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill={isFavorite ? "currentColor" : "none"}
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
              </svg>
            </button>
          </div>

          {asset.asset_name && (
            <p className="text-sm text-[var(--text-secondary)] truncate mt-0.5">
              {asset.asset_name}
            </p>
          )}
        </div>

        {asset.latest_signal && (
          <span
            className={`px-2 py-0.5 text-xs font-medium rounded border ${
              asset.latest_signal === "buy"
                ? "bg-[var(--accent-green)]/20 border-[var(--accent-green)]/30 text-[var(--accent-green)]"
                : asset.latest_signal === "sell"
                ? "bg-red-400/20 border-red-400/30 text-red-400"
                : "bg-[var(--bg-card)] border-[var(--border-color)] text-[var(--text-secondary)]"
            }`}
          >
            {signalConfig.icon} {asset.latest_signal.toUpperCase()}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-2">
          <div
            className={`w-8 h-8 rounded-full ${sentimentConfig.bg} flex items-center justify-center`}
          >
            <span className="text-lg">{sentimentConfig.icon}</span>
          </div>
          <div>
            <div className={`text-sm font-medium ${sentimentConfig.color}`}>
              {sentimentConfig.label}
            </div>
            {asset.latest_sentiment && (
              <div className="text-xs text-[var(--text-secondary)]">
                {asset.latest_sentiment === "bullish" ? t('sentimentBullish') : asset.latest_sentiment === "bearish" ? t('sentimentBearish') : t('sentimentNeutral')}
              </div>
            )}
          </div>
        </div>

        <div className="text-right">
          <div className="flex items-center gap-1 text-sm text-[var(--text-secondary)] justify-end">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 9 20 9"></polyline>
            </svg>
            <span>{asset.insights_count}</span>
          </div>
          {asset.last_analysis_at && (
            <div className="text-xs text-[var(--text-secondary)]/60 mt-0.5">
              {formatRelativeTime(asset.last_analysis_at)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// 统计项组件
interface StatItemProps {
  label: string;
  value: number;
  color?: string;
}

function StatItem({ label, value, color = "text-[var(--text-primary)]" }: StatItemProps) {
  return (
    <div className="text-center">
      <div className={`font-bold text-lg ${color}`}>{value}</div>
      <div className="text-xs text-[var(--text-secondary)]">{label}</div>
    </div>
  );
}
