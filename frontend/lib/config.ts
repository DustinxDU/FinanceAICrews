'use client';

/**
 * Resolve API base URL for frontend fetch calls.
 *
 * Priority:
 * 1. Explicit NEXT_PUBLIC_API_URL (supports external backends / production)
 * 2. Relative path '' so Next.js rewrites/proxy can forward requests (works in Codespaces/tunnels)
 * 3. http://localhost:8000 fallback for Node-side execution (e.g. scripts)
 */
const LOCAL_FALLBACK_BASE = 'http://localhost:8000';

export function getApiBaseUrl(): string {
  const envValue = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (envValue) {
    return envValue;
  }
  if (typeof window !== 'undefined') {
    return '';
  }
  return LOCAL_FALLBACK_BASE;
}

export const API_BASE_URL = getApiBaseUrl();
