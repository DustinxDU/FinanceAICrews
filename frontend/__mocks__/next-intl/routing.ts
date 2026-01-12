/**
 * Mock for next-intl/routing module
 */

import { vi } from 'vitest'

export const defineRouting = vi.fn((config) => ({
  locales: config?.locales || ['en'],
  defaultLocale: config?.defaultLocale || 'en',
  localePrefix: config?.localePrefix || 'always',
  pathnames: config?.pathnames || {},
  ...config,
}))

export const defineLocale = vi.fn((locale) => locale)

export default {
  defineRouting,
  defineLocale,
}
