"use client";

import React, { useState, useEffect, Suspense, useRef, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { AppLayout } from "@/components/layout";
import { withAuth } from "@/contexts/AuthContext";
import apiClient, { QuickScanResponse, ChartAnalysisResponse } from "@/lib/api";
import {
  Zap, Activity, Loader2, ArrowLeft, TrendingUp, TrendingDown,
  Minus, Clock, BarChart3, Target
} from "lucide-react";
import { Link } from "@/i18n/routing";

function AnalysisResultContent() {
  const searchParams = useSearchParams();
  const ticker = searchParams.get('ticker') || '';
  const mode = searchParams.get('mode') || 'quick';
  const thesis = searchParams.get('thesis') || undefined;
  const autoRun = searchParams.get('auto_run') === 'true';

  const t = useTranslations('cockpit');

  const [isLoading, setIsLoading] = useState(false);
  const [quickResult, setQuickResult] = useState<QuickScanResponse | null>(null);
  const [chartResult, setChartResult] = useState<ChartAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 使用 ref 防止 React Strict Mode 下的重复调用
  const hasRunRef = useRef(false);

  const runAnalysis = useCallback(async () => {
    if (!ticker) return;

    setIsLoading(true);
    setError(null);

    try {
      if (mode === 'quick') {
        const result = await apiClient.runQuickScan(ticker, thesis);
        setQuickResult(result);
      } else if (mode === 'chart') {
        const result = await apiClient.runChartAnalysis(ticker, thesis);
        setChartResult(result);
      }
    } catch (err: any) {
      console.error('Analysis error:', err);

      // Handle structured error responses from backend
      let errorMessage = 'Analysis failed';
      if (err.response?.data?.detail) {
        // Backend returned structured error in detail field
        if (typeof err.response.data.detail === 'object') {
          // New structured format
          errorMessage = JSON.stringify(err.response.data.detail);
        } else {
          // Simple string message
          errorMessage = err.response.data.detail;
        }
      } else if (err.message) {
        errorMessage = err.message;
      }

      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [ticker, mode, thesis]);

  useEffect(() => {
    // 防止 React Strict Mode 下的重复调用
    if (autoRun && ticker && !hasRunRef.current) {
      hasRunRef.current = true;
      runAnalysis();
    }
  }, [autoRun, ticker, runAnalysis]);

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case 'bullish': return <TrendingUp className="w-5 h-5 text-green-400" />;
      case 'bearish': return <TrendingDown className="w-5 h-5 text-red-400" />;
      default: return <Minus className="w-5 h-5 text-yellow-400" />;
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'bullish': return 'text-green-400 bg-green-900/20 border-green-500/30';
      case 'bearish': return 'text-red-400 bg-red-900/20 border-red-500/30';
      default: return 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30';
    }
  };

  const getMainErrorMessage = (error: string) => {
    try {
      // Try to parse as JSON (structured error from backend)
      const errorData = JSON.parse(error);
      return errorData.message || error;
    } catch {
      // Fallback to original error string
      return error;
    }
  };

  const getErrorDetails = (error: string): string[] | null => {
    try {
      // Try to parse as JSON (structured error from backend)
      const errorData = JSON.parse(error);
      if (errorData.details) {
        const details = [];
        if (errorData.error_type) details.push(`${t('errorType')}: ${errorData.error_type}`);
        if (errorData.timestamp) details.push(`${t('timestamp')}: ${new Date(errorData.timestamp).toLocaleString()}`);
        if (errorData.details.llm_config_available !== undefined) {
          details.push(`${t('configStatus', { status: errorData.details.llm_config_available ? t('configured') : t('notConfigured') })}`);
        }
        if (errorData.details.request_thesis !== undefined) {
          details.push(`${t('thesisStatus', { status: errorData.details.request_thesis ? t('provided') : t('notProvided') })}`);
        }
        return details.length > 0 ? details : null;
      }
    } catch {
      // Not a JSON error, return null
    }
    return null;
  };

  return (
    <div className="min-h-screen bg-[var(--bg-app)] p-8">
      {/* Header */}
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <Link 
            href="/cockpit"
            className="p-2 rounded-lg border border-[var(--border-color)] hover:bg-[var(--bg-panel)] transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              {mode === 'quick' ? (
                <><Zap className="w-6 h-6 text-green-400" /> Quick Scan</>
              ) : (
                <><Activity className="w-6 h-6 text-yellow-400" /> Technical Analysis</>
              )}
            </h1>
            <p className="text-[var(--text-secondary)]">
              {ticker} • {mode === 'quick' ? t('quickScan') : t('technicalDiagnostic')}
            </p>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-12 h-12 animate-spin text-blue-400 mb-4" />
            <p className="text-lg">{t('analyzing', { ticker })}</p>
            <p className="text-sm text-[var(--text-secondary)]">
              {mode === 'quick' ? t('estimatedTimeQuick') : t('estimatedTimeTech')}
            </p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-6 mb-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-6 h-6 rounded-full bg-red-600 flex items-center justify-center">
                <span className="text-white text-sm font-bold">!</span>
              </div>
              <p className="text-red-400 font-bold">{t('analysisFailed')}</p>
            </div>
            
            <div className="space-y-4">
              {/* Main Error Message */}
              <div className="bg-red-900/10 border border-red-700/20 rounded-lg p-4">
                <p className="text-red-300 text-sm leading-relaxed">{getMainErrorMessage(error)}</p>
              </div>
              
              {/* Error Details - if available */}
              {getErrorDetails(error) && (
                <details className="group">
                  <summary className="cursor-pointer text-red-400 text-sm font-medium hover:text-red-300 transition-colors">
                    {t('viewDetails')} <span className="group-open:rotate-90 transition-transform">▶</span>
                  </summary>
                  <div className="mt-3 space-y-2 text-xs">
                    {getErrorDetails(error)?.map((detail, index) => (
                      <div key={index} className="flex">
                        <span className="text-red-400 mr-2 font-mono">•</span>
                        <span className="text-red-300/80">{detail}</span>
                      </div>
                    ))}
                  </div>
                </details>
              )}
              
              {/* Retry Button */}
              <button 
                onClick={runAnalysis}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500 transition-colors flex items-center gap-2"
              >
                <span>{t('retryAnalysis')}</span>
                <span className="text-xs opacity-75">({ticker})</span>
              </button>
            </div>
          </div>
        )}

        {/* Quick Scan Result */}
        {quickResult && (
          <div className="space-y-6">
            {/* Sentiment Badge */}
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border ${getSentimentColor(quickResult.sentiment)}`}>
              {getSentimentIcon(quickResult.sentiment)}
              <span className="font-bold uppercase">{quickResult.sentiment}</span>
            </div>

            {/* Summary */}
            <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-6">
              <h2 className="text-lg font-bold mb-4">{t('analysisSummary')}</h2>
              <div className="prose prose-invert max-w-none">
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                  {quickResult.summary}
                </pre>
              </div>
            </div>

            {/* Price Info */}
            <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-6">
              <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5" /> {t('priceInfo')}
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(quickResult.price_info).map(([key, value]) => (
                  <div key={key} className="bg-[var(--bg-card)] p-4 rounded-lg">
                    <div className="text-xs text-[var(--text-secondary)] uppercase">{key}</div>
                    <div className="text-lg font-mono font-bold">{String(value)}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* News Highlights */}
            {quickResult.news_highlights.length > 0 && (
              <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-6">
                <h2 className="text-lg font-bold mb-4">{t('newsHighlights')}</h2>
                <ul className="space-y-2">
                  {quickResult.news_highlights.map((news, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-blue-400">•</span>
                      <span className="text-sm">{news}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Execution Time */}
            <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
              <Clock className="w-4 h-4" />
              {t('executionTime', { ms: quickResult.execution_time_ms })}
            </div>
          </div>
        )}

        {/* Chart Analysis Result */}
        {chartResult && (
          <div className="space-y-6">
            {/* Trend Badge */}
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border ${getSentimentColor(chartResult.trend_assessment)}`}>
              {getSentimentIcon(chartResult.trend_assessment)}
              <span className="font-bold uppercase">{chartResult.trend_assessment}</span>
            </div>

            {/* Technical Summary */}
            <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-6">
              <h2 className="text-lg font-bold mb-4">{t('techSummary')}</h2>
              <div className="prose prose-invert max-w-none">
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                  {chartResult.technical_summary}
                </pre>
              </div>
            </div>

            {/* Technical Indicators */}
            <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-6">
              <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5" /> {t('techIndicators')}
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(chartResult.indicators).map(([key, value]) => (
                  <div key={key} className="bg-[var(--bg-card)] p-4 rounded-lg">
                    <div className="text-xs text-[var(--text-secondary)] uppercase">{key}</div>
                    <div className="text-lg font-mono font-bold">{String(value)}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Support/Resistance */}
            <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-6">
              <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Target className="w-5 h-5" /> {t('supportResistance')}
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(chartResult.support_resistance).map(([key, value]) => (
                  <div key={key} className="bg-[var(--bg-card)] p-4 rounded-lg">
                    <div className="text-xs text-[var(--text-secondary)] uppercase">{key}</div>
                    <div className="text-lg font-mono font-bold">
                      {typeof value === 'number' ? `$${value.toFixed(2)}` : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Execution Time */}
            <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
              <Clock className="w-4 h-4" />
              {t('executionTime', { ms: chartResult.execution_time_ms })}
            </div>
          </div>
        )}

        {/* Run Button (if not auto-run) */}
        {!autoRun && !isLoading && !quickResult && !chartResult && (
          <div className="flex flex-col items-center justify-center py-20">
            <button
              onClick={runAnalysis}
              className="px-6 py-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-500 transition-colors flex items-center gap-2"
            >
              {mode === 'quick' ? <Zap className="w-5 h-5" /> : <Activity className="w-5 h-5" />}
              {t('startAnalysis')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function AnalysisResultPage() {
  return (
    <AppLayout>
      <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="w-8 h-8 animate-spin" /></div>}>
        <AnalysisResultContent />
      </Suspense>
    </AppLayout>
  );
}

export default withAuth(AnalysisResultPage);
