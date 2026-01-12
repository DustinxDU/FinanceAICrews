/**
 * Skill Catalog Hooks
 *
 * SWR hooks for fetching skill catalog data with caching and auto-refresh.
 */

"use client";

import { useMemo } from 'react';
import useSWR from 'swr';
import apiClient from '@/lib/api';
import type { Skill } from '@/lib/types';

// Local type definitions matching api.ts
interface SkillCatalogResponse {
  capabilities: Skill[];
  presets: Skill[];
  strategies: Skill[];
  skillsets: Skill[];
}

/**
 * Fetch skill catalog with caching and auto-refresh.
 *
 * @param params - Optional filter parameters
 * @param options - SWR options
 * @returns Skill catalog data and status
 */
export function useSkillCatalog(
  params?: { kind?: string; search?: string },
  options?: { refreshInterval?: number }
) {
  const { data, error, isLoading, mutate } = useSWR<SkillCatalogResponse>(
    ['/api/v1/skills/catalog', params],
    () => apiClient.getSkillCatalog(params),
    {
      refreshInterval: options?.refreshInterval || 30000, // 30s polling
      revalidateOnFocus: true,
      dedupingInterval: 2000, // Deduplicate requests within 2s
      errorRetryCount: 2, // Retry failed requests twice
    }
  );

  // Flatten all skills into a single array for searching
  const allSkills = useMemo(() => data ? [
    ...data.capabilities,
    ...data.presets,
    ...data.strategies,
    ...data.skillsets,
  ] : [], [data]);

  return {
    catalog: data,
    allSkills,
    isLoading,
    isError: !!error,
    error,
    mutate,
  };
}

// Re-export types for consumers
export type {
  SkillCatalogResponse,
};
