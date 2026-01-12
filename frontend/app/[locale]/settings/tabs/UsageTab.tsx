"use client";

import React, { useState, useEffect } from "react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import { Activity, TrendingUp, TrendingDown, FileText, DollarSign, Calendar, ChevronLeft, ChevronRight } from "lucide-react";

interface UsageStats {
  total_tokens_current_month: number;
  total_tokens_previous_month: number;
  token_growth_percentage: number;
  reports_generated_current_month: number;
  estimated_cost_current_month: number;
  currency: string;
}

interface UsageActivityItem {
  id: number;
  date: string;
  time: string;
  activity: string;
  model: string;
  reports: number;
  tokens: number;
}

interface UsageActivityResponse {
  items: UsageActivityItem[];
  total_count: number;
  current_page: number;
  total_pages: number;
}

export function UsageTab() {
  const t = useTranslations("settings");
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [activity, setActivity] = useState<UsageActivityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activityLoading, setActivityLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    fetchUsageStats();
    fetchActivityLog(1);
  }, []);

  const fetchUsageStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getUsageStats();
      setStats(data);
    } catch (err: any) {
      console.error("{t('failed')} to load usage stats:", err);
      setError(err.message || "{t('failed')} to load usage statistics");
    } finally {
      setLoading(false);
    }
  };

  const fetchActivityLog = async (page: number) => {
    try {
      setActivityLoading(true);
      const data = await apiClient.getUsageActivity({
        page,
        page_size: pageSize,
      });
      setActivity(data);
      setCurrentPage(page);
    } catch (err: any) {
      console.error("{t('failed')} to load activity log:", err);
      setError(err.message || "{t('failed')} to load activity log");
    } finally {
      setActivityLoading(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && activity && newPage <= activity.total_pages) {
      fetchActivityLog(newPage);
    }
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold mb-2">Usage Statistics</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Track your API usage and activity.
          </p>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--accent-primary)]"></div>
        </div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold mb-2">Usage Statistics</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Track your API usage and activity.
          </p>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-800">Error: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold mb-2">Usage Statistics</h2>
        <p className="text-sm text-[var(--text-secondary)]">
          Track your API usage and activity for the current month.
        </p>
      </div>

      {/* Stats Grid */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Current Month {t('tokens')} */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-[var(--text-secondary)]">{t('tokens')} Used</span>
              <Activity className="w-4 h-4 text-[var(--text-secondary)]" />
            </div>
            <div className="text-2xl font-bold text-[var(--text-primary)]">
              {formatNumber(stats.total_tokens_current_month)}
            </div>
            <div className="flex items-center gap-1 mt-1">
              {stats.token_growth_percentage >= 0 ? (
                <TrendingUp className="w-3 h-3 text-green-500" />
              ) : (
                <TrendingDown className="w-3 h-3 text-red-500" />
              )}
              <span className={`text-xs ${stats.token_growth_percentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {stats.token_growth_percentage >= 0 ? '+' : ''}{stats.token_growth_percentage.toFixed(1)}% from last month
              </span>
            </div>
          </div>

          {/* Previous Month {t('tokens')} */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-[var(--text-secondary)]">{t('lastMonth')}</span>
              <Calendar className="w-4 h-4 text-[var(--text-secondary)]" />
            </div>
            <div className="text-2xl font-bold text-[var(--text-primary)]">
              {formatNumber(stats.total_tokens_previous_month)}
            </div>
            <div className="text-xs text-[var(--text-secondary)] mt-1">
              Previous month tokens
            </div>
          </div>

          {/* {t('reports')} Generated */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-[var(--text-secondary)]">{t('reports')}</span>
              <FileText className="w-4 h-4 text-[var(--text-secondary)]" />
            </div>
            <div className="text-2xl font-bold text-[var(--text-primary)]">
              {formatNumber(stats.reports_generated_current_month)}
            </div>
            <div className="text-xs text-[var(--text-secondary)] mt-1">
              Generated this month
            </div>
          </div>

          {/* Estimated Cost */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-[var(--text-secondary)]">Estimated Cost</span>
              <DollarSign className="w-4 h-4 text-[var(--text-secondary)]" />
            </div>
            <div className="text-2xl font-bold text-[var(--text-primary)]">
              ${stats.estimated_cost_current_month.toFixed(2)}
            </div>
            <div className="text-xs text-[var(--text-secondary)] mt-1">
              {stats.currency} this month
            </div>
          </div>
        </div>
      )}

      {/* Activity Log */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-[var(--border-color)]">
          <h3 className="text-lg font-semibold text-[var(--text-primary)]">Recent Activity</h3>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            View your recent analysis runs and token usage
          </p>
        </div>

        {activityLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[var(--accent-primary)]"></div>
          </div>
        ) : activity && activity.items.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-[var(--bg-panel)]">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                      {t('date')} & {t('time')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                      Activity
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                      Model
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                      {t('tokens')}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-color)]">
                  {activity.items.map((item) => (
                    <tr key={item.id} className="hover:bg-[var(--bg-panel)] transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-[var(--text-primary)]">
                        <div>{item.date}</div>
                        <div className="text-xs text-[var(--text-secondary)]">{item.time}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-[var(--text-primary)]">
                        {item.activity}
                      </td>
                      <td className="px-6 py-4 text-sm text-[var(--text-secondary)]">
                        {item.model}
                      </td>
                      <td className="px-6 py-4 text-sm text-right font-mono text-[var(--text-primary)]">
                        {formatNumber(item.tokens)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {activity.total_pages > 1 && (
              <div className="px-6 py-4 border-t border-[var(--border-color)] flex items-center justify-between">
                <div className="text-sm text-[var(--text-secondary)]">
                  Page {activity.current_page} of {activity.total_pages} ({formatNumber(activity.total_count)} total)
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="px-3 py-1 text-sm border border-[var(--border-color)] rounded-md hover:bg-[var(--bg-panel)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === activity.total_pages}
                    className="px-3 py-1 text-sm border border-[var(--border-color)] rounded-md hover:bg-[var(--bg-panel)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="px-6 py-12 text-center">
            <Activity className="w-12 h-12 text-[var(--text-secondary)] mx-auto mb-3 opacity-50" />
            <p className="text-[var(--text-secondary)]">{t('noActivityRecordedYet')}</p>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Your analysis runs will appear here
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
