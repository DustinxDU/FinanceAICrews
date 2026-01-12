"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { AppLayout } from "@/components/layout";
import { withAuth } from "@/contexts/AuthContext";
import { useTranslations } from "next-intl";
import apiClient from "@/lib/api";
import {
  TrendingUp, TrendingDown, Plus, X, Zap, Maximize2, Pin, Search,
  BarChart3, Cpu, Layers, Activity, Check, Loader2, Sparkles,
  BookOpen, FileText, StickyNote, Radar, ChevronRight, SendHorizontal,
  Bell, Bot, User, Save, ExternalLink
} from "lucide-react";
import { CommandPalette } from "@/components/layout/CommandPalette";

// --- Types ---

interface MacroIndicator {
  id: string;
  name: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
  critical: boolean;
}

interface AssetBadge {
  label: string;
  color: 'red' | 'yellow' | 'green' | 'blue' | 'zinc';
}

interface Asset {
  id: string;
  type: 'US Stocks' | 'Crypto' | 'A/H Shares' | 'Macro';
  name: string;
  price: string;
  priceLocal?: string;
  currencyLocal?: string;
  change: string;
  badges?: AssetBadge[];
  sparkline?: number[];
  thesis?: string;
  isMacro?: boolean;
  actual?: string;
  forecast?: string;
}

interface NewsItem {
  id: string | number;
  tickers: string[];
  title: string;
  summary: string;
  time: string;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  source: string;
  url?: string;
}

interface ArticleContent {
  success: boolean;
  title?: string;
  text?: string;
  top_image?: string;
  authors?: string[];
  url: string;
  error?: string;
  is_blacklisted?: boolean;
}

interface LogItem {
  id: number;
  agent: string;
  status: string;
  message: string;
  timestamp: string;
  detail?: string;
}

// --- Mock Data ---

const MACRO_INDICATORS: MacroIndicator[] = [
  { id: 'us10y', name: 'US 10Y', value: '4.02%', change: '+1.2%', trend: 'up', critical: false },
  { id: 'dxy', name: 'DXY', value: '102.4', change: '-0.1%', trend: 'down', critical: false },
  { id: 'gold', name: 'Gold', value: '$2,045', change: '+0.5%', trend: 'up', critical: false },
  { id: 'vix', name: 'VIX', value: '18.5', change: '+12.4%', trend: 'up', critical: true },
  { id: 'btc', name: 'BTC', value: '$64,200', change: '+2.1%', trend: 'up', critical: false },
];

const ASSETS: Asset[] = [
  {
    id: 'NVDA',
    type: 'US Stocks',
    name: 'Nvidia Corp.',
    price: '$875.20',
    change: '+2.4%',
    badges: [{ label: '🔥 Breakout', color: 'red' }, { label: 'AI Trend', color: 'blue' }],
    sparkline: [20, 25, 22, 30, 28, 35, 40, 38, 42, 45],
    thesis: "Watching strictly for data center revenue growth deceleration. Key level $850."
  },
  {
    id: 'AAPL',
    type: 'US Stocks',
    name: 'Apple Inc.',
    price: '$178.30',
    change: '-0.5%',
    badges: [{ label: '⚖️ Range', color: 'zinc' }],
    sparkline: [50, 48, 49, 48, 47, 48, 46, 47, 46, 45],
    thesis: "Neutral until Vision Pro numbers are confirmed. Buy zone $165."
  },
  {
    id: 'BTC-USD',
    type: 'Crypto',
    name: 'Bitcoin',
    price: '$64,200',
    change: '+2.1%',
    badges: [{ label: '🚀 Momentum', color: 'green' }],
    sparkline: [60, 62, 61, 63, 65, 64, 66, 68, 67, 69],
    thesis: "Halving event priced in? Monitor ETF inflows."
  },
  {
    id: 'ETH-USD',
    type: 'Crypto',
    name: 'Ethereum',
    price: '$3,450',
    change: '+1.8%',
    badges: [],
    sparkline: [30, 31, 31, 32, 33, 33, 34, 34, 35, 35]
  },
  {
    id: '0700.HK',
    type: 'A/H Shares',
    name: 'Tencent',
    price: 'HK$310.0',
    change: '+0.8%',
    badges: [{ label: '⚡ Earnings', color: 'yellow' }],
    sparkline: [20, 21, 20, 22, 23, 22, 24, 25, 24, 25]
  },
  {
    id: 'UNEMP',
    type: 'Macro',
    name: 'US Unemployment',
    price: '3.9%',
    change: '0.0%',
    isMacro: true,
    actual: '3.9%',
    forecast: '3.9%',
    badges: [{ label: '📅 Released', color: 'blue' }]
  }
];

const NEWS_FEED: NewsItem[] = [
  {
    id: 1,
    tickers: ['NVDA', 'AMD'],
    title: "US Considers New Export Restrictions on AI Chips to Middle East",
    summary: "Regulatory uncertainty may create short-term volatility for chipmakers, though long-term demand remains robust.",
    time: "15 min ago",
    sentiment: "bearish",
    source: "Bloomberg"
  },
  {
    id: 2,
    tickers: ['BTC-USD', 'ETH-USD'],
    title: "SEC Delays Decision on Ethereum ETF Applications",
    summary: "Market anticipated the delay; impact likely priced in, but dampens immediate speculative fervor.",
    time: "42 min ago",
    sentiment: "neutral",
    source: "Coindesk"
  },
  {
    id: 3,
    tickers: ['AAPL'],
    title: "Apple Vision Pro Initial Sales Exceed Expectations",
    summary: "Early adoption numbers suggest strong ecosystem stickiness, potentially offsetting iPhone China weakness.",
    time: "1 hour ago",
    sentiment: "bullish",
    source: "Reuters"
  },
  {
    id: 4,
    tickers: ['UNEMP', 'us10y'],
    title: "Jobless Claims Come in Lower Than Expected",
    summary: "Labor market resilience reinforces 'Higher for Longer' narrative, pushing yields slightly higher.",
    time: "2 hours ago",
    sentiment: "bearish",
    source: "CNBC"
  },
  {
    id: 5,
    tickers: ['0700.HK'],
    title: "China Approves 105 New Domestic Games",
    summary: "Strong regulatory support signal for the gaming sector, alleviating policy risk concerns.",
    time: "3 hours ago",
    sentiment: "bullish",
    source: "Caixin"
  }
];

// --- Utilities ---

const formatTime = () => {
  const now = new Date();
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
};

// ==================== Sparkline client cache ====================

const SPARKLINE_PERIOD_DEFAULT = "5d";
const sparklineCache = new Map<string, number[]>();
const sparklineInFlight = new Map<string, Promise<number[]>>();

const sparklineKey = (ticker: string, period: string = SPARKLINE_PERIOD_DEFAULT) =>
  `${ticker.toUpperCase()}:${period}`;

const useLongPress = (onLongPress: () => void, ms: number = 800) => {
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const isLongPress = useRef(false);

  const start = useCallback(() => {
    isLongPress.current = false;
    timerRef.current = setTimeout(() => {
      isLongPress.current = true;
      onLongPress();
    }, ms);
  }, [onLongPress, ms]);

  const stop = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  return {
    onMouseDown: start,
    onMouseUp: stop,
    onMouseLeave: stop,
    onTouchStart: start,
    onTouchEnd: stop,
  };
};

// --- Components ---

const Sparkline = ({ 
  data, 
  color = '#10b981',
  showReferenceLine = true,
  showDataPoints = true
}: { 
  data?: number[]; 
  color?: string;
  showReferenceLine?: boolean;
  showDataPoints?: boolean;
}) => {
  if (!data || data.length === 0) return null;
  
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const width = 100;
  const height = 30;
  
  // Calculate points with smooth curves
  const points = data.map((val, i) => {
    const x = (i / (Math.max(data.length - 1, 1))) * width;
    const y = height - ((val - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');
  
  // Calculate reference line (middle point)
  const midValue = min + range / 2;
  const midY = height - ((midValue - min) / range) * height;
  
  // Calculate start and end values for labels
  const startValue = data[0];
  const endValue = data[data.length - 1];
  const changePercent = ((endValue - startValue) / startValue * 100).toFixed(1);
  const isPositive = endValue >= startValue;

  return (
    <div className="relative w-full h-full">
      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="overflow-visible">
        {/* Reference line */}
        {showReferenceLine && (
          <line 
            x1="0" y1={midY} 
            x2={width} y2={midY} 
            stroke={color} 
            strokeWidth="0.5" 
            strokeDasharray="2,2" 
            opacity="0.3" 
          />
        )}
        
        {/* Main sparkline */}
        <polyline 
          points={points} 
          fill="none" 
          stroke={color} 
          strokeWidth="2" 
          strokeLinecap="round" 
          strokeLinejoin="round"
          className="transition-all duration-300"
        />
        
        {/* Start point */}
        {showDataPoints && (
          <circle 
            cx={0} 
            cy={height - ((data[0] - min) / range) * height} 
            r="2" 
            fill={color}
            className="transition-all duration-300"
          />
        )}
        
        {/* End point with larger indicator */}
        {showDataPoints && (
          <circle 
            cx={width} 
            cy={height - ((data[data.length - 1] - min) / range) * height} 
            r="3" 
            fill={color}
            className="transition-all duration-300"
          />
        )}
      </svg>
      
      {/* Data labels */}
      <div className="absolute -top-3 left-0 text-[8px] text-[var(--text-secondary)] font-mono opacity-60">
        {startValue.toFixed(0)}
      </div>
      <div className={`absolute -top-3 right-0 text-[8px] font-mono font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
        {endValue.toFixed(0)} ({isPositive ? '+' : ''}{changePercent}%)
      </div>
    </div>
  );
};

const DetailChart = ({ color = '#10b981', ticker }: { color?: string; ticker?: string }) => {
  const t = useTranslations('cockpit');
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<any>(null);
  const [chartData, setChartData] = useState<number[]>([]);
  const [chartLabels, setChartLabels] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [chartInfo, setChartInfo] = useState<{high: number; low: number; change: number; lastClosePrice?: number; lastCloseDate?: string} | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState('1m');
  const seenKeysRef = useRef<Set<string>>(new Set());
  const forceRefreshRef = useRef(false);
  const [refreshNonce, setRefreshNonce] = useState(0);

  // Fetch real chart data
  useEffect(() => {
    if (ticker) {
      setIsLoading(true);
      const key = `${ticker}:${selectedPeriod}`;
      const shouldForceRefresh = forceRefreshRef.current;
      forceRefreshRef.current = false;

      apiClient.getSparklineData(ticker, selectedPeriod, shouldForceRefresh)
        .then(res => {
          if (res.data && res.data.length > 0) {
            setChartData(res.data);
            setChartInfo({
              high: res.high || Math.max(...res.data),
              low: res.low || Math.min(...res.data),
              change: res.change_percent || 0,
              lastClosePrice: res.current_price,
              lastCloseDate: res.last_close_date
            });
            const labels = res.timestamps?.length > 0
              ? res.timestamps.map((t: string) => {
                  const date = new Date(t);
                  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                })
              : res.data.map((_: number, i: number) => `Day ${i + 1}`);
            setChartLabels(labels);
            seenKeysRef.current.add(key);
          }
        })
        .catch(err => console.error('Failed to fetch chart data:', err))
        .finally(() => setIsLoading(false));
    }
  }, [ticker, selectedPeriod, refreshNonce]);

  useEffect(() => {
    let cancelled = false;
    const canvas = canvasRef.current;

    if (canvas && chartData.length > 0) {
      const ctx = canvas.getContext('2d');

      if (ctx) {
        const isPositive = chartInfo && chartInfo.change >= 0;
        const lineColor = isPositive ? '#10b981' : '#ef4444';
        const gradient = ctx.createLinearGradient(0, 0, 0, 180);
        gradient.addColorStop(0, isPositive ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)');
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

        (async () => {
          try {
            const mod: any = await import('chart.js/auto');
            const ChartCtor = mod?.default ?? mod?.Chart ?? mod;
            if (!ChartCtor || cancelled) return;

            if (chartRef.current) {
              chartRef.current.destroy();
              chartRef.current = null;
            }

            const existing = typeof ChartCtor.getChart === 'function' ? ChartCtor.getChart(canvas) : null;
            if (existing) existing.destroy();

            if (cancelled) return;

            chartRef.current = new ChartCtor(ctx, {
              type: 'line',
              data: {
                labels: chartLabels,
                datasets: [{
                  label: 'Price',
                  data: chartData,
                  borderColor: lineColor,
                  backgroundColor: gradient,
                  borderWidth: 2,
                  fill: true,
                  tension: 0.1,
                  pointRadius: 0,
                  pointHoverRadius: 5,
                  pointHoverBackgroundColor: lineColor,
                  pointHoverBorderColor: '#fff',
                  pointHoverBorderWidth: 2
                }]
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                  legend: { display: false },
                  tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: lineColor,
                    borderWidth: 1,
                    padding: 10,
                    displayColors: false,
                    callbacks: {
                      label: (context: any) => `$${(context?.parsed?.y ?? 0).toFixed(2)}`
                    }
                  }
                },
                scales: {
                  x: { 
                    display: true,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { 
                      color: 'rgba(255,255,255,0.4)', 
                      font: { size: 10 },
                      maxTicksLimit: 6
                    }
                  },
                  y: { 
                    display: true,
                    position: 'right',
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { 
                      color: 'rgba(255,255,255,0.4)', 
                      font: { size: 10 },
                      callback: (value: any) => `$${Number(value).toFixed(0)}`
                    }
                  }
                },
                interaction: {
                  mode: 'index',
                  intersect: false,
                }
              }
            });
          } catch (e) {
            console.error('Failed to load Chart.js:', e);
          }
        })();
      }
    }
    return () => {
      cancelled = true;
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [chartData, chartLabels, chartInfo]);

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--text-secondary)]" />
      </div>
    );
  }

  if (chartData.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center text-[var(--text-secondary)]">
        {t('noChartDataAvailable')}
      </div>
    );
  }

  const periods = [
    { label: '1D', value: '1d' },
    { label: '5D', value: '5d' },
    { label: '1M', value: '1m' },
    { label: '3M', value: '3m' },
    { label: '1Y', value: '1y' },
  ];

  return (
    <div className="w-full h-full relative flex flex-col">
      {/* Chart Header with Stats */}
      <div className="flex justify-between items-center mb-2">
        <div className="flex items-center gap-4">
          {chartInfo && (
            <>
              {/* 方案 A：明确标注这是历史收盘价 */}
              {chartInfo.lastClosePrice && chartInfo.lastCloseDate && (
                <div className="text-xs">
                  <span className="text-[var(--text-secondary)]">Close ({chartInfo.lastCloseDate}): </span>
                  <span className="text-white font-mono font-medium">${chartInfo.lastClosePrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              <div className="text-xs">
                <span className="text-[var(--text-secondary)]">H: </span>
                <span className="text-green-400 font-mono">${chartInfo.high.toFixed(2)}</span>
              </div>
              <div className="text-xs">
                <span className="text-[var(--text-secondary)]">L: </span>
                <span className="text-red-400 font-mono">${chartInfo.low.toFixed(2)}</span>
              </div>
              <div className={`text-xs font-mono ${chartInfo.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {chartInfo.change >= 0 ? '+' : ''}{chartInfo.change.toFixed(2)}%
              </div>
            </>
          )}
        </div>
        {/* Period Selector */}
        <div className="flex gap-1 items-center">
          <button
            onClick={() => {
              forceRefreshRef.current = true;
              setRefreshNonce(n => n + 1);
            }}
            className="px-2 py-1 text-[10px] rounded bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-white"
            title="Force refresh"
          >
            Refresh
          </button>
          {periods.map(p => (
            <button
              key={p.value}
              onClick={() => setSelectedPeriod(p.value)}
              className={`px-2 py-1 text-[10px] rounded transition-all ${
                selectedPeriod === p.value 
                  ? 'bg-[var(--accent-blue)] text-white' 
                  : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-white'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
      {/* Chart Canvas */}
      <div className="flex-1 min-h-0">
        <canvas ref={canvasRef}></canvas>
      </div>
    </div>
  );
};

const MacroBar = ({ 
  items, 
  onAdd, 
  isEditMode, 
  onDelete,
  onEnterEditMode,
  errorMessage
}: { 
  items: MacroIndicator[]; 
  onAdd: () => void; 
  isEditMode: boolean;
  onDelete: (id: string) => void;
  onEnterEditMode: () => void;
  errorMessage?: string | null;
}) => {
  // Hooks must not be called inside loops; compute once and reuse
  const longPressProps = useLongPress(onEnterEditMode);

  return (
    <div className="h-24 bg-[var(--bg-app)] border-b border-[var(--border-color)] overflow-x-auto flex items-center px-6 gap-4 no-scrollbar">
      <div className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-widest shrink-0 mr-2 opacity-50">
        Global<br/>Context
      </div>
      {errorMessage && items.length === 0 && (
        <div className="min-w-[240px] h-16 rounded-lg border border-yellow-500/30 bg-yellow-900/10 flex items-center px-4 text-xs text-yellow-200 shrink-0">
          {errorMessage}
        </div>
      )}
      {items.map(item => {
        return (
          <div 
            key={item.id} 
            {...longPressProps}
            className={`min-w-[140px] h-16 rounded-lg border flex flex-col justify-center px-4 relative overflow-hidden transition-all shrink-0 select-none
              ${item.critical 
                  ? 'bg-red-900/10 border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.2)] animate-pulse' 
                  : 'bg-[var(--bg-card)] border-[var(--border-color)] hover:border-[var(--text-secondary)]'
              }
              ${isEditMode ? 'animate-shake cursor-default' : ''}
            `}
          >
            {isEditMode && (
              <button 
                onClick={(e) => { e.stopPropagation(); onDelete(item.id); }}
                className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center z-20 hover:bg-red-600 shadow-md"
              >
                <X className="text-white text-[10px]" />
              </button>
            )}
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-[var(--text-secondary)] font-bold">{item.name}</span>
              {item.trend === 'up' ? <TrendingUp className={`text-xs ${item.change.startsWith('+') ? 'text-green-400' : 'text-red-400'}`} /> : <TrendingDown className={`text-xs ${item.change.startsWith('+') ? 'text-green-400' : 'text-red-400'}`} />}
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-bold font-mono">{item.value}</span>
              <span className={`text-[10px] ${item.change.startsWith('+') ? 'text-green-400' : 'text-red-400'}`}>{item.change}</span>
            </div>
          </div>
        );
      })}
      <button 
        onClick={onAdd}
        className="h-16 w-12 rounded-lg border-2 border-dashed border-[var(--border-color)] flex items-center justify-center hover:bg-[var(--bg-card)] hover:border-[var(--text-secondary)] transition-all group shrink-0"
        title="Add Macro Indicator"
      >
        <Plus className="text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]" />
      </button>
    </div>
  );
};

const FilterTabs = ({ current, onChange }: { current: string; onChange: (filter: string) => void }) => {
  const tabs = ['All', 'US Stocks', 'Crypto', 'A/H Shares', 'Macro'];
  return (
    <div className="px-8 py-6 flex flex-wrap gap-2">
      {tabs.map(tab => (
        <button
          key={tab}
          onClick={() => onChange(tab)}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 border
            ${current === tab 
                ? 'bg-[var(--text-primary)] text-[var(--bg-app)] border-[var(--text-primary)] shadow-lg' 
                : 'bg-[var(--bg-card)] text-[var(--text-secondary)] border-[var(--border-color)] hover:border-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
        >
          {tab}
        </button>
      ))}
    </div>
  );
};

const AssetCard = ({ 
  asset, 
  isSelected, 
  onClick, 
  onDetail, 
  isEditMode, 
  onDelete,
  onEnterEditMode
}: {
  asset: Asset;
  isSelected: boolean;
  onClick: () => void;
  onDetail: () => void;
  isEditMode: boolean;
  onDelete: (id: string) => void;
  onEnterEditMode: () => void;
}) => {
  const t = useTranslations('cockpit');
  const isPositive = asset.change.startsWith('+') || asset.change === '0.0%';
  const longPressProps = useLongPress(onEnterEditMode);
  const cardRef = useRef<HTMLDivElement | null>(null);
  const [sparklineData, setSparklineData] = useState<number[]>([]);
  const [isLoadingSparkline, setIsLoadingSparkline] = useState(false);
  // 历史收盘价信息（用于双价格显示）
  const [closeInfo, setCloseInfo] = useState<{price: number; date: string} | null>(null);

  // Fetch sparkline lazily (only when card is visible) + dedupe via client cache
  useEffect(() => {
    if (asset.isMacro) return;

    const key = sparklineKey(asset.id, SPARKLINE_PERIOD_DEFAULT);
    const cached = sparklineCache.get(key);
    if (cached && cached.length > 0) {
      setSparklineData(cached);
      return;
    }

    let cancelled = false;

    const load = async () => {
      try {
        setIsLoadingSparkline(true);

        const inFlight = sparklineInFlight.get(key);
        if (inFlight) {
          const data = await inFlight;
          if (!cancelled && data?.length) setSparklineData(data);
          return;
        }

        const promise = apiClient.getSparklineData(asset.id, SPARKLINE_PERIOD_DEFAULT, false)
          .then(res => {
            const data = res?.data || [];
            if (data.length > 0) sparklineCache.set(key, data);
            // 保存历史收盘价信息
            if (res?.current_price && res?.last_close_date) {
              setCloseInfo({ price: res.current_price, date: res.last_close_date });
            }
            return data;
          })
          .catch(() => [])
          .finally(() => sparklineInFlight.delete(key));

        sparklineInFlight.set(key, promise);
        const data = await promise;
        if (!cancelled && data?.length) setSparklineData(data);
      } finally {
        if (!cancelled) setIsLoadingSparkline(false);
      }
    };

    const el = cardRef.current;
    if (!el || typeof IntersectionObserver === 'undefined') {
      load();
      return () => {
        cancelled = true;
      };
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting) {
          observer.disconnect();
          load();
        }
      },
      { root: null, threshold: 0.15 }
    );

    observer.observe(el);

    return () => {
      cancelled = true;
      observer.disconnect();
    };
  }, [asset.id, asset.isMacro]);

  const getBadgeColor = (color: AssetBadge['color']) => {
    switch (color) {
      case 'red': return 'bg-red-900/20 text-red-400 border-red-900/50';
      case 'yellow': return 'bg-yellow-900/20 text-yellow-400 border-yellow-900/50';
      case 'green': return 'bg-green-900/20 text-green-400 border-green-900/50';
      case 'blue': return 'bg-blue-900/20 text-blue-400 border-blue-900/50';
      default: return 'bg-zinc-800 text-zinc-400 border-zinc-700';
    }
  };

  return (
    <div 
      data-asset-card
      ref={cardRef}
      onClick={!isEditMode ? onClick : undefined}
      {...longPressProps}
      className={`group relative bg-[var(--bg-panel)] border rounded-xl p-5 transition-all h-56 flex flex-col justify-between cursor-pointer select-none
        ${isSelected && !isEditMode ? 'border-[var(--accent-blue)] shadow-[0_0_15px_rgba(59,130,246,0.3)] ring-1 ring-[var(--accent-blue)]' : 'border-[var(--border-color)] hover:border-[var(--text-secondary)]'}
        ${isEditMode ? 'animate-shake' : 'hover:shadow-xl hover:-translate-y-1'}
      `}
    >
      {isEditMode && (
        <button 
          onClick={(e) => { e.stopPropagation(); onDelete(asset.id); }}
          className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center z-30 hover:bg-red-600 shadow-md border-2 border-[var(--bg-app)]"
        >
          <X className="text-white text-xs" />
        </button>
      )}

      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg bg-[var(--bg-card)] flex items-center justify-center border border-[var(--border-color)] text-xs font-bold ${isSelected ? 'text-[var(--accent-blue)] border-[var(--accent-blue)]' : 'text-[var(--text-secondary)]'}`}>
            {asset.id.substring(0, 2)}
          </div>
          <div>
            <div className="font-bold text-base leading-none mb-1">{asset.id}</div>
            <div className="text-xs text-[var(--text-secondary)] truncate w-24">{asset.name}</div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          {asset.badges && asset.badges.map((b, i) => (
            <span key={i} className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border ${getBadgeColor(b.color)}`}>
              {b.label}
            </span>
          ))}
        </div>
      </div>

      {/* Body */}
      <div>
        {asset.isMacro ? (
          <div className="flex justify-between items-end mb-2">
            <div>
              <div className="text-xs text-[var(--text-secondary)]">Actual</div>
              <div className="text-2xl font-bold font-mono">{asset.actual}</div>
            </div>
            <div className="text-right">
              <div className="text-xs text-[var(--text-secondary)]">Forecast</div>
              <div className="text-lg font-mono text-[var(--text-secondary)]">{asset.forecast}</div>
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-2xl font-bold font-mono tracking-tight">{asset.price}</span>
              <span className={`text-sm font-medium ${isPositive ? 'text-green-400' : 'text-red-400'}`}>{asset.change}</span>
            </div>
            {/* 双价格显示：历史收盘价（方案 C） */}
            {closeInfo && (
              <div className="text-xs text-[var(--text-secondary)] mb-1 flex items-center gap-1">
                <span>Close ({closeInfo.date}):</span>
                <span className="font-mono">${closeInfo.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
            )}
            {/* 双币种显示：非美股资产显示本地货币价格 */}
            {asset.priceLocal && asset.currencyLocal && (
              <div className="text-xs text-[var(--text-secondary)] mb-1">
                {asset.currencyLocal} {asset.priceLocal}
              </div>
            )}
            <div className="h-8 w-full opacity-60 group-hover:opacity-100 transition-opacity">
              {isLoadingSparkline ? (
                <div className="flex items-center justify-center h-full">
                  <div className="w-4 h-4 border-2 border-[var(--text-secondary)] border-t-transparent rounded-full animate-spin" />
                </div>
              ) : sparklineData.length > 0 ? (
                <Sparkline data={sparklineData} color={isPositive ? '#10b981' : '#ef4444'} />
              ) : (
                <div className="flex items-center justify-center h-full text-[10px] text-[var(--text-secondary)]">
                  {t('noChartData')}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Action Footer */}
      {!isEditMode && (
        <div className={`absolute inset-x-0 bottom-0 p-4 bg-[var(--bg-panel)]/95 backdrop-blur border-t border-[var(--border-color)] rounded-b-xl translate-y-2 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-200 flex items-center gap-2 z-10 ${isSelected ? 'opacity-100 translate-y-0' : ''}`}>
          <button 
            onClick={(e) => { e.stopPropagation(); onDetail(); }}
            className="flex-1 bg-[var(--accent-blue)] hover:bg-blue-600 text-white text-xs font-bold py-2 rounded-lg flex items-center justify-center gap-2 shadow-lg shadow-blue-900/20 transition-colors"
          >
            <Maximize2 className="text-xs" />
            Deep Context
          </button>
          <button 
            onClick={(e) => { e.stopPropagation(); }}
            className="p-2 hover:bg-[var(--bg-card)] rounded-lg text-[var(--text-secondary)] hover:text-white transition-colors" 
            title="Pin"
          >
            <Pin className="text-xs" />
          </button>
        </div>
      )}
    </div>
  );
};

const AddAssetCard = ({ onClick }: { onClick: () => void }) => {
  const t = useTranslations('cockpit');
  return (
    <div
      onClick={onClick}
      className="h-56 bg-[var(--bg-app)] border-2 border-dashed border-[var(--border-color)] rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-[var(--text-secondary)] hover:bg-[var(--bg-card)] transition-all group"
    >
      <div className="w-12 h-12 rounded-full bg-[var(--bg-card)] group-hover:bg-[var(--bg-panel)] border border-[var(--border-color)] flex items-center justify-center mb-3 transition-colors">
        <Plus className="text-xl text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]" />
      </div>
      <span className="text-sm font-medium text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]">{t('addAsset')}</span>
    </div>
  );
};

// --- Omni-Search Modal ---
const OmniSearchModal = ({ onClose, onAddAsset, existingTickers }: { onClose: () => void; onAddAsset: (ticker: string, assetType: string) => Promise<void>; existingTickers: Set<string>; }) => {
  const t = useTranslations('cockpit');
  const [query, setQuery] = useState('');
  const [activeTab, setActiveTab] = useState('All');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (inputRef.current) inputRef.current.focus();
  }, []);

  const tabs = ['All', 'US Stocks', 'Crypto', 'A/H Shares', 'Macro'];

  // Debounced search function
  useEffect(() => {
    const timeoutId = setTimeout(async () => {
      if (query.trim().length >= 2) {
        await performSearch(query);
      } else {
        setSearchResults([]);
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [query, activeTab]);

  const performSearch = async (searchQuery: string) => {
    try {
      setIsSearching(true);
      setSearchError(null);
      
      const assetTypes = activeTab === 'All' ? undefined : [activeTab];
      const results = await apiClient.searchAssets({
        query: searchQuery,
        asset_types: assetTypes,
        limit: 20
      });
      
      setSearchResults(results);
    } catch (error) {
      console.error('Search error:', error);
      setSearchError(t('searchFailed'));
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleAddAsset = async (result: any) => {
    try {
      await onAddAsset(result.ticker, result.asset_type);
      onClose();
    } catch (error) {
      console.error('Add asset error:', error);
      setSearchError(t('addAssetFailed'));
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-start justify-center pt-[15vh] animate-in fade-in duration-200" onClick={onClose}>
      <div className="bg-[var(--bg-panel)] w-full max-w-2xl border border-[var(--border-color)] rounded-xl shadow-2xl overflow-hidden animate-in zoom-in-95" onClick={e => e.stopPropagation()}>
        {/* Search Header */}
        <div className="p-4 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-3 mb-3">
            <Search className="text-[var(--text-secondary)] text-xl" />
            <input 
              ref={inputRef}
              type="text" 
              value={query} 
              onChange={e => setQuery(e.target.value)}
              placeholder="Search ticker (AAPL), name (Apple), or concept (Inflation)..."
              className="bg-transparent border-none outline-none text-xl w-full text-[var(--text-primary)] placeholder-[var(--text-secondary)]"
            />
            <div className="px-2 py-1 bg-[var(--bg-card)] rounded text-xs text-[var(--text-secondary)]">ESC</div>
          </div>
          <div className="flex gap-4">
            {tabs.map(tab => (
              <button 
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`text-xs font-bold uppercase transition-colors ${activeTab === tab ? 'text-[var(--accent-blue)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Content Area */}
        <div className="min-h-[300px] max-h-[500px] overflow-y-auto">
          {!query ? (
            <div className="p-4">
              <div className="mb-6">
                <h4 className="text-xs font-bold text-[var(--text-secondary)] uppercase mb-3">{t('trendingAnalysis')}</h4>
                <div className="grid grid-cols-2 gap-2">
                  {(() => {
                    const items = [
                      { ticker: 'NVDA', asset_type: 'US', badge: 'NV', badgeClass: 'bg-red-900/20 text-red-400', name: 'Nvidia Corp' },
                      { ticker: 'BTC-USD', asset_type: 'CRYPTO', badge: 'BT', badgeClass: 'bg-orange-900/20 text-orange-400', name: 'Bitcoin' },
                    ];
                    return items.map(item => {
                      const already = existingTickers.has(item.ticker.toUpperCase());
                      return (
                        <button
                          key={item.ticker}
                          onClick={() => !already && handleAddAsset({ ticker: item.ticker, asset_type: item.asset_type })}
                          disabled={already}
                          className={`p-3 bg-[var(--bg-card)] rounded-lg flex items-center justify-between group w-full text-left border border-transparent transition-colors ${
                            already ? 'opacity-60 cursor-not-allowed border-[var(--border-color)]' : 'hover:bg-zinc-800 cursor-pointer'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded flex items-center justify-center font-bold text-xs ${item.badgeClass}`}>{item.badge}</div>
                            <div>
                              <div className="font-bold text-sm">{item.ticker}</div>
                              <div className="text-xs text-[var(--text-secondary)]">{item.name}</div>
                            </div>
                          </div>
                          {already ? (
                            <span className="text-[10px] text-[var(--text-secondary)]">{t('added')}</span>
                          ) : (
                            <Plus className="text-[var(--text-secondary)] group-hover:text-white" />
                          )}
                        </button>
                      );
                    });
                  })()}
                </div>
              </div>
              <div>
                <h4 className="text-xs font-bold text-[var(--text-secondary)] uppercase mb-3">Major Indices</h4>
                <div className="space-y-1">
                  {[
                    { label: 'S&P 500 (SPX)', ticker: 'SPX', asset_type: 'MACRO' },
                    { label: 'Nasdaq 100 (NDX)', ticker: 'NDX', asset_type: 'MACRO' },
                    { label: 'US 10Y Yield (US10Y)', ticker: 'US10Y', asset_type: 'MACRO' },
                  ].map(idx => (
                    <button
                      key={idx.ticker}
                      onClick={() => !existingTickers.has(idx.ticker.toUpperCase()) && handleAddAsset({ ticker: idx.ticker, asset_type: idx.asset_type })}
                      disabled={existingTickers.has(idx.ticker.toUpperCase())}
                      className={`w-full flex items-center justify-between p-2 rounded-lg group text-left transition-colors ${
                        existingTickers.has(idx.ticker.toUpperCase())
                          ? 'opacity-60 cursor-not-allowed border border-[var(--border-color)]'
                          : 'hover:bg-[var(--bg-card)] cursor-pointer'
                      }`}
                    >
                      <span className="text-sm font-medium text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]">{idx.label}</span>
                      {existingTickers.has(idx.ticker.toUpperCase()) ? (
                        <span className="text-[10px] text-[var(--text-secondary)]">{t('added')}</span>
                      ) : (
                        <Plus className="text-xs text-[var(--text-secondary)] opacity-0 group-hover:opacity-100" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-2">
              {isSearching && (
                <div className="flex items-center justify-center p-4">
                  <Loader2 className="animate-spin mr-2" />
                  <span className="text-[var(--text-secondary)]">{t('loading')}</span>
                </div>
              )}
              {searchError && (
                <div className="p-4 text-center text-red-400">
                  {searchError}
                </div>
              )}
              {searchResults && searchResults.map((res: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-3 hover:bg-[var(--bg-card)] rounded-lg cursor-pointer group animate-in slide-in-from-left-2" style={{animationDelay: `${i*50}ms`}}>
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded flex items-center justify-center text-sm font-bold bg-zinc-800 text-zinc-300">
                      {res.ticker.substring(0, 2)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm">{res.ticker}</span>
                        <span className="text-[10px] bg-[var(--bg-app)] border border-[var(--border-color)] px-1.5 rounded text-[var(--text-secondary)]">{res.asset_type}</span>
                        {res.exchange && <span className="text-[10px] text-[var(--text-secondary)]">{res.exchange}</span>}
                      </div>
                      <div className="text-xs text-[var(--text-secondary)]">{res.name}</div>
                    </div>
                  </div>
                  <button 
                    onClick={() => handleAddAsset(res)}
                    className="w-8 h-8 rounded-full border border-[var(--border-color)] flex items-center justify-center hover:bg-[var(--accent-green)] hover:text-black hover:border-[var(--accent-green)] transition-all"
                  >
                    <Plus className="text-xs" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// --- Asset Detail Slide-over (AI War Room) ---
const AssetDetailPanel = ({ asset, onClose, onLaunchAnalysis }: {
  asset: Asset;
  onClose: () => void;
  onLaunchAnalysis: (ticker: string, type: string) => void;
}) => {
  const t = useTranslations('cockpit');
  const [thesis, setThesis] = useState(asset.thesis || '');
  const [isSavingThesis, setIsSavingThesis] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedThesis, setSavedThesis] = useState(asset.thesis || '');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  
  // Track unsaved changes
  useEffect(() => {
    setHasUnsavedChanges(thesis !== savedThesis);
  }, [thesis, savedThesis]);
  
  const handleSaveThesis = async () => {
    if (thesis === savedThesis) return; // No change
    
    setIsSavingThesis(true);
    setSaveError(null);
    try {
      await apiClient.updateUserAsset(asset.id, { notes: thesis });
      setSavedThesis(thesis); // Update saved state
      setHasUnsavedChanges(false);
    } catch (error) {
      console.error('Failed to save thesis:', error);
      setSaveError(t('saveFailed'));
    } finally {
      setIsSavingThesis(false);
    }
  };

  const handleLaunchAnalysis = (type: string) => {
    onLaunchAnalysis(asset.id, type);
  };

  return (
    <div className="fixed inset-y-0 right-0 w-full md:w-[600px] bg-[var(--bg-panel)] border-l border-[var(--border-color)] shadow-2xl z-40 flex flex-col transform transition-transform duration-300 animate-in slide-in-from-right">
      {/* Header */}
      <div className="h-16 border-b border-[var(--border-color)] flex items-center justify-between px-6 bg-[var(--bg-card)]">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-[var(--bg-panel)] flex items-center justify-center border border-[var(--border-color)] text-sm font-bold">
            {asset.id.substring(0, 2)}
          </div>
          <div>
            <h2 className="font-bold text-lg leading-none">{asset.id}</h2>
            <div className="text-xs text-[var(--text-secondary)]">{asset.name}</div>
          </div>
          <div className={`px-2 py-1 rounded text-sm font-mono font-bold ${asset.change.startsWith('+') ? 'bg-green-900/20 text-green-400' : 'bg-red-900/20 text-red-400'}`}>
            {asset.change}
          </div>
        </div>
        <button onClick={onClose} className="p-2 hover:bg-[var(--bg-panel)] rounded-lg text-[var(--text-secondary)] hover:text-white">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {/* Visual Context (Chart) */}
        <div className="h-64 bg-[var(--bg-app)] border-b border-[var(--border-color)] relative p-4">
          <DetailChart color={asset.change.startsWith('+') ? '#10b981' : '#ef4444'} ticker={asset.id} />
        </div>

        {/* My Thesis (Memory Injection) */}
        <div className="p-6 border-b border-[var(--border-color)]">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-bold uppercase text-[var(--text-secondary)] flex items-center gap-2">
              <StickyNote className="w-4 h-4" /> My Thesis (Memory)
            </h3>
            <div className="flex items-center gap-2">
              {saveError && <span className="text-xs text-red-400">{saveError}</span>}
              {!hasUnsavedChanges && !isSavingThesis && !saveError && savedThesis && (
                <span className="text-xs text-green-400 flex items-center gap-1"><Check className="w-3 h-3" /> {t('saved')}</span>
              )}
              {hasUnsavedChanges && (
                <button
                  onClick={handleSaveThesis}
                  disabled={isSavingThesis}
                  className={`px-3 py-1 text-xs rounded-lg flex items-center gap-1 transition-all ${
                    isSavingThesis 
                      ? 'bg-blue-900/30 text-blue-400 cursor-not-allowed' 
                      : 'bg-blue-600 text-white hover:bg-blue-500'
                  }`}
                >
                  {isSavingThesis ? (
                    <><Loader2 className="w-3 h-3 animate-spin" /> {t('saving')}</>
                  ) : (
                    <><Save className="w-3 h-3" /> {t('save')}</>
                  )}
                </button>
              )}
            </div>
          </div>
          <div className="relative">
            <textarea 
              value={thesis}
              onChange={(e) => setThesis(e.target.value)}
              placeholder="Write your investment thesis here. AI agents will read this as long-term memory context..."
              className={`w-full h-24 bg-[var(--bg-card)] border rounded-xl p-3 text-sm focus:border-[var(--accent-blue)] outline-none resize-none placeholder:text-zinc-600 ${
                hasUnsavedChanges ? 'border-yellow-500/50' : 'border-[var(--border-color)]'
              }`}
            />
            <div className="absolute bottom-3 right-3 text-[10px] text-[var(--text-secondary)] opacity-50">
              {hasUnsavedChanges ? t('unsavedChanges') : t('syncedWithAI')}
            </div>
          </div>
        </div>

        {/* AI Action Deck */}
        <div className="p-6">
          <h3 className="text-sm font-bold uppercase text-[var(--text-secondary)] mb-4 flex items-center gap-2">
            <Cpu className="w-4 h-4" /> Intelligence Deck
          </h3>
          
          {/* Smart Research Links */}
          <div className="mb-6">
            <div className="text-xs font-bold text-[var(--text-secondary)] mb-2">Research Links</div>
            <div className="flex gap-2 overflow-x-auto pb-2 no-scrollbar">
              <a 
                href={`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${asset.id}&type=10-K&dateb=&owner=include&count=40`}
                target="_blank"
                rel="noopener noreferrer"
                className="min-w-[160px] p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] hover:border-blue-500 cursor-pointer transition-colors group"
              >
                <div className="flex items-center gap-2 mb-1 text-blue-400">
                  <FileText className="w-3 h-3" />
                  <span className="text-xs font-bold">SEC Filings</span>
                  <ExternalLink className="w-2.5 h-2.5 ml-auto opacity-0 group-hover:opacity-100" />
                </div>
                <p className="text-[10px] text-[var(--text-secondary)] line-clamp-2 group-hover:text-[var(--text-primary)]">
                  10-K, 10-Q, 8-K filings
                </p>
              </a>
              <a 
                href={`https://finance.yahoo.com/quote/${asset.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="min-w-[160px] p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] hover:border-purple-500 cursor-pointer transition-colors group"
              >
                <div className="flex items-center gap-2 mb-1 text-purple-400">
                  <BarChart3 className="w-3 h-3" />
                  <span className="text-xs font-bold">Yahoo Finance</span>
                  <ExternalLink className="w-2.5 h-2.5 ml-auto opacity-0 group-hover:opacity-100" />
                </div>
                <p className="text-[10px] text-[var(--text-secondary)] line-clamp-2 group-hover:text-[var(--text-primary)]">
                  Financials, News, Analysis
                </p>
              </a>
              <a 
                href={`https://seekingalpha.com/symbol/${asset.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="min-w-[160px] p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] hover:border-green-500 cursor-pointer transition-colors group"
              >
                <div className="flex items-center gap-2 mb-1 text-green-400">
                  <BookOpen className="w-3 h-3" />
                  <span className="text-xs font-bold">Seeking Alpha</span>
                  <ExternalLink className="w-2.5 h-2.5 ml-auto opacity-0 group-hover:opacity-100" />
                </div>
                <p className="text-[10px] text-[var(--text-secondary)] line-clamp-2 group-hover:text-[var(--text-primary)]">
                  Expert analysis & ratings
                </p>
              </a>
              <a 
                href={`https://www.google.com/search?q=${asset.id}+stock+news&tbm=nws`}
                target="_blank"
                rel="noopener noreferrer"
                className="min-w-[160px] p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] hover:border-yellow-500 cursor-pointer transition-colors group"
              >
                <div className="flex items-center gap-2 mb-1 text-yellow-400">
                  <Search className="w-3 h-3" />
                  <span className="text-xs font-bold">News Search</span>
                  <ExternalLink className="w-2.5 h-2.5 ml-auto opacity-0 group-hover:opacity-100" />
                </div>
                <p className="text-[10px] text-[var(--text-secondary)] line-clamp-2 group-hover:text-[var(--text-primary)]">
                  Latest news & headlines
                </p>
              </a>
            </div>
          </div>

          {/* Launchpad Cards */}
          <div className="space-y-3">
            <div className="text-xs font-bold text-[var(--text-secondary)] mb-2">{t('tacticalAnalysis')}</div>
            
            <div onClick={() => handleLaunchAnalysis('quick')} className="flex items-center gap-4 p-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] hover:bg-[var(--bg-panel)] hover:border-[var(--accent-green)] cursor-pointer transition-all group">
              <div className="w-10 h-10 rounded-full bg-green-900/20 text-green-400 flex items-center justify-center border border-green-900/50 group-hover:scale-110 transition-transform">
                <Zap className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <div className="font-bold text-sm">{t('quickScan')}</div>
                <div className="text-xs text-[var(--text-secondary)]">News summary & sentiment check. 30s.</div>
              </div>
              <ChevronRight className="text-[var(--text-secondary)]" />
            </div>

            <div onClick={() => handleLaunchAnalysis('deep')} className="flex items-center gap-4 p-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] hover:bg-[var(--bg-panel)] hover:border-[var(--accent-blue)] cursor-pointer transition-all group">
              <div className="w-10 h-10 rounded-full bg-blue-900/20 text-blue-400 flex items-center justify-center border border-blue-900/50 group-hover:scale-110 transition-transform">
                <Layers className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <div className="font-bold text-sm">{t('deepDiveReport')}</div>
                <div className="text-xs text-[var(--text-secondary)]">Fundamental analysis + Thesis check. 3m.</div>
              </div>
              <ChevronRight className="text-[var(--text-secondary)]" />
            </div>

            <div onClick={() => handleLaunchAnalysis('chart')} className="flex items-center gap-4 p-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] hover:bg-[var(--bg-panel)] hover:border-yellow-500 cursor-pointer transition-all group">
              <div className="w-10 h-10 rounded-full bg-yellow-900/20 text-yellow-400 flex items-center justify-center border border-yellow-900/50 group-hover:scale-110 transition-transform">
                <Activity className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <div className="font-bold text-sm">{t('technicalDiagnostic')}</div>
                <div className="text-xs text-[var(--text-secondary)]">Key levels & Volume profile. 1m.</div>
              </div>
              <ChevronRight className="text-[var(--text-secondary)]" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// --- Zone D Components ---

const NewsItemCard = ({ 
  news, 
  onAnalyze,
  onReadArticle 
}: { 
  news: NewsItem; 
  onAnalyze: (tickers: string[], title: string) => void;
  onReadArticle: (news: NewsItem) => void;
}) => {
  const handleImpactAnalysis = () => {
    onAnalyze(news.tickers, news.title);
  };

  return (
    <div className="group flex flex-col md:flex-row gap-4 p-4 hover:bg-[var(--bg-card)] rounded-xl transition-colors border-b border-[var(--border-color)] last:border-0 relative">
      {/* Sentiment Bar */}
      <div className={`absolute left-0 top-4 bottom-4 w-1 rounded-r-full ${
        news.sentiment === 'bullish' ? 'bg-green-500' : 
        news.sentiment === 'bearish' ? 'bg-red-500' : 'bg-zinc-600'
      }`}></div>
      
      <div className="pl-3 flex-1">
        <div className="flex items-center gap-2 mb-2">
          {news.tickers.map(t => (
            <span key={t} className="text-[10px] font-bold bg-[var(--bg-panel)] border border-[var(--border-color)] px-1.5 py-0.5 rounded text-[var(--text-secondary)] group-hover:text-[var(--text-primary)] transition-colors">
              {t}
            </span>
          ))}
          <span className="text-[10px] text-[var(--text-secondary)] ml-auto md:ml-2">{news.time}</span>
        </div>
        
        <h3 
          onClick={() => onReadArticle(news)}
          className="font-bold text-base mb-1 cursor-pointer hover:text-[var(--accent-blue)] transition-colors"
        >
          {news.title}
        </h3>
        
        <div className="flex items-start gap-2">
          <div className="mt-1 shrink-0 w-4 h-4 rounded-full bg-[var(--accent-blue)]/10 flex items-center justify-center">
            <Sparkles className="w-[10px] h-[10px] text-[var(--accent-blue)]" />
          </div>
          <p className="text-sm text-[var(--text-secondary)] leading-snug">{news.summary}</p>
        </div>
      </div>

      <div className="pl-3 md:pl-0 flex items-center">
        <button 
          onClick={handleImpactAnalysis}
          className="w-full md:w-auto px-4 py-2 bg-[var(--bg-panel)] border border-[var(--border-color)] hover:border-[var(--accent-blue)] hover:text-[var(--accent-blue)] rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 group/btn"
        >
          <Zap className="w-3 h-3 group-hover/btn:text-[var(--accent-blue)] transition-colors" />
          Analyze Impact
        </button>
      </div>
    </div>
  );
};

// --- Article Reader Drawer ---
const ArticleReaderDrawer = ({ 
  isOpen, 
  onClose, 
  article, 
  isLoading, 
  originalUrl 
}: {
  isOpen: boolean;
  onClose: () => void;
  article: ArticleContent | null;
  isLoading: boolean;
  originalUrl: string;
}) => {
  const t = useTranslations('cockpit');
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop - increased z-index to ensure it's on top */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[1000] animate-in fade-in duration-200"
        onClick={onClose}
      />
      
      {/* Drawer - increased z-index and added transform-gpu for better performance */}
      <div className="fixed right-0 top-0 h-full w-full max-w-2xl bg-[var(--bg-panel)] border-l border-[var(--border-color)] z-[1001] shadow-2xl animate-in slide-in-from-right duration-300 flex flex-col transform-gpu">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[var(--border-color)] bg-[var(--bg-card)]">
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="p-2 hover:bg-[var(--bg-panel)] rounded-lg text-[var(--text-secondary)] hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
            <span className="text-sm font-medium text-[var(--text-secondary)]">Article Reader</span>
          </div>
          <a
            href={originalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-3 py-1.5 text-xs text-[var(--text-secondary)] hover:text-[var(--accent-blue)] border border-[var(--border-color)] hover:border-[var(--accent-blue)] rounded-lg transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            {t('openOriginal')}
          </a>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
              <p className="text-sm text-[var(--text-secondary)]">Extracting article content...</p>
            </div>
          ) : article?.success ? (
            <div className="p-6">
              {/* Cover Image */}
              {article.top_image && (
                <div className="mb-6 rounded-xl overflow-hidden">
                  <img 
                    src={article.top_image} 
                    alt={article.title || 'Article cover'} 
                    className="w-full h-48 object-cover"
                    onError={(e) => (e.currentTarget.style.display = 'none')}
                  />
                </div>
              )}
              
              {/* Title */}
              <h1 className="text-2xl font-bold mb-4 leading-tight">{article.title}</h1>
              
              {/* Authors */}
              {article.authors && article.authors.length > 0 && (
                <div className="flex items-center gap-2 mb-6 text-sm text-[var(--text-secondary)]">
                  <span>By {article.authors.join(', ')}</span>
                </div>
              )}
              
              {/* Article Text */}
              <div className="prose prose-invert prose-sm max-w-none">
                {article.text?.split('\n\n').map((paragraph, idx) => (
                  paragraph.trim() && (
                    <p key={idx} className="mb-4 text-[var(--text-primary)] leading-relaxed">
                      {paragraph}
                    </p>
                  )
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-4 p-6">
              <div className="w-16 h-16 rounded-full bg-yellow-500/10 flex items-center justify-center">
                <ExternalLink className="w-8 h-8 text-yellow-400" />
              </div>
              <p className="text-center text-[var(--text-secondary)]">
                {article?.error || 'Unable to extract article content'}
              </p>
              <a
                href={originalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-[var(--accent-blue)] text-white rounded-lg text-sm font-medium hover:bg-[var(--accent-blue)]/80 transition-colors"
              >
                Read on Original Site
              </a>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

const IntelligentBriefing = ({
  selectedAssetId,
  onAnalyze
}: {
  selectedAssetId: string | null;
  onAnalyze: (tickers: string[], title: string) => void;
}) => {
  const t = useTranslations('cockpit');
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Article reader drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [selectedArticle, setSelectedArticle] = useState<ArticleContent | null>(null);
  const [isArticleLoading, setIsArticleLoading] = useState(false);
  const [currentArticleUrl, setCurrentArticleUrl] = useState('');
  
  // Debug: Log state changes
  useEffect(() => {
    console.log('[Article Drawer] isDrawerOpen changed to:', isDrawerOpen);
  }, [isDrawerOpen]);

  const handleReadArticle = async (newsItem: NewsItem) => {
    const url = newsItem.url;
    if (!url) {
      // No URL available, can't extract
      console.log('[Article Extraction] No URL available for news item:', newsItem);
      return;
    }
    
    console.log('[Article Extraction] Opening article drawer for URL:', url);
    setCurrentArticleUrl(url);
    setIsDrawerOpen(true);
    setIsArticleLoading(true);
    setSelectedArticle(null);
    
    try {
      const response = await fetch(`/api/v1/news/extract?url=${encodeURIComponent(url)}`);
      const data: ArticleContent = await response.json();
      
      console.log('[Article Extraction] API response:', data);
      
      // If blacklisted, open in new tab instead
      if (data.is_blacklisted) {
        console.log('[Article Extraction] URL is blacklisted, opening in new tab');
        window.open(url, '_blank');
        setIsDrawerOpen(false);
        return;
      }
      
      setSelectedArticle(data);
    } catch (err) {
      console.error('Failed to extract article:', err);
      setSelectedArticle({
        success: false,
        url,
        error: t('extractContentFailed'),
      });
    } finally {
      setIsArticleLoading(false);
    }
  };

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const params = new URLSearchParams();
        if (selectedAssetId) {
          params.append('tickers', selectedAssetId);
        }
        params.append('limit', '10');
        
        const response = await fetch(`/api/v1/news/headlines?${params.toString()}`, {
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error(`API Error: ${response.status}`);
        }

        const data = await response.json();
        
        const mappedNews: NewsItem[] = (data.news || data.articles || []).map((item: any, index: number) => {
          let timeStr = '';
          try {
            const publishedAt = item.published_at ? new Date(item.published_at) : new Date();
            const now = new Date();
            const diffMs = now.getTime() - publishedAt.getTime();
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMins / 60);
            const diffDays = Math.floor(diffHours / 24);
            
            if (diffMins < 1) {
              timeStr = 'Just now';
            } else if (diffMins < 60) {
              timeStr = `${diffMins} min ago`;
            } else if (diffHours < 24) {
              timeStr = `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
            } else if (diffDays < 7) {
              timeStr = `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
            } else {
              timeStr = publishedAt.toLocaleDateString();
            }
          } catch {
            timeStr = new Date().toISOString();
          }
          
          return {
            id: item.id || `news-${index}`,
            tickers: item.tickers || item.related_tickers || (selectedAssetId ? [selectedAssetId] : []),
            title: item.title,
            summary: item.summary || item.description || '',
            time: timeStr,
            sentiment: (item.sentiment === 'bullish' || item.sentiment === 'bearish' || item.sentiment === 'neutral') ? item.sentiment : 'neutral',
            source: (typeof item.source === 'string' ? item.source : item.source?.name) || 'Unknown',
            url: item.url || '',
          };
        });
        
        setNews(mappedNews);
      } catch (err) {
        console.error('Failed to fetch news:', err);
        setError(err instanceof Error ? err.message : t('loadNewsFailed'));
        setNews([]);
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, [selectedAssetId]);

  if (loading) {
    return (
      <div className="px-8 pb-20 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
        <div className="flex items-center gap-3 mb-6">
          <div className="h-6 w-1 bg-[var(--accent-blue)] rounded-full"></div>
          <h2 className="text-xl font-bold">Intelligent Briefing</h2>
        </div>
        <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-8">
          <div className="flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
            <p className="text-sm text-[var(--text-secondary)]">{t('loadingNews')}</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-8 pb-20 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
        <div className="flex items-center gap-3 mb-6">
          <div className="h-6 w-1 bg-[var(--accent-blue)] rounded-full"></div>
          <h2 className="text-xl font-bold">Intelligent Briefing</h2>
        </div>
        <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-8">
          <div className="flex flex-col items-center justify-center gap-3">
            <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center">
              <Activity className="w-5 h-5 text-red-400" />
            </div>
            <p className="text-sm text-red-400">{error}</p>
            <button 
              onClick={() => window.location.reload()}
              className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] underline"
            >
              {t('clickRetry')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="px-8 pb-20 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
      <div className="flex items-center gap-3 mb-6">
        <div className="h-6 w-1 bg-[var(--accent-blue)] rounded-full"></div>
        <h2 className="text-xl font-bold">Intelligent Briefing</h2>
        {selectedAssetId && (
          <span className="text-xs bg-[var(--accent-blue)]/10 text-[var(--accent-blue)] px-2 py-1 rounded-lg border border-[var(--accent-blue)]/20 flex items-center gap-1">
            {t('filteredBy')} <span className="font-bold">{selectedAssetId}</span>
            <X className="w-3 h-3 cursor-pointer hover:text-white" onClick={() => document.dispatchEvent(new CustomEvent('clear-filter'))} />
          </span>
        )}
      </div>

      <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl divide-y divide-[var(--border-color)]">
        {news.length > 0 ? (
          news.map(item => (
            <NewsItemCard 
              key={item.id} 
              news={item} 
              onAnalyze={onAnalyze} 
              onReadArticle={handleReadArticle}
            />
          ))
        ) : (
          <div className="p-8 text-center text-[var(--text-secondary)]">
            <div className="w-10 h-10 mx-auto mb-2 opacity-50 flex items-center justify-center">
              <Activity className="w-10 h-10" />
            </div>
            <p>No high-impact intelligence found for this asset recently.</p>
          </div>
        )}
      </div>
      
      {/* Article Reader Drawer */}
      <ArticleReaderDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        article={selectedArticle}
        isLoading={isArticleLoading}
        originalUrl={currentArticleUrl}
      />
    </div>
  );
};

// --- Global Context Customizer Modal ---
const GlobalContextCustomizer = ({ onClose, onRefresh }: { onClose: () => void; onRefresh: () => void }) => {
  const t = useTranslations('cockpit');
  const [availableIndicators, setAvailableIndicators] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAvailableIndicators = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const indicators = await apiClient.getAvailableCockpitIndicators();
        setAvailableIndicators(indicators);
      } catch (error) {
        console.error('Failed to fetch available indicators:', error);
        setError(t('loadIndicatorsFailed'));
      } finally {
        setIsLoading(false);
      }
    };

    fetchAvailableIndicators();
  }, []);

  const handleToggleIndicator = async (indicatorId: string, isSelected: boolean) => {
    try {
      if (isSelected) {
        await apiClient.removeUserCockpitIndicator(indicatorId);
      } else {
        await apiClient.addUserCockpitIndicator({ indicator_id: indicatorId });
      }
      
      // Update local state
      setAvailableIndicators(prev => 
        prev.map(ind => 
          ind.indicator_id === indicatorId 
            ? { ...ind, is_selected: !isSelected }
            : ind
        )
      );
    } catch (error) {
      console.error('Failed to toggle indicator:', error);
      setError(t('operationFailed'));
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-[var(--bg-panel)] w-full max-w-4xl max-h-[80vh] border border-[var(--border-color)] rounded-xl shadow-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="p-6 border-b border-[var(--border-color)] bg-[var(--bg-card)]">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">{t('customIndicators')}</h2>
              <p className="text-sm text-[var(--text-secondary)] mt-1">{t('customIndicatorsDesc')}</p>
            </div>
            <button 
              onClick={onClose}
              className="p-2 hover:bg-[var(--bg-panel)] rounded-lg text-[var(--text-secondary)] hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-140px)]">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin mr-3" />
              <span className="text-[var(--text-secondary)]">{t('loadingIndicators')}</span>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <div className="text-red-400 mb-4">{error}</div>
              <button 
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-[var(--accent-blue)] text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                {t('reload')}
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Selected Indicators */}
              {availableIndicators.filter(ind => ind.is_selected).length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-4 text-[var(--accent-green)]">
                    {t('selectedIndicators', { count: availableIndicators.filter(ind => ind.is_selected).length })}
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {availableIndicators
                      .filter(ind => ind.is_selected)
                      .map(indicator => (
                        <IndicatorCard 
                          key={indicator.indicator_id}
                          indicator={indicator}
                          isSelected={true}
                          onToggle={handleToggleIndicator}
                        />
                      ))}
                  </div>
                </div>
              )}

              {/* Available Indicators by Type */}
              {['index', 'commodity', 'crypto', 'macro'].map(type => {
                const typeIndicators = availableIndicators.filter(
                  ind => ind.indicator_type === type && !ind.is_selected
                );
                
                if (typeIndicators.length === 0) return null;

                const typeNames: Record<string, string> = {
                  index: t('indexCategory'),
                  commodity: t('commodityCategory'),
                  crypto: t('cryptoCategory'),
                  macro: t('macroCategory')
                };

                return (
                  <div key={type}>
                    <h3 className="text-lg font-semibold mb-4">
                      {typeNames[type]} ({typeIndicators.length})
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {typeIndicators.map(indicator => (
                        <IndicatorCard 
                          key={indicator.indicator_id}
                          indicator={indicator}
                          isSelected={false}
                          onToggle={handleToggleIndicator}
                        />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-[var(--border-color)] bg-[var(--bg-card)] flex items-center justify-between">
          <div className="text-sm text-[var(--text-secondary)]">
            {t('selectedCount', { count: availableIndicators.filter(ind => ind.is_selected).length })}
          </div>
          <div className="flex gap-3">
            <button 
              onClick={onClose}
              className="px-6 py-2 border border-[var(--border-color)] rounded-lg hover:bg-[var(--bg-panel)] transition-colors"
            >
              {t('close')}
            </button>
            <button 
              onClick={() => {
                onRefresh();
                onClose();
              }}
              className="px-6 py-2 bg-[var(--accent-blue)] text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              {t('done')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Indicator Card Component
const IndicatorCard = ({
  indicator,
  isSelected,
  onToggle
}: {
  indicator: any;
  isSelected: boolean;
  onToggle: (indicatorId: string, isSelected: boolean) => void;
}) => {
  const t = useTranslations('cockpit');
  const getIndicatorColor = (type: string) => {
    switch (type) {
      case 'index': return 'blue';
      case 'commodity': return 'yellow';
      case 'crypto': return 'purple';
      case 'macro': return 'green';
      default: return 'gray';
    }
  };

  const color = getIndicatorColor(indicator.indicator_type);

  return (
    <div className={`relative p-4 border rounded-xl transition-all cursor-pointer hover:scale-105 ${
      isSelected 
        ? 'border-blue-500/50 bg-blue-900/20 ring-2 ring-blue-500/30 shadow-lg' 
        : 'border-[var(--border-color)] bg-[var(--bg-card)] hover:border-[var(--text-secondary)]'
    }`}>
      {/* Selection Indicator */}
      <div className={`absolute top-3 right-3 w-5 h-5 rounded-full border-2 flex items-center justify-center ${
        isSelected 
          ? 'bg-blue-500 border-blue-500' 
          : 'border-[var(--border-color)] bg-[var(--bg-card)]'
      }`}>
        {isSelected && <Check className="w-3 h-3 text-white" />}
      </div>

      <div onClick={() => onToggle(indicator.indicator_id, isSelected)}>
        {/* Header */}
        <div className="flex items-start gap-3 mb-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${
            isSelected 
              ? 'border-blue-500/50 bg-blue-900/20' 
              : 'border-[var(--border-color)] bg-[var(--bg-panel)]'
          }`}>
            <span className={`font-bold text-xs ${isSelected ? 'text-blue-400' : 'text-[var(--text-secondary)]'}`}>
              {indicator.symbol.substring(0, 2)}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-bold text-sm leading-tight">{indicator.indicator_name}</div>
            <div className="text-xs text-[var(--text-secondary)] truncate">{indicator.symbol}</div>
          </div>
        </div>

        {/* Current Value */}
        {indicator.current_value && (
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-lg font-bold font-mono">{indicator.current_value}</span>
            {indicator.change_percent !== null && (
              <span className={`text-xs ${
                indicator.change_percent >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {indicator.change_percent >= 0 ? '+' : ''}{indicator.change_percent?.toFixed(2)}%
              </span>
            )}
          </div>
        )}

        {/* Critical Badge */}
        {indicator.is_critical && (
          <div className="inline-flex items-center gap-1 px-2 py-1 bg-red-900/20 border border-red-500/30 rounded text-red-400 text-[10px] font-bold">
            <Bell className="w-3 h-3" />
            {t('importantMetrics')}
          </div>
        )}

        {/* Last Updated */}
        {indicator.last_updated && (
          <div className="text-[10px] text-[var(--text-secondary)] mt-2">
            {t('lastUpdated', { time: new Date(indicator.last_updated).toLocaleString() })}
          </div>
        )}
      </div>
    </div>
  );
};

// --- Main Component ---

function CockpitContent() {
  const [activeFilter, setActiveFilter] = useState('All');
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [detailAssetId, setDetailAssetId] = useState<string | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isLoadingMacros, setIsLoadingMacros] = useState(true);
  const [macroError, setMacroError] = useState<string | null>(null);
  
  const [assets, setAssets] = useState<Asset[]>([]);
  const [macros, setMacros] = useState<MacroIndicator[]>([]);
  const [isEditMode, setIsEditMode] = useState(false);
  const [isLoadingAssets, setIsLoadingAssets] = useState(true);
  const [isGlobalContextCustomizerOpen, setIsGlobalContextCustomizerOpen] = useState(false);

  const t = useTranslations('cockpit');

  // Helper to map backend asset types to frontend display types
  const mapBackendAssetType = useCallback((backendType: string): 'US Stocks' | 'Crypto' | 'A/H Shares' | 'Macro' => {
    switch (backendType) {
      case 'US': return 'US Stocks';
      case 'CRYPTO': return 'Crypto';
      case 'HK': return 'A/H Shares';
      case 'MACRO': return 'Macro';
      default: return 'US Stocks';
    }
  }, []);

  // Fetch cockpit dashboard (single request for macro + assets)
  const fetchDashboard = useCallback(async (forceRefresh: boolean = false) => {
    try {
      setIsLoadingMacros(true);
      setIsLoadingAssets(true);
      setMacroError(null);

      const dashboard = await apiClient.getCockpitDashboard(forceRefresh);

      const convertedMacros: MacroIndicator[] = (dashboard.markets || []).map((m) => ({
        id: m.id,
        name: m.name,
        value: m.value,
        change: m.change,
        trend: m.trend,
        critical: m.critical,
      }));

      setMacros(convertedMacros);
      if (convertedMacros.length === 0) {
        setMacroError('No macro indicators returned from dashboard API');
      }

      const convertedAssets: Asset[] = (dashboard.assets || []).map((a) => {
        const assetType = a.asset_type || 'US';
        const priceValue = typeof a.price === 'number' ? a.price : null;
        const price = priceValue !== null ? `$${priceValue.toFixed(2)}` : '$--';
        const changePercent = typeof a.change_percent === 'number' ? a.change_percent : null;
        const change = changePercent !== null ? `${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%` : '0.0%';

        let priceLocal: string | undefined;
        let currencyLocal: string | undefined;
        if (typeof a.price_local === 'number' && a.currency_local) {
          currencyLocal = a.currency_local;
          priceLocal = a.price_local.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }

        return {
          id: a.ticker,
          type: mapBackendAssetType(assetType),
          name: a.name || a.ticker,
          price,
          priceLocal,
          currencyLocal,
          change,
          badges: [],
          thesis: a.notes || undefined,
          isMacro: assetType === 'MACRO',
          actual: assetType === 'MACRO' ? (priceValue !== null ? `$${priceValue.toFixed(2)}` : undefined) : undefined,
          forecast: typeof a.target_price === 'number' ? `$${a.target_price}` : undefined,
        };
      });

      setAssets(convertedAssets);
    } catch (error) {
      console.error('Error fetching cockpit dashboard:', error);
      setMacros([]);
      setAssets([]);
      setMacroError(error instanceof Error ? error.message : 'Failed to fetch cockpit dashboard');
    } finally {
      setIsLoadingMacros(false);
      setIsLoadingAssets(false);
    }
  }, [mapBackendAssetType]);

  useEffect(() => {
    fetchDashboard(true);
    const interval = setInterval(() => fetchDashboard(false), 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchDashboard]);

  // WebSocket for real-time price updates (no 30s polling)
  useEffect(() => {
    const tickers = assets.filter(a => !a.isMacro).map(a => a.id).filter(Boolean);
    if (tickers.length === 0) return;

    const baseWsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    const wsUrl = baseWsUrl.replace(/^http:\/\//, 'ws://').replace(/^https:\/\//, 'wss://');

    const param = encodeURIComponent(tickers.join(','));
    const wsEndpoint = `${wsUrl}/api/v1/realtime/ws/price?tickers=${param}`;

    let socket: WebSocket | null = null;
    let pingTimer: NodeJS.Timeout | null = null;
    let reconnectTimer: NodeJS.Timeout | null = null;
    let reconnectAttempts = 0;
    let shouldReconnect = true;

    const cleanupSocket = () => {
      if (pingTimer) clearInterval(pingTimer);
      pingTimer = null;
      if (socket && socket.readyState === WebSocket.OPEN) {
        try {
          socket.close();
        } catch {
          // ignore
        }
      }
      socket = null;
    };

    const scheduleReconnect = () => {
      if (!shouldReconnect) return;
      if (reconnectTimer) return;

      const maxAttempts = 10;
      if (reconnectAttempts >= maxAttempts) return;

      const baseDelayMs = 1000; // 1s
      const maxDelayMs = 30000; // 30s
      const delay = Math.min(maxDelayMs, baseDelayMs * Math.pow(2, reconnectAttempts));
      const jitter = Math.floor(Math.random() * 250);
      reconnectAttempts += 1;

      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connect();
      }, delay + jitter);
    };

    const connect = () => {
      cleanupSocket();

      try {
        socket = new WebSocket(wsEndpoint);
      } catch {
        scheduleReconnect();
        return;
      }

      socket.onopen = () => {
        reconnectAttempts = 0;
        pingTimer = setInterval(() => {
          try {
            socket?.send('ping');
          } catch {
            // ignore
          }
        }, 25000);
      };

      socket.onmessage = (event) => {
        if (event.data === 'pong') return;
        try {
          const msg = JSON.parse(event.data);
          if (msg?.type !== 'price_update' || !msg?.ticker) return;

          const ticker = String(msg.ticker).toUpperCase();
          const data = msg.data || {};
          const priceValue = typeof data.price === 'number' ? data.price : null;
          const changePercent = typeof data.change_percent === 'number' ? data.change_percent : null;

          setAssets((prev) => prev.map((a) => {
            if (a.id.toUpperCase() !== ticker) return a;

            const nextPrice = priceValue !== null ? `$${priceValue.toFixed(2)}` : a.price;
            const nextChange = changePercent !== null
              ? `${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%`
              : a.change;

            return {
              ...a,
              price: nextPrice,
              change: nextChange,
              actual: a.isMacro ? nextPrice : a.actual,
            };
          }));
        } catch {
          // ignore
        }
      };

      socket.onclose = () => {
        cleanupSocket();
        scheduleReconnect();
      };

      socket.onerror = () => {
        // Let onclose handle cleanup + reconnect
      };
    };

    connect();

    return () => {
      shouldReconnect = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      reconnectTimer = null;
      cleanupSocket();
    };
  }, [assets.map(a => a.id).join('|')]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (isEditMode) {
        // Don't exit edit mode if clicking on delete button or asset card
        const target = e.target as HTMLElement;
        const isDeleteButton = target.closest('button')?.classList.contains('bg-red-500') || 
                               target.closest('button')?.classList.contains('bg-red-600');
        const isAssetCard = target.closest('[data-asset-card]');
        
        if (!isDeleteButton && !isAssetCard) {
          setIsEditMode(false);
        }
      }
    };
    
    if (isEditMode) {
      // Use setTimeout to avoid immediate trigger from the long press that entered edit mode
      const timer = setTimeout(() => {
        window.addEventListener('click', handleClickOutside);
      }, 100);
      return () => {
        clearTimeout(timer);
        window.removeEventListener('click', handleClickOutside);
      };
    }
    return () => window.removeEventListener('click', handleClickOutside);
  }, [isEditMode]);
  
  useEffect(() => {
    const handleClear = () => setSelectedAssetId(null);
    document.addEventListener('clear-filter', handleClear);
    return () => document.removeEventListener('clear-filter', handleClear);
  }, []);
  
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsEditMode(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const filteredAssets = activeFilter === 'All' 
    ? assets 
    : assets.filter(a => a.type === activeFilter);

  const handleAssetClick = (id: string) => {
    if (selectedAssetId === id) {
      setSelectedAssetId(null);
    } else {
      setSelectedAssetId(id);
    }
  };

  const handleOpenDetail = (id: string) => {
    setDetailAssetId(id);
  };

  const handleDeleteAsset = async (id: string) => {
    try {
      await apiClient.removeUserAsset(id);
      if (selectedAssetId === id) setSelectedAssetId(null);
      if (detailAssetId === id) setDetailAssetId(null);
      await fetchDashboard(false);
    } catch (error) {
      console.error('Failed to delete asset:', error);
    }
  };

  const handleAddAsset = async (ticker: string, assetType: string) => {
    try {
      await apiClient.addUserAsset({
        ticker: ticker.toUpperCase(),
        asset_type: assetType,
      });

      await fetchDashboard(false);
    } catch (error) {
      console.error('Failed to add asset:', error);
      throw error;
    }
  };

  const handleDeleteMacro = async (id: string) => {
    try {
      await apiClient.removeUserCockpitIndicator(id);
      setMacros(prev => prev.filter(m => m.id !== id));
    } catch (error) {
      console.error('Failed to delete macro indicator:', error);
    }
  };

  const handleAddMacro = async () => {
    setIsGlobalContextCustomizerOpen(true);
  };

  const handleLaunchAnalysis = async (ticker: string, type: string) => {
    // Get the asset's thesis for context
    const asset = assets.find(a => a.id === ticker);
    const thesis = asset?.thesis;
    
    if (type === 'deep') {
      // Deep Dive: 跳转到Workbench选择Crew运行
      const today = new Date().toISOString().split('T')[0];
      window.location.href = `/dashboard?ticker=${ticker}&date=${today}&mode=deep&select_crew=true`;
    } else {
      // Quick Scan / Chart Analysis: 跳转到结果页面
      const queryParams = new URLSearchParams({
        ticker,
        mode: type,
        auto_run: 'true',
        ...(thesis ? { thesis } : {})
      });
      window.location.href = `/analysis/result?${queryParams.toString()}`;
    }
  };

  const handleAnalyzeNews = (tickers: string[], title: string) => {
    const query = `Analyze the impact of this news on ${tickers.join(', ')}: ${title}`;
    window.location.href = `/dashboard?auto_run=true&query=${encodeURIComponent(query)}`;
  };

  const selectedAsset = detailAssetId ? assets.find(a => a.id === detailAssetId) : null;

  return (
    <div className="min-h-screen bg-[var(--bg-app)]">
      {/* Zone A: Global Context (Macro Bar) */}
      <MacroBar 
        items={macros}
        onAdd={handleAddMacro}
        isEditMode={isEditMode}
        onDelete={handleDeleteMacro}
        onEnterEditMode={() => setIsEditMode(true)}
        errorMessage={macroError}
      />

      {/* Zone B: Filter */}
      <FilterTabs current={activeFilter} onChange={setActiveFilter} />

      {/* Zone C: Bento Grid */}
      <div className="px-8 pb-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 animate-in slide-in-from-bottom-4 duration-500">
        {filteredAssets.map(asset => (
          <AssetCard 
            key={asset.id} 
            asset={asset} 
            isSelected={selectedAssetId === asset.id}
            onClick={() => handleAssetClick(asset.id)}
            onDetail={() => handleOpenDetail(asset.id)}
            isEditMode={isEditMode}
            onDelete={handleDeleteAsset}
            onEnterEditMode={() => setIsEditMode(true)}
          />
        ))}
        {!isEditMode && <AddAssetCard onClick={() => setIsSearchOpen(true)} />}
      </div>

      {/* Zone D: Intelligent Briefing */}
      <IntelligentBriefing 
        selectedAssetId={selectedAssetId} 
        onAnalyze={handleAnalyzeNews}
      />

      {/* Overlays */}
      {isSearchOpen && (
        <OmniSearchModal 
          onClose={() => setIsSearchOpen(false)} 
          onAddAsset={handleAddAsset}
          existingTickers={new Set(assets.map(a => a.id.toUpperCase()))}
        />
      )}
      
      {isGlobalContextCustomizerOpen && (
        <GlobalContextCustomizer 
          onClose={() => setIsGlobalContextCustomizerOpen(false)}
          onRefresh={async () => {
            try {
              await fetchDashboard(false);
            } catch (error) {
              console.error('Failed to refresh macro data:', error);
            }
          }}
        />
      )}
      
      {selectedAsset && (
        <>
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-30" onClick={() => setDetailAssetId(null)} />
          <AssetDetailPanel 
            asset={selectedAsset} 
            onClose={() => setDetailAssetId(null)}
            onLaunchAnalysis={handleLaunchAnalysis}
          />
        </>
      )}
      
      {/* Edit Mode Overlay Info */}
      {isEditMode && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-[var(--bg-panel)] border border-[var(--border-color)] px-6 py-3 rounded-full shadow-2xl z-50 flex items-center gap-4 animate-in slide-in-from-bottom-4">
          <div className="text-sm font-bold">{t('editMode')}</div>
          <div className="w-[1px] h-4 bg-[var(--border-color)]"></div>
          <button onClick={() => setIsEditMode(false)} className="text-sm text-[var(--accent-green)] hover:underline font-bold">Done</button>
        </div>
      )}
    </div>
  );
}

function CockpitPage() {
  return (
    <AppLayout>
      <CockpitContent />
    </AppLayout>
  );
}

export default withAuth(CockpitPage);
