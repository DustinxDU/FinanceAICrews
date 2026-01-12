/**
 * 组件测试模板
 *
 * 复制此文件并重命名为 YourComponent.test.tsx
 * 替换 TemplateComponent 为实际组件名
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'

// 1. 导入被测组件
// import { YourComponent } from '../YourComponent'

// 2. Mock 外部依赖
vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}))

// 3. 测试套件
describe('TemplateComponent', () => {
  // 4. 每个测试前重置 mocks
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // 5. 渲染测试
  it('renders without crashing', () => {
    // render(<YourComponent />)
    // expect(screen.getByTestId('your-component')).toBeInTheDocument()
    expect(true).toBe(true) // Placeholder
  })

  // 6. 交互测试
  it('handles click event', async () => {
    // render(<YourComponent />)
    // fireEvent.click(screen.getByRole('button'))
    // await waitFor(() => {
    //   expect(mockApi.get).toHaveBeenCalled()
    // })
    expect(true).toBe(true) // Placeholder
  })

  // 7. 错误状态测试
  it('displays error message on failure', async () => {
    // const mockApi = await import('@/lib/api')
    // mockApi.api.get.mockRejectedValue(new Error('Failed'))
    // render(<YourComponent />)
    // await waitFor(() => {
    //   expect(screen.getByText(/error/i)).toBeInTheDocument()
    // })
    expect(true).toBe(true) // Placeholder
  })
})
