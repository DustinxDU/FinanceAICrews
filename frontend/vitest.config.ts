import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // 修复 Next.js 16 + next-intl ESM 模块兼容性
      'next/navigation': path.resolve(__dirname, './__mocks__/next/navigation.ts'),
      'next-intl': path.resolve(__dirname, './__mocks__/next-intl.ts'),
      'next-intl/navigation': path.resolve(__dirname, './__mocks__/next-intl/navigation.ts'),
      'next-intl/routing': path.resolve(__dirname, './__mocks__/next-intl/routing.ts'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      'tests/e2e/**',  // Playwright e2e tests - run separately
    ],
    alias: [
      // Mock i18n/routing 必须在 @ 别名之前（更具体的路径优先）
      { find: /^@\/i18n\/routing$/, replacement: path.resolve(__dirname, './__mocks__/i18n/routing.ts') },
      { find: /^i18n\/routing$/, replacement: path.resolve(__dirname, './__mocks__/i18n/routing.ts') },
      // 修复 Next.js 16 + next-intl ESM 模块兼容性
      { find: /^next\/navigation$/, replacement: path.resolve(__dirname, './__mocks__/next/navigation.ts') },
      { find: /^next-intl$/, replacement: path.resolve(__dirname, './__mocks__/next-intl.ts') },
      { find: /^next-intl\/navigation$/, replacement: path.resolve(__dirname, './__mocks__/next-intl/navigation.ts') },
      { find: /^next-intl\/routing$/, replacement: path.resolve(__dirname, './__mocks__/next-intl/routing.ts') },
      // 通用别名
      { find: '@', replacement: path.resolve(__dirname, './') },
      { find: '@v2', replacement: path.resolve(__dirname, './v2') },
    ],
    // 强制内联 next-intl 以应用别名
    deps: {
      optimizer: {
        web: {
          include: ['next-intl'],
        },
      },
    },
    // 覆盖率配置
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'json-summary'],
      reportsDirectory: './coverage',
      exclude: [
        'node_modules/**',
        'tests/**',
        '**/*.d.ts',
        '**/*.config.*',
        '**/types/**',
      ],
      thresholds: {
        statements: 30,  // 初始阈值，逐步提升
        branches: 30,
        functions: 30,
        lines: 30,
      },
    },
  },
})
