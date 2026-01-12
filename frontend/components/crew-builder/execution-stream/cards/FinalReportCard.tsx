'use client';

import React, { useState, lazy, Suspense } from 'react';
import { Trophy, Clock, Zap, Wrench, ChevronDown, ChevronUp, Image, Loader2 } from 'lucide-react';
import { RunSummary } from '@/lib/types';
import { generateReportDSL } from '../reportDSLGenerator';

// Lazy load InfographicReport to reduce bundle size
const InfographicReport = lazy(() => import('../InfographicReport'));

interface FinalReportCardProps {
  content: string;
  summary?: RunSummary;
  ticker?: string;
  crewName?: string;
}

export const FinalReportCard = ({ content, summary, ticker, crewName }: FinalReportCardProps) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showInfographic, setShowInfographic] = useState(false);
  const [reportDSL, setReportDSL] = useState<string | null>(null);

  // Generate infographic report DSL
  const handleGenerateReport = () => {
    const dsl = generateReportDSL({
      ticker,
      crewName,
      content,
      summary,
    });
    setReportDSL(dsl);
    setShowInfographic(true);
  };

  return (
    <div className="border-2 border-green-400 bg-gradient-to-br from-green-900/40 via-emerald-900/30 to-teal-900/20 rounded-xl shadow-2xl ring-2 ring-green-400/30 overflow-hidden">
      {/* Hero Header */}
      <div className="bg-gradient-to-r from-green-600/30 to-emerald-600/20 px-6 py-4 border-b border-green-500/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-500/30 rounded-lg">
              <Trophy size={24} className="text-green-300" />
            </div>
            <div>
              <h3 className="font-bold text-green-200 text-lg tracking-wide">
                FINAL REPORT
              </h3>
              <div className="flex items-center gap-2 text-xs text-gray-400">
                {ticker && <span className="text-green-400 font-mono">{ticker}</span>}
                {crewName && <span>· {crewName}</span>}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Generate Infographic Button */}
            <button
              onClick={handleGenerateReport}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                showInfographic
                  ? 'bg-purple-500/30 text-purple-300 ring-1 ring-purple-400/50'
                  : 'bg-green-500/20 text-green-300 hover:bg-green-500/30'
              }`}
              title="Generate visual report"
            >
              <Image size={14} />
              {showInfographic ? 'Infographic' : 'Generate Report'}
            </button>

            {/* Expand/Collapse Button */}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-2 hover:bg-green-500/20 rounded transition-colors"
            >
              {isExpanded ? (
                <ChevronUp size={20} className="text-green-400" />
              ) : (
                <ChevronDown size={20} className="text-green-400" />
              )}
            </button>
          </div>
        </div>

        {/* Summary Stats */}
        {summary && (
          <div className="flex gap-6 mt-4 text-xs">
            <div className="flex items-center gap-1.5 text-gray-300">
              <Clock size={12} className="text-green-400" />
              <span>{formatDuration(summary.total_duration_ms)}</span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-300">
              <Zap size={12} className="text-purple-400" />
              <span>{summary.total_tokens?.toLocaleString() || 0} tokens</span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-300">
              <Wrench size={12} className="text-yellow-400" />
              <span>{summary.tool_calls_count || 0} tool calls</span>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-6">
          {/* Tab Switch: Text / Infographic */}
          {showInfographic && (
            <div className="flex gap-2 mb-4 border-b border-green-500/30 pb-3">
              <button
                onClick={() => setShowInfographic(false)}
                className={`px-3 py-1.5 rounded-t-lg text-xs font-medium transition-colors ${
                  !showInfographic
                    ? 'bg-green-500/20 text-green-300'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                Text Report
              </button>
              <button
                onClick={() => setShowInfographic(true)}
                className={`px-3 py-1.5 rounded-t-lg text-xs font-medium transition-colors ${
                  showInfographic
                    ? 'bg-purple-500/20 text-purple-300'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                Visual Report
              </button>
            </div>
          )}

          {/* Infographic View */}
          {showInfographic && reportDSL ? (
            <Suspense
              fallback={
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-purple-400" />
                  <span className="ml-2 text-sm text-gray-400">Loading infographic engine...</span>
                </div>
              }
            >
              <InfographicReport
                dsl={reportDSL}
                title={`${ticker || 'Analysis'} Report`}
                width={560}
                height={400}
                className="mb-4"
              />
            </Suspense>
          ) : (
            /* Text View */
            <div className="prose prose-invert prose-sm max-w-none">
              <div className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap font-sans">
                {content || 'No final report available'}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

function formatDuration(ms?: number): string {
  if (!ms) return '-';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = ((ms % 60000) / 1000).toFixed(0);
  return `${minutes}m ${seconds}s`;
}
