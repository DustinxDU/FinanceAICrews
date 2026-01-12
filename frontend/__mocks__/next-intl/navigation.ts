/**
 * Mock for next-intl/navigation module
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

export const Link = vi.fn(({ children, href, ...props }) => {
  return { type: 'a', props: { href, ...props, children } }
})

export const redirect = vi.fn()
export const permanentRedirect = vi.fn()

export const createNavigation = vi.fn((routing) => ({
  Link,
  useRouter,
  usePathname,
  redirect,
  permanentRedirect,
  getPathname: vi.fn(() => '/'),
}))

export const createLocalizedPathnamesNavigation = createNavigation

export default {
  useRouter,
  usePathname,
  useSearchParams,
  useParams,
  Link,
  redirect,
  permanentRedirect,
  createNavigation,
  createLocalizedPathnamesNavigation,
}
