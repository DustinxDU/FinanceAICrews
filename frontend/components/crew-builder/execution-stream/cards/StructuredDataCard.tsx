'use client';

import React from 'react';
import { ExternalLink, TrendingUp, TrendingDown, Building2, Globe, Calendar } from 'lucide-react';
import { StructuredData } from '../eventMapper';

interface StructuredDataCardProps {
  data: StructuredData;
}

/**
 * Formats a large number for display
 */
function formatNumber(num?: number | string): string {
  if (num === undefined || num === null) return '-';
  if (typeof num === 'string') return num;

  if (Math.abs(num) >= 1e12) return (num / 1e12).toFixed(2) + 'T';
  if (Math.abs(num) >= 1e9) return (num / 1e9).toFixed(2) + 'B';
  if (Math.abs(num) >= 1e6) return (num / 1e6).toFixed(2) + 'M';
  if (Math.abs(num) >= 1e3) return (num / 1e3).toFixed(2) + 'K';
  return num.toFixed(2);
}

/**
 * Formats a date string
 */
function formatDate(dateStr?: string): string {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

export const StructuredDataCard = ({ data }: StructuredDataCardProps) => {
  switch (data.type) {
    case 'news':
      return <NewsCard data={data.data} title={data.title} />;

    case 'quote':
      return <QuoteCard data={data.data} title={data.title} />;

    case 'stock_info':
      return <StockInfoCard data={data.data} title={data.title} />;

    default:
      return null;
  }
};

/**
 * News Card - Displays news articles in a list format
 */
function NewsCard({ data, title }: { data: any; title?: string }) {
  const { symbol, news, totalCount } = data;

  return (
    <div className="space-y-3">
      {title && (
        <div className="flex items-center justify-between pb-2 border-b border-gray-700">
          <h4 className="text-sm font-semibold text-green-400">{title}</h4>
          <span className="text-xs text-gray-500">{totalCount} articles</span>
        </div>
      )}

      {symbol && (
        <div className="text-xs text-gray-400 mb-2">
          <span className="font-mono text-green-400">{symbol}</span>
        </div>
      )}

      <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
        {news.map((item: any, index: number) => (
          <div
            key={index}
            className="p-3 bg-gray-900/50 rounded-lg border border-gray-700/50 hover:border-green-500/30 transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <h5 className="text-sm font-medium text-gray-200 line-clamp-2 flex-1">
                {item.title}
              </h5>
              {item.pubDate && (
                <span className="text-[10px] text-gray-500 whitespace-nowrap">
                  {formatDate(item.pubDate)}
                </span>
              )}
            </div>

            {item.summary && (
              <p className="text-xs text-gray-400 mt-1 line-clamp-2">{item.summary}</p>
            )}

            <div className="flex items-center justify-between mt-2">
              {item.provider && (
                <span className="text-[10px] text-gray-500 flex items-center gap-1">
                  <Globe size={10} />
                  {item.provider}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Quote Card - Displays stock quote with price and change
 */
function QuoteCard({ data, title }: { data: any; title?: string }) {
  const {
    symbol,
    price,
    change,
    changePercent,
    volume,
    marketCap,
    previousClose,
    open,
    dayHigh,
    dayLow,
  } = data;

  const isPositive = change >= 0;
  const changeColor = isPositive ? 'text-green-400' : 'text-red-400';
  const changeBg = isPositive ? 'bg-green-500/20' : 'bg-red-500/20';

  return (
    <div className="space-y-3">
      {title && (
        <div className="flex items-center justify-between pb-2 border-b border-gray-700">
          <h4 className="text-sm font-semibold text-green-400">{title}</h4>
        </div>
      )}

      {/* Price and Change */}
      <div className="flex items-end gap-3">
        <div className="text-2xl font-bold text-white">${price?.toFixed(2)}</div>
        <div
          className={`flex items-center gap-1 px-2 py-0.5 rounded ${changeBg} ${changeColor}`}
        >
          {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          <span className="text-sm font-medium">
            {isPositive ? '+' : ''}
            {change?.toFixed(2)} ({isPositive ? '+' : ''}
            {changePercent?.toFixed(2)}%)
          </span>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="p-2 bg-gray-900/50 rounded">
          <div className="text-gray-500">Volume</div>
          <div className="text-gray-200 font-medium">{formatNumber(volume)}</div>
        </div>
        <div className="p-2 bg-gray-900/50 rounded">
          <div className="text-gray-500">Market Cap</div>
          <div className="text-gray-200 font-medium">{formatNumber(marketCap)}</div>
        </div>
        <div className="p-2 bg-gray-900/50 rounded">
          <div className="text-gray-500">Open</div>
          <div className="text-gray-200 font-medium">${open?.toFixed(2)}</div>
        </div>
        <div className="p-2 bg-gray-900/50 rounded">
          <div className="text-gray-500">Prev Close</div>
          <div className="text-gray-200 font-medium">${previousClose?.toFixed(2)}</div>
        </div>
        <div className="p-2 bg-gray-900/50 rounded">
          <div className="text-gray-500">Day High</div>
          <div className="text-green-400 font-medium">${dayHigh?.toFixed(2)}</div>
        </div>
        <div className="p-2 bg-gray-900/50 rounded">
          <div className="text-gray-500">Day Low</div>
          <div className="text-red-400 font-medium">${dayLow?.toFixed(2)}</div>
        </div>
      </div>
    </div>
  );
}

/**
 * Stock Info Card - Displays company information
 */
function StockInfoCard({ data, title }: { data: any; title?: string }) {
  const { symbol, companyName, sector, industry, marketCap, peRatio, eps, dividend, beta } = data;

  return (
    <div className="space-y-3">
      {title && (
        <div className="flex items-center justify-between pb-2 border-b border-gray-700">
          <h4 className="text-sm font-semibold text-green-400">{title}</h4>
        </div>
      )}

      {/* Company Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center">
          <Building2 size={20} className="text-green-400" />
        </div>
        <div>
          <div className="text-lg font-bold text-white">{companyName || symbol}</div>
          {symbol && <div className="text-sm text-gray-400 font-mono">{symbol}</div>}
        </div>
      </div>

      {/* Sector/Industry */}
      {(sector || industry) && (
        <div className="flex gap-2 text-xs">
          {sector && (
            <span className="px-2 py-1 bg-gray-800 rounded text-gray-300">{sector}</span>
          )}
          {industry && (
            <span className="px-2 py-1 bg-gray-800 rounded text-gray-400">{industry}</span>
          )}
        </div>
      )}

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="p-2 bg-gray-900/50 rounded">
          <div className="text-gray-500">Market Cap</div>
          <div className="text-gray-200 font-medium">{formatNumber(marketCap)}</div>
        </div>
        <div className="p-2 bg-gray-900/50 rounded">
          <div className="text-gray-500">P/E Ratio</div>
          <div className="text-gray-200 font-medium">{peRatio ?? '-'}</div>
        </div>
        <div className="p-2 bg-gray-900/50 rounded">
          <div className="text-gray-500">EPS</div>
          <div className="text-gray-200 font-medium">${eps ?? '-'}</div>
        </div>
        <div className="p-2 bg-gray-900/50 rounded">
          <div className="text-gray-500">Dividend</div>
          <div className="text-gray-200 font-medium">{dividend ?? '-'}</div>
        </div>
        <div className="p-2 bg-gray-900/50 rounded">
          <div className="text-gray-500">Beta</div>
          <div className="text-gray-200 font-medium">{beta ?? '-'}</div>
        </div>
      </div>
    </div>
  );
}

export default StructuredDataCard;
