/**
 * Mock for i18n/routing module
 * 用于测试环境，避免 next-intl ESM 兼容性问题
 */

import { vi } from 'vitest'
import React from 'react'

export const routing = {
  locales: ['en', 'zh-CN', 'zh-TW', 'ja', 'ko', 'ms', 'id', 'vi', 'th', 'es', 'fr', 'de', 'ru', 'ar', 'hi', 'pt'],
  defaultLocale: 'en',
}

// Link 组件必须返回有效的 React 元素
export const Link = vi.fn(({ children, href, ...props }) => {
  return React.createElement('a', { href, ...props }, children)
})

export const redirect = vi.fn()

export const usePathname = vi.fn(() => '/')

export const useRouter = vi.fn(() => ({
  push: vi.fn(),
  replace: vi.fn(),
  prefetch: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
}))

export default {
  routing,
  Link,
  redirect,
  usePathname,
  useRouter,
}
