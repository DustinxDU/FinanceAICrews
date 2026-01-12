'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Building2,
  TrendingUp,
  TrendingDown,
  ChevronDown,
  ChevronUp,
  BarChart3,
  DollarSign,
  Percent,
  Activity,
} from 'lucide-react';
import { cardVariants, staggerChildren, slideUp } from '../core/animations';
import { registerChartComponent, ChartComponentProps } from '../core/chartRegistry';

// ============ Types ============

export interface StockInfoCardV2Props {
  data: {
    symbol: string;
    info: {
      shortName?: string;
      longName?: string;
      sector?: string;
      industry?: string;
      currentPrice?: number;
      previousClose?: number;
      fiftyTwoWeekLow?: number;
      fiftyTwoWeekHigh?: number;
      marketCap?: number;
      forwardPE?: number;
      priceToBook?: number;
      revenueGrowth?: number;
      longBusinessSummary?: string;
    };
  };
}

// ============ Helpers ============

/**
 * Format large numbers with T/B/M/K suffixes
 */
function formatLargeNumber(num: number | undefined): string {
  if (num === undefined || num === null) return '-';

  const absNum = Math.abs(num);
  if (absNum >= 1e12) {
    return `${(num / 1e12).toFixed(1)}T`;
  }
  if (absNum >= 1e9) {
    return `${(num / 1e9).toFixed(1)}B`;
  }
  if (absNum >= 1e6) {
    return `${(num / 1e6).toFixed(1)}M`;
  }
  if (absNum >= 1e3) {
    return `${(num / 1e3).toFixed(1)}K`;
  }
  return num.toFixed(2);
}

/**
 * Format a decimal as a percentage
 */
function formatPercent(value: number | undefined): string {
  if (value === undefined || value === null) return '-';
  return `${(value * 100).toFixed(2)}%`;
}

/**
 * Format currency value
 */
function formatCurrency(value: number | undefined): string {
  if (value === undefined || value === null) return '-';
  return `$${value.toFixed(2)}`;
}

// ============ Component ============

export function StockInfoCardV2Component({ data }: StockInfoCardV2Props) {
  const [aboutExpanded, setAboutExpanded] = useState(false);
  const { symbol, info } = data;

  // Calculate price change
  const currentPrice = info.currentPrice ?? 0;
  const previousClose = info.previousClose ?? currentPrice;
  const priceChange = currentPrice - previousClose;
  const priceChangePercent = previousClose > 0 ? (priceChange / previousClose) * 100 : 0;
  const isPositive = priceChange >= 0;

  // Calculate 52-week range position
  const low52 = info.fiftyTwoWeekLow ?? 0;
  const high52 = info.fiftyTwoWeekHigh ?? 0;
  const rangeWidth = high52 - low52;
  const rangePosition = rangeWidth > 0 ? ((currentPrice - low52) / rangeWidth) * 100 : 50;

  // Get company name
  const companyName = info.shortName || info.longName || symbol;

  return (
    <motion.div
      className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4 sm:p-5 backdrop-blur-sm"
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      data-testid="stock-info-card-v2"
    >
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <Building2 className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">{companyName}</h3>
            <span className="text-sm text-slate-400 font-mono">{symbol}</span>
          </div>
        </div>

        {/* Sector/Industry Badges */}
        <div className="flex flex-wrap gap-2 sm:justify-end">
          {info.sector && (
            <span className="px-2.5 py-1 text-xs font-medium bg-purple-500/20 text-purple-300 rounded-full">
              {info.sector}
            </span>
          )}
          {info.industry && (
            <span className="px-2.5 py-1 text-xs font-medium bg-teal-500/20 text-teal-300 rounded-full">
              {info.industry}
            </span>
          )}
        </div>
      </div>

      {/* Price Section */}
      {info.currentPrice !== undefined && (
        <div className="mb-5">
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-bold text-white">
              {formatCurrency(currentPrice)}
            </span>
            <div
              className={`flex items-center gap-1 text-sm font-medium ${
                isPositive ? 'text-green-400' : 'text-red-400'
              }`}
            >
              {isPositive ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <TrendingDown className="w-4 h-4" />
              )}
              <span>
                {isPositive ? '+' : '-'}${Math.abs(priceChange).toFixed(2)}
              </span>
              <span>
                ({isPositive ? '+' : '-'}{Math.abs(priceChangePercent).toFixed(2)}%)
              </span>
            </div>
          </div>
          {info.previousClose !== undefined && (
            <p className="text-xs text-slate-500 mt-1">
              Previous Close: {formatCurrency(previousClose)}
            </p>
          )}
        </div>
      )}

      {/* 52-Week Range */}
      {info.fiftyTwoWeekLow !== undefined && info.fiftyTwoWeekHigh !== undefined && (
        <div className="mb-5">
          <p className="text-xs text-slate-400 mb-2">52-Week Range</p>
          <div className="relative">
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>{low52.toFixed(2)}</span>
              <span>{high52.toFixed(2)}</span>
            </div>
            <div className="h-2 bg-slate-700/50 rounded-full relative overflow-hidden">
              {/* Gradient background */}
              <div className="absolute inset-0 bg-gradient-to-r from-red-500/30 via-yellow-500/30 to-green-500/30" />
              {/* Position marker */}
              <motion.div
                className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-blue-400 rounded-full border-2 border-white shadow-lg"
                initial={{ left: '0%' }}
                animate={{ left: `calc(${Math.max(0, Math.min(100, rangePosition))}% - 6px)` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Metrics Grid - Responsive */}
      <motion.div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3 mb-4"
        variants={staggerChildren}
        initial="hidden"
        animate="visible"
      >
        {/* Market Cap */}
        <motion.div
          className="bg-slate-900/50 rounded-lg p-3"
          variants={slideUp}
        >
          <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
            <DollarSign className="w-3 h-3" />
            <span>Market Cap</span>
          </div>
          <p className="text-sm font-semibold text-white">
            {formatLargeNumber(info.marketCap)}
          </p>
        </motion.div>

        {/* P/E (Forward) */}
        <motion.div
          className="bg-slate-900/50 rounded-lg p-3"
          variants={slideUp}
        >
          <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
            <BarChart3 className="w-3 h-3" />
            <span>P/E (Fwd)</span>
          </div>
          <p className="text-sm font-semibold text-white">
            {info.forwardPE !== undefined ? info.forwardPE.toFixed(2) : '-'}
          </p>
        </motion.div>

        {/* P/B */}
        <motion.div
          className="bg-slate-900/50 rounded-lg p-3"
          variants={slideUp}
        >
          <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
            <Activity className="w-3 h-3" />
            <span>P/B</span>
          </div>
          <p className="text-sm font-semibold text-white">
            {info.priceToBook !== undefined ? info.priceToBook.toFixed(2) : '-'}
          </p>
        </motion.div>

        {/* Revenue Growth */}
        <motion.div
          className="bg-slate-900/50 rounded-lg p-3"
          variants={slideUp}
        >
          <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
            <Percent className="w-3 h-3" />
            <span>Rev Growth</span>
          </div>
          <p className="text-sm font-semibold text-white">
            {formatPercent(info.revenueGrowth)}
          </p>
        </motion.div>
      </motion.div>

      {/* About Section (Collapsible) */}
      {info.longBusinessSummary && (
        <div className="border-t border-slate-700/50 pt-3">
          <button
            onClick={() => setAboutExpanded(!aboutExpanded)}
            className="flex items-center justify-between w-full text-sm text-slate-400 hover:text-slate-300 transition-colors"
            aria-expanded={aboutExpanded}
          >
            <span className="font-medium">About</span>
            {aboutExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          <AnimatePresence>
            {aboutExpanded && (
              <motion.p
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="text-xs text-slate-400 mt-2 leading-relaxed overflow-hidden"
              >
                {info.longBusinessSummary}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  );
}

// Wrap with React.memo to prevent unnecessary re-renders
export const StockInfoCardV2 = React.memo(StockInfoCardV2Component);
StockInfoCardV2.displayName = 'StockInfoCardV2';

// ============ Chart Router Registration ============

// Adapter to match ChartComponentProps interface
function StockInfoCardV2Adapter({ data }: ChartComponentProps) {
  return <StockInfoCardV2 data={data} />;
}

// Register with ChartRouter for 'stock_info' data type
registerChartComponent('stock_info', StockInfoCardV2Adapter);

export default StockInfoCardV2;
