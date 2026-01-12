import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api';

/**
 * Crew Builder 数据 Hook
 * 使用 React Query 进行数据获取和缓存
 */
export function useCrewBuilderData() {
  return useQuery({
    queryKey: ['crew-builder-data'],
    queryFn: async () => {
      const [tools, config] = await Promise.all([
        apiClient.getTieredTools(),
        apiClient.getUserToolsConfig(),
      ]);
      return { tools, config };
    },
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    gcTime: 10 * 60 * 1000, // 10分钟垃圾回收
    retry: 2, // 失败重试2次
    retryDelay: 1000, // 重试间隔1秒
    refetchOnWindowFocus: false, // 窗口聚焦时不自动重新获取
  });
}

/**
 * 分离的 Tiered Tools Hook
 */
export function useTieredTools() {
  return useQuery({
    queryKey: ['tiered-tools'],
    queryFn: () => apiClient.getTieredTools(),
    staleTime: 5 * 60 * 1000,
    retry: 2,
    retryDelay: 1000,
    refetchOnWindowFocus: false,
  });
}

/**
 * 分离的 User Tools Config Hook
 */
export function useUserToolsConfig() {
  return useQuery({
    queryKey: ['user-tools-config'],
    queryFn: () => apiClient.getUserToolsConfig(),
    staleTime: 5 * 60 * 1000,
    retry: 2,
    retryDelay: 1000,
    refetchOnWindowFocus: false,
  });
}
