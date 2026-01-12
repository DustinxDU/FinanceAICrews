"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { MarketIndex, MarketDataResponse, apiClient } from "@/lib/api";

// Indicator item from personalized cockpit data
interface CockpitIndicator {
  id: string;
  name: string;
  value: string;
  change: string;
  change_percent: number;
  trend: string;
  critical: boolean;
  symbol: string;
  type: string;
}

interface MarketTickerProps {
  intervalMs?: number; // Scroll interval in milliseconds (default: 30000 = 30s)
  className?: string;
}

export function MarketTicker({ intervalMs = 30000, className = "" }: MarketTickerProps) {
  const [indicators, setIndicators] = useState<CockpitIndicator[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const scrollTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch personalized cockpit data (synced with Global Context)
  const fetchIndicatorData = useCallback(async () => {
    try {
      const data = await apiClient.getPersonalizedCockpitData();
      if (data.indicators && data.indicators.length > 0) {
        setIndicators(data.indicators);
        setLastUpdated(data.last_updated);
      }
      setError(null);
      setIsLoading(false);
    } catch (err) {
      console.error("Failed to fetch indicator data:", err);
      setError("Failed to load market data");
      setIsLoading(false);
    }
  }, []);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    fetchIndicatorData();
    
    refreshTimerRef.current = setInterval(() => {
      fetchIndicatorData();
    }, 5 * 60 * 1000); // 5 minutes

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [fetchIndicatorData]);

  // Scroll to next indicator every interval
  useEffect(() => {
    if (indicators.length <= 1) return;

    scrollTimerRef.current = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % indicators.length);
    }, intervalMs);

    return () => {
      if (scrollTimerRef.current) {
        clearInterval(scrollTimerRef.current);
      }
    };
  }, [indicators.length, intervalMs]);

  // Get current indicator
  const currentIndicator = indicators[currentIndex];

  // Get type icon
  const getTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      macro: "📊",
      index: "📈",
      crypto: "₿",
      commodity: "🪙",
    };
    return icons[type] || "📊";
  };

  // Get change color
  const getChangeColor = (trend: string) => {
    return trend === "up" ? "var(--accent-green)" : "var(--accent-red)";
  };

  if (isLoading) {
    return (
      <div className={`flex items-center gap-2 text-xs ${className}`}>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[var(--accent-green)]">Loading...</span>
        </div>
      </div>
    );
  }

  if (error || !currentIndicator) {
    return (
      <div className={`flex items-center gap-2 text-xs ${className}`}>
        <span className="font-mono text-[var(--text-secondary)]">
          Market data unavailable
        </span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-4 ${className}`}>
      {/* Indicator info display */}
      <div className="flex items-center gap-2">
        <span className="text-lg">{getTypeIcon(currentIndicator.type)}</span>
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-sm text-[var(--text-primary)]">
            {currentIndicator.name}
          </span>
          <span className="font-mono text-[var(--text-primary)]">
            {currentIndicator.value}
          </span>
          <span
            className="font-mono text-xs font-medium"
            style={{ color: getChangeColor(currentIndicator.trend) }}
          >
            ({currentIndicator.change})
          </span>
        </div>
      </div>

      {/* Progress indicator */}
      <div className="flex items-center gap-1 ml-2">
        {indicators.map((_: CockpitIndicator, index: number) => (
          <div
            key={index}
            className={`w-1.5 h-1.5 rounded-full transition-all duration-300 ${
              index === currentIndex
                ? "bg-[var(--accent-blue)] w-3"
                : "bg-[var(--border-color)]"
            }`}
          />
        ))}
      </div>

      {/* Timestamp */}
      {lastUpdated && (
        <span className="text-[10px] text-[var(--text-tertiary)] ml-auto">
          Updated: {new Date(lastUpdated).toLocaleTimeString()}
        </span>
      )}
    </div>
  );
}

// Static version that shows a single market summary
export function MarketSummary({ className = "" }: { className?: string }) {
  const [market, setMarket] = useState<MarketIndex | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data: MarketDataResponse = await apiClient.getGlobalMarketData();
        if (data.markets.length > 0) {
          // Show NASDAQ as default
          const nasdaq = data.markets.find(m => m.code === "NASDAQ") || data.markets[0];
          setMarket(nasdaq);
        }
      } catch (err) {
        console.error("Failed to fetch market data:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (isLoading || !market) {
    return (
      <div className={`flex items-center gap-2 text-xs ${className}`}>
        <span className="font-mono text-[var(--accent-green)]">Loading...</span>
      </div>
    );
  }

  const formatPrice = (price: number) => {
    return price.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  const formatChange = (changePercent: number) => {
    const sign = changePercent >= 0 ? "+" : "";
    return `${sign}${changePercent.toFixed(2)}%`;
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className="font-mono font-bold text-[var(--accent-green)]">
        {market.name}
      </span>
      <span className="font-mono text-[var(--text-secondary)]">
        {formatPrice(market.price)}
      </span>
      <span 
        className="font-mono text-xs"
        style={{ color: market.is_up ? "var(--accent-green)" : "var(--accent-red)" }}
      >
        {formatChange(market.change_percent)}
      </span>
    </div>
  );
}

export default MarketTicker;
