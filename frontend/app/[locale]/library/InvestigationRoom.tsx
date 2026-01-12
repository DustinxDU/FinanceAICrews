"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { useTranslations } from 'next-intl';
import apiClient from "@/lib/api";
import type { LibraryInsightDetail, LibraryInsight } from "@/lib/types";
import { getToken } from "@/lib/auth";
import { LogItem, LogItemComponent } from "../dashboard/page";
import { Play, Pause, RotateCcw, FastForward, Clock, Star, Share2, MoreHorizontal } from "lucide-react";

// 信号配置
interface SignalConfig {
  icon: string;
  color: string;
  bg: string;
  variant: "success" | "destructive" | "warning" | "secondary";
}

// 信号配置工厂
const getSignalConfig = (signal?: string): SignalConfig => {
  switch (signal) {
    case "buy":
      return { icon: "🟢", color: "text-[var(--accent-green)]", bg: "bg-[var(--accent-green)]/20", variant: "success" };
    case "sell":
      return { icon: "🔴", color: "text-red-400", bg: "bg-red-400/20", variant: "destructive" };
    case "hold":
      return { icon: "🟡", color: "text-[var(--accent-yellow)]", bg: "bg-[var(--accent-yellow)]/20", variant: "warning" };
    default:
      return { icon: "⚪", color: "text-[var(--text-secondary)]", bg: "bg-[var(--bg-card)]", variant: "secondary" };
  }
};

// 来源配置
interface SourceConfig {
  label: string;
  color: string;
  bg: string;
  border: string;
  icon: string;
}

const getSourceConfig = (sourceType: string): SourceConfig => {
  const config: Record<string, SourceConfig> = {
    quick_scan: { label: "Quick Scan", color: "text-blue-400", bg: "bg-blue-400/10", border: "border-blue-400/30", icon: "" },
    technical_diagnostic: { label: "Technical Diagnostic", color: "text-purple-400", bg: "bg-purple-400/10", border: "border-purple-400/30", icon: "" },
    crew_analysis: { label: "Crew Analysis", color: "text-[var(--accent-green)]", bg: "bg-[var(--accent-green)]/10", border: "border-[var(--accent-green)]/30", icon: "" },
  };
  const item = config[sourceType] || { label: sourceType, color: "text-[var(--text-secondary)]", bg: "bg-[var(--bg-card)]", border: "border-[var(--border-color)]", icon: "" };
  return item;
};

// 情绪配置
interface SentimentConfig {
  bg: string;
  color: string;
  icon: string;
  label: string;
}

const getSentimentConfig = (sentiment?: string): SentimentConfig => {
  switch (sentiment) {
    case "bullish":
      return { bg: "bg-[var(--accent-green)]/20 border-[var(--accent-green)]/30", color: "text-[var(--accent-green)]", icon: "", label: "Bullish" };
    case "bearish":
      return { bg: "bg-red-400/20 border-red-400/30", color: "text-red-400", icon: "", label: "Bearish" };
    default:
      return { bg: "bg-[var(--bg-card)] border-[var(--border-color)]", color: "text-[var(--text-secondary)]", icon: "", label: "Neutral" };
  }
};

// 格式化数字
const formatValue = (key: string, value: number | string | null | undefined): string => {
  if (value === null || value === undefined) return "-";
  if (typeof value === "string") return value;
  if (key.includes("percent") || key.includes("change") || key.includes("growth") || key.includes("yield")) {
    return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
  }
  if (key.includes("price") || key.includes("volume") || key.includes("market_cap")) {
    if (value >= 1000000) return `${(value / 1000000).toFixed(2)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(2)}K`;
    return value.toLocaleString();
  }
  if (key.includes("ratio") || key.includes("rate") || key.includes("pe") || key.includes("pb")) {
    return value.toFixed(2);
  }
  return String(value);
};

// 格式化文件名
const formatFileSize = (bytes?: number): string => {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

// 获取文件类型图标
const getFileTypeIcon = (fileType?: string): string => {
  switch (fileType) {
    case "excel": return "📊";
    case "pdf": return "📄";
    case "markdown": return "📝";
    case "csv": return "📈";
    case "json": return "📋";
    default: return "📁";
  }
};

interface InvestigationRoomProps {
  insightId: number;
  insight?: LibraryInsight | null;
  onClose?: () => void;
}

export default function InvestigationRoom({ insightId, insight: initialInsight, onClose }: InvestigationRoomProps) {
  const t = useTranslations('library');
  const tCommon = useTranslations('common');

  const [detail, setDetail] = useState<LibraryInsightDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"content" | "traces" | "attachments">("content");
  const [isFavorite, setIsFavorite] = useState(false);
  const [isRead, setIsRead] = useState(false);

  // Playback State
  const [isPlaybackActive, setIsPlaybackActive] = useState(false);
  const [playbackIndex, setPlaybackIndex] = useState(-1);
  const [playbackSpeed, setPlaybackSpeed] = useState(1000);
  const playbackTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Playback effect
  useEffect(() => {
    if (isPlaybackActive && detail && detail.traces) {
      playbackTimerRef.current = setInterval(() => {
        setPlaybackIndex((prev) => {
          if (prev >= (detail.traces?.length || 0) - 1) {
            setIsPlaybackActive(false);
            return prev;
          }
          return prev + 1;
        });
      }, playbackSpeed);
    } else {
      if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
    }
    return () => { if (playbackTimerRef.current) clearInterval(playbackTimerRef.current); };
  }, [isPlaybackActive, detail, playbackSpeed]);

  const resetPlayback = () => {
    setIsPlaybackActive(false);
    setPlaybackIndex(-1);
  };

  const loadDetail = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.getLibraryInsightDetail(insightId);
      setDetail(data);
      setError(null);
      setIsFavorite(data.insight.is_favorite || false);
      setIsRead(data.insight.is_read || false);
    } catch (err) {
      console.error("Failed to load insight detail:", err);
      setError(t('failedToLoad'));
    } finally {
      setLoading(false);
    }
  }, [insightId, t]);

  useEffect(() => {
    if (insightId) {
      loadDetail();
      apiClient.markLibraryInsightAsRead(insightId).catch(console.error);
    }
  }, [insightId, loadDetail]);

  // 切换收藏
  const handleToggleFavorite = async () => {
    try {
      await apiClient.toggleLibraryInsightFavorite(insightId, !isFavorite);
      setIsFavorite(!isFavorite);
    } catch (err) {
      console.error("Failed to toggle favorite:", err);
    }
  };

  // 下载处理
  const handleDownload = async (attachmentId: number, filename: string) => {
    try {
      const token = getToken();
      const response = await fetch(`/api/v1/library/attachments/${attachmentId}/download`, {
        headers: { Authorization: token ? `Bearer ${token}` : "" },
      });
      if (!response.ok) throw new Error("Download failed");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Failed to download attachment:", err);
      alert(t('download') + " failed");
    }
  };

  // 骨架屏
  if (loading) {
    return (
      <div className="flex flex-col h-full bg-[var(--bg-panel)]">
        <div className="p-4 border-b border-[var(--border-color)]">
          <div className="h-8 w-64 bg-[var(--bg-card)] rounded animate-pulse"></div>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <div className="h-48 bg-[var(--bg-card)] rounded animate-pulse mb-4"></div>
          <div className="h-32 bg-[var(--bg-card)] rounded animate-pulse"></div>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error || !detail) {
    return (
      <div className="flex flex-col h-full items-center justify-center p-8">
        <div className="text-red-400 mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" x2="12" y1="8" y2="12"></line>
            <line x1="12" x2="12.01" y1="16" y2="16"></line>
          </svg>
        </div>
        <p className="text-[var(--text-secondary)]">{error || t('detailNotFound')}</p>
      </div>
    );
  }

  const { insight, traces, attachments } = detail;
  const sourceConfig = getSourceConfig(insight.source_type);
  const sentimentConfig = getSentimentConfig(insight.sentiment);
  const signalConfig = getSignalConfig(insight.signal);

  return (
    <div className="flex flex-col h-full bg-[var(--bg-panel)]">
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-color)]">
        {/* 标签行 */}
        <div className="flex items-center gap-2 flex-wrap mb-3">
          <span className={`px-2 py-0.5 text-xs font-medium rounded border ${sourceConfig.bg} ${sourceConfig.color}`}>
            {sourceConfig.label}
          </span>
          <span className={`px-2 py-0.5 text-xs font-medium rounded border ${sentimentConfig.bg} ${sentimentConfig.color}`}>
            {sentimentConfig.label}
          </span>
          {insight.signal && (
            <span className={`px-2 py-0.5 text-xs font-medium rounded border ${signalConfig.bg} ${signalConfig.color}`}>
              {insight.signal.toUpperCase()}
            </span>
          )}
          {insight.crew_name && (
            <span className="px-2 py-0.5 text-xs font-medium rounded border bg-[var(--bg-card)] border-[var(--border-color)] text-[var(--text-secondary)]">
              {insight.crew_name}
            </span>
          )}
        </div>

        {/* 标题 */}
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-2">{insight.title}</h2>

        {/* 元信息行 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-sm text-[var(--text-secondary)]">
            <span className="flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
              {new Date(insight.created_at).toLocaleString("zh-CN")}
            </span>
            {insight.ticker && (
              <span className="flex items-center gap-1 font-medium text-[var(--accent-blue)]">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                </svg>
                {insight.ticker}
              </span>
            )}
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center gap-1">
            <button
              onClick={handleToggleFavorite}
              className={`p-2 rounded-lg transition-colors ${
                isFavorite
                  ? "bg-yellow-400/20 text-yellow-400"
                  : "bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-yellow-400"
              }`}
              title={isFavorite ? t('removeFromFavorites') : t('addToFavorites')}
            >
              <Star className={`w-4 h-4 ${isFavorite ? "fill-current" : ""}`} />
            </button>
            <button
              className="p-2 rounded-lg bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--accent-blue)] transition-colors"
              title={t('share')}
            >
              <Share2 className="w-4 h-4" />
            </button>
            <button
              className="p-2 rounded-lg bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
              title={t('more')}
            >
              <MoreHorizontal className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 关键指标网格 */}
      {insight.key_metrics && Object.keys(insight.key_metrics).length > 0 && (
        <div className="p-4 border-b border-[var(--border-color)] bg-[var(--bg-panel)]">
          <h3 className="text-xs font-medium text-[var(--text-secondary)] mb-3 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20V10"></path>
              <path d="M18 20V4"></path>
              <path d="M6 20v-4"></path>
            </svg>
            {t('keyMetrics')}
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {Object.entries(insight.key_metrics).slice(0, 8).map(([key, value]) => (
              <div
                key={key}
                className="bg-[var(--bg-card)] rounded-lg p-2.5 border border-[var(--border-color)]"
              >
                <div className="text-[10px] text-[var(--text-secondary)] capitalize truncate" title={key}>
                  {key.replace(/_/g, " ")}
                </div>
                <div className="font-semibold text-[var(--text-primary)] mt-0.5 truncate" title={String(value)}>
                  {formatValue(key, value as number)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[var(--border-color)]">
        {[
          { key: "content", label: t('content'), icon: "📄" },
          { key: "traces", label: t('actionLog'), count: traces.length, icon: "🔍" },
          { key: "attachments", label: t('attachments'), count: attachments.length, icon: "📎" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as "content" | "traces" | "attachments")}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? "border-[var(--accent-blue)] text-[var(--accent-blue)]"
                : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
            {tab.count !== undefined && tab.count > 0 && (
              <span className={`px-1.5 py-0.5 text-xs rounded-full ${
                activeTab === tab.key ? "bg-[var(--accent-blue)]/20" : "bg-[var(--bg-card)]"
              }`}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {activeTab === "content" && (
          <div className="p-4 space-y-4">
            {/* 摘要 */}
            {insight.summary && (
              <div className="bg-[var(--bg-card)] rounded-lg p-4 border border-[var(--border-color)]">
                <h3 className="text-xs font-medium text-[var(--text-secondary)] mb-2 flex items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="21" x2="9" y1="10" y2="10"></line>
                    <line x1="9" x2="9" y1="10" y2="20"></line>
                    <line x1="15" x2="15" y1="10" y2="20"></line>
                  </svg>
                  {t('coreSummary')}
                </h3>
                <p className="text-[var(--text-primary)] text-sm leading-relaxed">{insight.summary}</p>
              </div>
            )}

            {/* 新闻要点 (from raw_data) */}
            {insight.raw_data?.news_highlights && insight.raw_data.news_highlights.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-[var(--text-secondary)] mb-2 flex items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"></path>
                    <path d="M18 14h-8"></path>
                    <path d="M15 18h-5"></path>
                    <path d="M10 6h8v4h-8V6Z"></path>
                  </svg>
                  {t('newsHighlights')}
                </h3>
                <div className="bg-[var(--bg-card)] rounded-lg p-4 border border-[var(--border-color)] space-y-2">
                  {insight.raw_data.news_highlights.map((highlight: string, index: number) => (
                    <div key={index} className="flex items-start gap-2 text-sm text-[var(--text-primary)]">
                      <span className="text-[var(--accent-blue)] mt-1">•</span>
                      <span>{highlight}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 完整内容 */}
            {insight.content && (
              <div>
                <h3 className="text-xs font-medium text-[var(--text-secondary)] mb-2 flex items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                  </svg>
                  {t('fullReport')}
                </h3>
                <div
                  className="bg-[var(--bg-card)] rounded-lg p-4 border border-[var(--border-color)] text-sm leading-relaxed whitespace-pre-wrap"
                  dangerouslySetInnerHTML={{
                    __html: insight.content
                      .replace(/##\s+(.*)/g, "<h4 class='font-bold mt-4 mb-2 text-[var(--text-primary)]'>$1</h4>")
                      .replace(/\*\*(.*?)\*\*/g, "<strong class='text-[var(--accent-green)]'>$1</strong>")
                      .replace(/[-*]\s+(.*)/g, "<li class='ml-4 text-[var(--text-secondary)]'>$1</li>"),
                  }}
                />
              </div>
            )}

            {/* 执行时间 */}
            {insight.raw_data?.execution_time_ms && (
              <div className="text-xs text-[var(--text-secondary)] text-right flex items-center justify-end gap-1">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                {t('analysisTime', { x: insight.raw_data.execution_time_ms })}
              </div>
            )}
          </div>
        )}

        {activeTab === "traces" && (
          <div className="p-4 space-y-4">
            {traces.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-16 h-16 rounded-full bg-[var(--bg-card)] flex items-center justify-center mb-4">
                  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--text-secondary)]">
                    <circle cx="11" cy="11" r="8"></circle>
                    <path d="m21 21-4.3-4.3"></path>
                  </svg>
                </div>
                <p className="text-[var(--text-secondary)]">{t('noActionLogsYet')}</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Playback Controls */}
                <div className="flex items-center justify-between bg-[var(--bg-card)] p-3 rounded-lg border border-[var(--border-color)]">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">{t('tracePlayback')}</span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setIsPlaybackActive(!isPlaybackActive)}
                        className="p-1.5 rounded hover:bg-[var(--bg-panel)] text-[var(--accent-blue)] transition-colors"
                        title={isPlaybackActive ? t('pause') : t('play')}
                      >
                        {isPlaybackActive ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                      </button>
                      <button
                        onClick={resetPlayback}
                        className="p-1.5 rounded hover:bg-[var(--bg-panel)] text-[var(--text-secondary)] transition-colors"
                        title={t('reset')}
                      >
                        <RotateCcw className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setPlaybackSpeed(Math.max(250, playbackSpeed / 2))}
                        className="p-1.5 rounded hover:bg-[var(--bg-panel)] text-[var(--text-secondary)] transition-colors"
                        title={t('speedUp')}
                      >
                        <FastForward className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setPlaybackSpeed(Math.min(4000, playbackSpeed * 2))}
                        className="p-1.5 rounded hover:bg-[var(--bg-panel)] text-[var(--text-secondary)] transition-colors"
                        title={t('slowDown')}
                      >
                        <Clock className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[var(--text-secondary)] font-mono">
                      {playbackIndex + 1} / {traces.length}
                    </span>
                    <span className="text-[10px] bg-[var(--accent-blue)]/10 text-[var(--accent-blue)] px-1.5 py-0.5 rounded border border-[var(--accent-blue)]/20">
                      V3
                    </span>
                  </div>
                </div>

                {/* Traces by Agent */}
                {Object.entries(
                  (playbackIndex === -1 ? traces : traces.slice(0, playbackIndex + 1)).reduce((acc, trace) => {
                    const agent = trace.agent_name || "System";
                    if (!acc[agent]) acc[agent] = [];
                    acc[agent].push(trace);
                    return acc;
                  }, {} as Record<string, typeof traces>)
                ).map(([agent, agentTraces]) => (
                  <div key={agent} className="space-y-3">
                    <div className="flex items-center gap-2">
                      <div className="h-[1px] flex-1 bg-[var(--border-color)]" />
                      <span className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-wider px-2">{agent}</span>
                      <div className="h-[1px] flex-1 bg-[var(--border-color)]" />
                    </div>
                    <div className="space-y-1">
                      {agentTraces.map((trace, index) => {
                        const logItem: LogItem = {
                          id: trace.id || `trace-${index}`,
                          agent: trace.agent_name || "System",
                          status: "completed",
                          message: trace.content || `${trace.action_type}`,
                          timestamp: trace.created_at ? new Date(trace.created_at).toLocaleTimeString() : "",
                          type: trace.action_type,
                          payload: trace.input_data || trace.output_data ? { input: trace.input_data, output: trace.output_data } : undefined,
                          detail: trace.tokens_used ? `Tokens: ${trace.tokens_used}` : undefined
                        };
                        return <LogItemComponent key={index} log={logItem} />;
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "attachments" && (
          <div className="p-4 space-y-3">
            {attachments.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-16 h-16 rounded-full bg-[var(--bg-card)] flex items-center justify-center mb-4">
                  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--text-secondary)]">
                    <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                  </svg>
                </div>
                <p className="text-[var(--text-secondary)]">{t('noAttachments')}</p>
                <p className="text-xs text-[var(--text-secondary)]/60 mt-1">{t('filesGeneratedHint')}</p>
              </div>
            ) : (
              <div className="grid gap-3">
                {attachments.map((attachment) => (
                  <div
                    key={attachment.id}
                    className="flex items-center justify-between p-3 bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)]
                      hover:border-[var(--accent-blue)]/50 transition-all group"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl ${
                        attachment.file_type === "excel" ? "bg-green-400/10" :
                        attachment.file_type === "pdf" ? "bg-red-400/10" :
                        attachment.file_type === "markdown" ? "bg-blue-400/10" :
                        "bg-[var(--bg-panel)]"
                      }`}>
                        {getFileTypeIcon(attachment.file_type)}
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-[var(--text-primary)] truncate">{attachment.file_name}</p>
                        <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                          <span className="px-1.5 py-0.5 bg-[var(--bg-panel)] rounded border border-[var(--border-color)]">
                            {attachment.file_type?.toUpperCase() || "FILE"}
                          </span>
                          {attachment.file_size && (
                            <span>{formatFileSize(attachment.file_size)}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDownload(attachment.id, attachment.file_name)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-[var(--accent-blue)] text-white rounded
                        hover:bg-[var(--accent-blue)]/80 transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" x2="12" y1="15" y2="3"></line>
                      </svg>
                      {t('download')}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
