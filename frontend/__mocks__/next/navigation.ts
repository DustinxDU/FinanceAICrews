/**
 * Mock for next/navigation module
 * 解决 Next.js 16 + next-intl ESM 兼容性问题
 */

import { vi } from 'vitest'

export const useRouter = vi.fn(() => ({
  push: vi.fn(),
  replace: vi.fn(),
  prefetch: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
}))

export const usePathname = vi.fn(() => '/')
export const useSearchParams = vi.fn(() => new URLSearchParams())
export const useParams = vi.fn(() => ({}))
export const useSelectedLayoutSegment = vi.fn(() => null)
export const useSelectedLayoutSegments = vi.fn(() => [])

export const redirect = vi.fn()
export const permanentRedirect = vi.fn()
export const notFound = vi.fn()

// Next.js 16 新增
export const forbidden = vi.fn()
export const unauthorized = vi.fn()

export default {
  useRouter,
  usePathname,
  useSearchParams,
  useParams,
  useSelectedLayoutSegment,
  useSelectedLayoutSegments,
  redirect,
  permanentRedirect,
  notFound,
  forbidden,
  unauthorized,
}
