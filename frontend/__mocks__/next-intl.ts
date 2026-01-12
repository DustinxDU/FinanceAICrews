/**
 * Mock for next-intl module
 * 解决 Next.js 16 + next-intl ESM 兼容性问题
 */

import { vi } from 'vitest'

// Mock useTranslations hook
export const useTranslations = vi.fn((namespace?: string) => {
  return vi.fn((key: string, values?: Record<string, unknown>) => {
    if (values) {
      return `${namespace ? `${namespace}.` : ''}${key}:${JSON.stringify(values)}`
    }
    return `${namespace ? `${namespace}.` : ''}${key}`
  })
})

// Mock useLocale hook
export const useLocale = vi.fn(() => 'en')

// Mock useNow hook
export const useNow = vi.fn(() => new Date())

// Mock useTimeZone hook
export const useTimeZone = vi.fn(() => 'UTC')

// Mock useFormatter hook
export const useFormatter = vi.fn(() => ({
  dateTime: vi.fn((date: Date) => date.toISOString()),
  number: vi.fn((num: number) => num.toString()),
  relativeTime: vi.fn(() => 'just now'),
}))

// Mock useMessages hook
export const useMessages = vi.fn(() => ({}))

// Mock NextIntlClientProvider
export const NextIntlClientProvider = vi.fn(({ children }) => children)

// Mock navigation exports
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

export const Link = vi.fn(({ children, href, ...props }) => {
  // Return a simple anchor element mock
  return { type: 'a', props: { href, ...props, children } }
})

export const redirect = vi.fn()
export const permanentRedirect = vi.fn()

// createNavigation mock
export const createNavigation = vi.fn(() => ({
  Link,
  useRouter,
  usePathname,
  redirect,
  permanentRedirect,
}))

// createLocalizedPathnamesNavigation mock (legacy)
export const createLocalizedPathnamesNavigation = createNavigation

// getTranslations for server components
export const getTranslations = vi.fn(async (namespace?: string) => {
  return (key: string) => `${namespace ? `${namespace}.` : ''}${key}`
})

export const getLocale = vi.fn(async () => 'en')
export const getNow = vi.fn(async () => new Date())
export const getTimeZone = vi.fn(async () => 'UTC')
export const getMessages = vi.fn(async () => ({}))
export const getFormatter = vi.fn(async () => ({
  dateTime: (date: Date) => date.toISOString(),
  number: (num: number) => num.toString(),
}))

export default {
  useTranslations,
  useLocale,
  useNow,
  useTimeZone,
  useFormatter,
  useMessages,
  NextIntlClientProvider,
  useRouter,
  usePathname,
  useSearchParams,
  Link,
  redirect,
  permanentRedirect,
  createNavigation,
  createLocalizedPathnamesNavigation,
  getTranslations,
  getLocale,
  getNow,
  getTimeZone,
  getMessages,
  getFormatter,
}
