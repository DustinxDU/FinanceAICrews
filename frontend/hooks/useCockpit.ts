/**
 * Cockpit Dashboard Hook
 * 
 * 提供 Cockpit 仪表盘的完整数据管理：
 * - 获取聚合的仪表盘数据
 * - 订阅/取消订阅资产
 * - WebSocket 实时价格更新
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '@/lib/api';


// ==================== 类型定义 ====================

export interface CockpitMarketIndex {
  id: string;
  name: string;
  value: string;
  change: string;
  change_percent: number;
  trend: 'up' | 'down';
  critical: boolean;
  type: string;
}

export interface CockpitAssetPrice {
  ticker: string;
  name?: string;
  price?: number;
  change_percent?: number;
  change_value?: number;
  volume?: number;
  source: 'cache' | 'database' | 'pending';
  last_updated?: string;
}

export interface CockpitDashboardData {
  markets: CockpitMarketIndex[];
  assets: CockpitAssetPrice[];
  last_updated: string;
  cache_expired: boolean;
}

export interface UseCockpitOptions {
  /** 是否自动刷新 */
  autoRefresh?: boolean;
  /** 刷新间隔（毫秒） */
  refreshInterval?: number;
  /** 是否使用 WebSocket 实时更新 */
  useWebSocket?: boolean;
}

export interface UseCockpitReturn {
  /** 仪表盘数据 */
  data: CockpitDashboardData | null;
  /** 加载状态 */
  loading: boolean;
  /** 错误信息 */
  error: string | null;
  /** 市场指数 */
  markets: CockpitMarketIndex[];
  /** 用户资产 */
  assets: CockpitAssetPrice[];
  /** 刷新数据 */
  refresh: () => Promise<void>;
  /** 订阅资产 */
  subscribe: (ticker: string) => Promise<boolean>;
  /** 取消订阅 */
  unsubscribe: (ticker: string) => Promise<boolean>;
  /** WebSocket 连接状态 */
  wsConnected: boolean;
}


// ==================== Hook 实现 ====================

export function useCockpit(options: UseCockpitOptions = {}): UseCockpitReturn {
  const {
    autoRefresh = true,
    refreshInterval = 30000, // 30秒刷新
    useWebSocket = true
  } = options;

  const [data, setData] = useState<CockpitDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 获取仪表盘数据
  const fetchDashboard = useCallback(async (forceRefresh = false) => {
    try {
      setError(null);
      const response = await apiClient.getCockpitDashboard(forceRefresh);
      setData(response);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch cockpit data');
      console.error('Cockpit fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // 订阅资产
  const subscribe = useCallback(async (ticker: string): Promise<boolean> => {
    try {
      await apiClient.addUserAsset({ ticker, asset_type: 'US' });
      // 刷新数据
      await fetchDashboard(true);
      return true;
    } catch (err) {
      console.error('Subscribe error:', err);
      return false;
    }
  }, [fetchDashboard]);

  // 取消订阅
  const unsubscribe = useCallback(async (ticker: string): Promise<boolean> => {
    try {
      await apiClient.removeUserAsset(ticker);
      // 刷新数据
      await fetchDashboard(true);
      return true;
    } catch (err) {
      console.error('Unsubscribe error:', err);
      return false;
    }
  }, [fetchDashboard]);

  // WebSocket 连接管理
  const connectWebSocket = useCallback(() => {
    if (!useWebSocket) return;

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    const socket = new WebSocket(`${wsUrl}/api/v1/realtime/ws/price`);

    socket.onopen = () => {
      setWsConnected(true);
      console.log('Cockpit WebSocket connected');
    };

    socket.onclose = () => {
      setWsConnected(false);
      console.log('Cockpit WebSocket disconnected');
      // 尝试重连
      setTimeout(connectWebSocket, 5000);
    };

    socket.onerror = (err) => {
      console.error('Cockpit WebSocket error:', err);
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        if (message.type === 'price_update') {
          // 更新资产价格
          setData(prev => {
            if (!prev) return prev;
            
            return {
              ...prev,
              assets: prev.assets.map(asset =>
                asset.ticker === message.ticker
                  ? { ...asset, ...message.data, source: 'cache' as const }
                  : asset
              ),
              last_updated: new Date().toISOString()
            };
          });
        }
      } catch (err) {
        console.error('WebSocket message parse error:', err);
      }
    };

    wsRef.current = socket;
  }, [useWebSocket]);

  // 初始化
  useEffect(() => {
    fetchDashboard();

    // WebSocket 连接
    if (useWebSocket) {
      connectWebSocket();
    }

    // 自动刷新
    if (autoRefresh && !useWebSocket) {
      refreshTimerRef.current = setInterval(() => {
        fetchDashboard();
      }, refreshInterval);
    }

    // 清理
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [fetchDashboard, autoRefresh, refreshInterval, useWebSocket, connectWebSocket]);

  return {
    data,
    loading,
    error,
    markets: data?.markets || [],
    assets: data?.assets || [],
    refresh: () => fetchDashboard(true),
    subscribe,
    unsubscribe,
    wsConnected
  };
}


// ==================== 单个资产 Hook ====================

export function useAssetPrice(ticker: string, options: { useWs?: boolean } = {}) {
  const { useWs = true } = options;
  const [price, setPrice] = useState<CockpitAssetPrice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);

  const fetchPrice = useCallback(async () => {
    try {
      setError(null);
      const data = await apiClient.getAssetPrice(ticker);
      setPrice(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch price');
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  useEffect(() => {
    fetchPrice();

    // WebSocket 订阅
    if (useWs) {
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
      const socket = new WebSocket(`${wsUrl}/api/v1/realtime/ws/price`);

      socket.onopen = () => {
        setWsConnected(true);
        // 订阅该 ticker
        socket.send(JSON.stringify({ action: 'subscribe', tickers: [ticker] }));
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'price_update' && message.ticker === ticker) {
            setPrice(prev => prev ? { ...prev, ...message.data, source: 'cache' } : message.data);
          }
        } catch {}
      };

      socket.onclose = () => setWsConnected(false);
      wsRef.current = socket;
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [ticker, useWs, fetchPrice]);

  return { price, loading, error, wsConnected, refresh: fetchPrice };
}


// ==================== 市场指数 Hook ====================

export function useMarketIndices() {
  const [indices, setIndices] = useState<CockpitMarketIndex[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchIndices = useCallback(async () => {
    try {
      setError(null);
      const data = await apiClient.getCockpitMacroData();
      setIndices(data.indicators);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch indices');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchIndices();
    // 每5分钟刷新一次
    const interval = setInterval(fetchIndices, 300000);
    return () => clearInterval(interval);
  }, [fetchIndices]);

  return { indices, loading, error, refresh: fetchIndices };
}
