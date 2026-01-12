"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import apiClient, { LibraryInsight } from "@/lib/api";
import { useTranslations } from "next-intl";

// 筛选类型
type SourceFilter = "all" | "quick_scan" | "technical_diagnostic" | "crew_analysis";
type SentimentFilter = "all" | "bullish" | "bearish" | "neutral";
type SignalFilter = "all" | "buy" | "sell" | "hold";

// 来源配置
interface SourceConfig {
  label: string;
  color: string;
  bg: string;
  border: string;
  icon: string;
}

// 情绪配置
interface SentimentConfig {
  color: string;
  bg: string;
  bgHover: string;
  border: string;
  borderSelected: string;
  icon: string;
  textColor: string;
  dotColor: string;
  label: string;
}

// 信号配置
interface SignalConfig {
  icon: string;
  color: string;
  bg: string;
  variant: "success" | "destructive" | "warning" | "secondary";
}

// 来源配置工厂
const getSourceConfig = (sourceType: string): SourceConfig => {
  const config: Record<string, SourceConfig> = {
    quick_scan: {
      label: "Quick Scan",
      color: "text-blue-400",
      bg: "bg-blue-400/10",
      border: "border-blue-400/30",
      icon: "",
    },
    technical_diagnostic: {
      label: "Technical Diagnostic",
      color: "text-purple-400",
      bg: "bg-purple-400/10",
      border: "border-purple-400/30",
      icon: "",
    },
    crew_analysis: {
      label: "Crew Analysis",
      color: "text-[var(--accent-green)]",
      bg: "bg-[var(--accent-green)]/10",
      border: "border-[var(--accent-green)]/30",
      icon: "",
    },
  };
  const item =
    config[sourceType] || {
      label: sourceType,
      color: "text-[var(--text-secondary)]",
      bg: "bg-[var(--bg-card)]",
      border: "border-[var(--border-color)]",
      icon: "",
    };
  return item;
};

// 情绪配置工厂
const getSentimentConfig = (sentiment?: string): SentimentConfig => {
  switch (sentiment) {
    case "bullish":
      return {
        color: "border-[var(--accent-green)]",
        bg: "bg-[var(--accent-green)]/10",
        bgHover: "bg-[var(--accent-green)]/15",
        border: "border-[var(--accent-green)]/20",
        borderSelected: "border-[var(--accent-green)]",
        icon: "📈",
        textColor: "text-[var(--accent-green)]",
        dotColor: "bg-[var(--accent-green)]",
        label: "Bullish",
      };
    case "bearish":
      return {
        color: "border-red-400",
        bg: "bg-red-400/10",
        bgHover: "bg-red-400/15",
        border: "border-red-400/20",
        borderSelected: "border-red-400",
        icon: "📉",
        textColor: "text-red-400",
        dotColor: "bg-red-400",
        label: "Bearish",
      };
    default:
      return {
        color: "border-[var(--border-color)]",
        bg: "bg-[var(--bg-card)]",
        bgHover: "bg-[var(--bg-card)]/80",
        border: "border-[var(--border-color)]",
        borderSelected: "border-[var(--border-color)]",
        icon: "📊",
        textColor: "text-[var(--text-secondary)]",
        dotColor: "bg-[var(--text-secondary)]",
        label: "Neutral",
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

// 格式化日期显示
const formatDateDisplay = (dateStr: string): string => {
  const date = new Date(dateStr);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (date.toDateString() === today.toDateString()) {
    return "Today";
  }
  if (date.toDateString() === yesterday.toDateString()) {
    return "Yesterday";
  }

  return date.toLocaleDateString("zh-CN", {
    month: "short",
    day: "numeric",
  });
};

// 格式化星期几
const formatWeekday = (dateStr: string): string => {
  const date = new Date(dateStr);
  const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  return weekdays[date.getDay()];
};

// 格式化时间
const formatTime = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

interface SignalTimelineProps {
  ticker?: string;
  onInsightSelect?: (insightId: number) => void;
  selectedInsightId?: number | null;
}

export default function SignalTimeline({
  ticker,
  onInsightSelect,
  selectedInsightId,
}: SignalTimelineProps) {
  const t = useTranslations('library');
  const [insights, setInsights] = useState<LibraryInsight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("all");
  const [sentimentFilter, setSentimentFilter] = useState<SentimentFilter>("all");
  const [signalFilter, setSignalFilter] = useState<SignalFilter>("all");
  const [expandedDates, setExpandedDates] = useState<Set<string>>(new Set());

  const loadInsights = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.listLibraryInsights({
        ticker,
        limit: 100,
      });
      setInsights(data);
      setError(null);

      // 默认展开第一个日期
      if (data.length > 0) {
        const firstDate = new Date(data[0].created_at).toDateString();
        setExpandedDates(new Set([firstDate]));
      }
    } catch (err) {
      console.error("Failed to load insights:", err);
      setError("Failed to load signals list");
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  useEffect(() => {
    loadInsights();
  }, [loadInsights]);

  // 根据筛选条件过滤
  const filteredInsights = useMemo(() => {
    return insights.filter((insight) => {
      if (sourceFilter !== "all" && insight.source_type !== sourceFilter) return false;
      if (sentimentFilter !== "all" && insight.sentiment !== sentimentFilter) return false;
      if (signalFilter !== "all" && insight.signal !== signalFilter) return false;
      return true;
    });
  }, [insights, sourceFilter, sentimentFilter, signalFilter]);

  // 按日期分组
  const groupedInsights = useMemo(() => {
    const groups: Record<string, LibraryInsight[]> = {};
    filteredInsights.forEach((insight) => {
      const date = new Date(insight.created_at).toDateString();
      if (!groups[date]) groups[date] = [];
      groups[date].push(insight);
    });
    return groups;
  }, [filteredInsights]);

  // 统计信息
  const stats = useMemo(() => {
    return {
      total: insights.length,
      bullish: insights.filter((i) => i.sentiment === "bullish").length,
      bearish: insights.filter((i) => i.sentiment === "bearish").length,
      neutral: insights.filter((i) => !i.sentiment || i.sentiment === "neutral").length,
      quickScan: insights.filter((i) => i.source_type === "quick_scan").length,
      technical: insights.filter((i) => i.source_type === "technical_diagnostic").length,
      crewAnalysis: insights.filter((i) => i.source_type === "crew_analysis").length,
    };
  }, [insights]);

  // 切换日期展开/折叠
  const toggleDate = (date: string) => {
    const newExpanded = new Set(expandedDates);
    if (newExpanded.has(date)) {
      newExpanded.delete(date);
    } else {
      newExpanded.add(date);
    }
    setExpandedDates(newExpanded);
  };

  const handleInsightClick = (insight: LibraryInsight) => {
    if (onInsightSelect) {
      onInsightSelect(insight.id);
    }
  };

  // 加载骨架屏
  if (loading) {
    return (
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="p-4 border-b border-[var(--border-color)]">
          <div className="h-7 w-32 bg-[var(--bg-card)] rounded animate-pulse"></div>
        </div>
        {/* Filters */}
        <div className="p-3 border-b border-[var(--border-color)] space-y-2">
          <div className="flex gap-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 flex-1 bg-[var(--bg-card)] rounded animate-pulse"></div>
            ))}
          </div>
          <div className="flex gap-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 flex-1 bg-[var(--bg-card)] rounded animate-pulse"></div>
            ))}
          </div>
        </div>
        {/* List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-[var(--bg-card)] rounded-lg animate-pulse"></div>
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
          onClick={loadInsights}
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
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          {t('signalTimeline')}
        </h2>
        <p className="text-sm text-[var(--text-secondary)] mt-1">
          {ticker ? `${ticker} · ` : ""}
          {t('records', { count: filteredInsights.length, total: stats.total })}
        </p>
      </div>

      {/* Filters */}
      <div className="p-3 border-b border-[var(--border-color)] space-y-2">
        {/* 来源类型筛选 */}
        <div className="flex flex-wrap gap-1.5">
          <span className="text-xs text-[var(--text-secondary)] mr-1 self-center">{t('filterSource')}</span>
          {[
            { key: "all" as SourceFilter, label: t('filterAll'), count: stats.total },
            { key: "quick_scan" as SourceFilter, label: t('filterQuick'), count: stats.quickScan },
            { key: "technical_diagnostic" as SourceFilter, label: t('filterTech'), count: stats.technical },
            { key: "crew_analysis" as SourceFilter, label: t('filterDeep'), count: stats.crewAnalysis },
          ].map((item) => (
            <button
              key={item.key}
              onClick={() => setSourceFilter(item.key)}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-all ${
                sourceFilter === item.key
                  ? "bg-[var(--accent-blue)]/20 text-[var(--accent-blue)] border border-[var(--accent-blue)]/30"
                  : "bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-card)]/80 border border-transparent"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* 情绪筛选 */}
        <div className="flex flex-wrap gap-1.5">
          <span className="text-xs text-[var(--text-secondary)] mr-1 self-center">{t('filterSentiment')}</span>
          {[
            { key: "all" as SentimentFilter, label: t('filterAll'), count: stats.total },
            { key: "bullish" as SentimentFilter, label: "Bullish", count: stats.bullish },
            { key: "neutral" as SentimentFilter, label: "Neutral", count: stats.neutral },
            { key: "bearish" as SentimentFilter, label: "Bearish", count: stats.bearish },
          ].map((item) => (
            <button
              key={item.key}
              onClick={() => setSentimentFilter(item.key)}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-all ${
                sentimentFilter === item.key
                  ? "bg-[var(--accent-blue)]/20 text-[var(--accent-blue)] border border-[var(--accent-blue)]/30"
                  : "bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-card)]/80 border border-transparent"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {Object.keys(groupedInsights).length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center px-4">
            <div className="w-16 h-16 rounded-full bg-[var(--bg-card)] flex items-center justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--text-secondary)]">
                <path d="M12 2v6"></path>
                <path d="m16.2 7.8 2.9-2.9"></path>
                <circle cx="12" cy="12" r="4"></circle>
                <path d="m7.8 7.8-2.9 2.9"></path>
                <path d="M2 12h6"></path>
                <path d="m7.8 16.2 2.9 2.9"></path>
                <path d="M12 22v-6"></path>
                <path d="m16.2 16.2-2.9 2.9"></path>
                <path d="M22 12h-6"></path>
                <path d="m7.8 7.8 2.9-2.9"></path>
              </svg>
            </div>
            <p className="text-[var(--text-secondary)]">
              {filteredInsights.length === 0 && insights.length > 0
                ? t('noMatchingSignals')
                : t('noSignalRecords')}
            </p>
            <p className="text-xs text-[var(--text-secondary)]/60 mt-1">
              {ticker ? t('selectOtherAssets') : t('selectAssetToView')}
            </p>
          </div>
        ) : (
          Object.entries(groupedInsights).map(([date, dateInsights]) => {
            const isExpanded = expandedDates.has(date);
            return (
              <div key={date} className="border-b border-[var(--border-color)]/50">
                {/* 日期分组头部 */}
                <button
                  onClick={() => toggleDate(date)}
                  className="w-full px-4 py-2.5 flex items-center justify-between hover:bg-[var(--bg-card)]/50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className={`text-[var(--text-secondary)] transition-transform ${isExpanded ? "rotate-90" : ""}`}
                    >
                      <path d="M9 18l6-6-6-6"></path>
                    </svg>
                    <span className="text-sm font-medium text-[var(--text-primary)]">
                      {formatDateDisplay(date)}
                    </span>
                    <span className="text-xs text-[var(--text-secondary)]">
                      {formatWeekday(date)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 text-xs bg-[var(--bg-card)] rounded-full">
                      {dateInsights.length}
                    </span>
                  </div>
                </button>

                {/* 展开的洞察列表 */}
                {isExpanded && (
                  <div className="pb-2 space-y-1 px-3">
                    {dateInsights.map((insight) => (
                      <InsightCard
                        key={insight.id}
                        insight={insight}
                        isSelected={selectedInsightId === insight.id}
                        onClick={() => handleInsightClick(insight)}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Footer Stats */}
      <div className="p-3 border-t border-[var(--border-color)] bg-[var(--bg-panel)]">
        <div className="flex justify-around">
          <StatItem label="Bullish" value={stats.bullish} color="text-[var(--accent-green)]" />
          <StatItem label="Neutral" value={stats.neutral} color="text-[var(--text-secondary)]" />
          <StatItem label="Bearish" value={stats.bearish} color="text-red-400" />
        </div>
      </div>
    </div>
  );
}

// 洞察卡片组件
interface InsightCardProps {
  insight: LibraryInsight;
  isSelected: boolean;
  onClick: () => void;
}

function InsightCard({ insight, isSelected, onClick }: InsightCardProps) {
  const sourceConfig = getSourceConfig(insight.source_type);
  const sentimentConfig = getSentimentConfig(insight.sentiment);
  const signalConfig = getSignalConfig(insight.signal);

  return (
    <div
      onClick={onClick}
      className={`relative p-3 rounded-lg border-l-4 cursor-pointer transition-all duration-200 ${
        isSelected
          ? "bg-[var(--bg-card)] border-l-[var(--border-color)] shadow-md"
          : `${sentimentConfig.bg} ${sentimentConfig.border} hover:${sentimentConfig.bgHover}`
      }`}
    >
      {/* Timeline dot */}
      <div
        className={`absolute -left-[5px] top-3 w-2.5 h-2.5 rounded-full ${sentimentConfig.dotColor} ${
          isSelected ? "ring-2 ring-[var(--accent-blue)] ring-offset-1 ring-offset-[var(--bg-panel)]" : ""
        }`}
      />

      {/* 顶部：来源 + 时间 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span
            className={`px-2 py-0.5 text-xs font-medium rounded border ${sourceConfig.bg} ${sourceConfig.color}`}
          >
            {sourceConfig.icon} {sourceConfig.label}
          </span>
        </div>
        <span className="text-xs text-[var(--text-secondary)]">{formatTime(insight.created_at)}</span>
      </div>

      {/* 标题 */}
      <h4 className="text-sm font-medium text-[var(--text-primary)] line-clamp-2 mb-1.5">
        {insight.title}
      </h4>

      {/* 摘要（如果有） */}
      {insight.summary && (
        <p className="text-xs text-[var(--text-secondary)] line-clamp-2 mb-2">
          {insight.summary}
        </p>
      )}

      {/* 底部：情绪 + 信号 + 附件 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${sentimentConfig.textColor}`}>
            {sentimentConfig.icon} {sentimentConfig.label}
          </span>
          {insight.signal && (
            <span
              className={`px-1.5 py-0.5 text-xs font-medium rounded border ${
                insight.signal === "buy"
                  ? "bg-[var(--accent-green)]/20 border-[var(--accent-green)]/30 text-[var(--accent-green)]"
                  : insight.signal === "sell"
                  ? "bg-red-400/20 border-red-400/30 text-red-400"
                  : "bg-[var(--bg-card)] border-[var(--border-color)] text-[var(--text-secondary)]"
              }`}
            >
              {signalConfig.icon} {insight.signal.toUpperCase()}
            </span>
          )}
        </div>

        {insight.attachments_count > 0 && (
          <div className="flex items-center gap-1 text-[var(--text-secondary)]">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
            </svg>
            <span className="text-xs">{insight.attachments_count}</span>
          </div>
        )}
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
      <div className={`font-bold text-base ${color}`}>{value}</div>
      <div className="text-[10px] text-[var(--text-secondary)]">{label}</div>
    </div>
  );
}
