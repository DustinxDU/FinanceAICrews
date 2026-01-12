# 前端测试指南

## 测试文件命名

- 单元测试: `ComponentName.test.tsx`
- 集成测试: `ComponentName.integration.test.tsx`

## 测试模式

### 组件测试模板

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import { ComponentName } from '../ComponentName'

// Mock 外部依赖
vi.mock('@/lib/api', () => ({
  fetchData: vi.fn(),
}))

describe('ComponentName', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders correctly', () => {
    render(<ComponentName />)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('handles user interaction', async () => {
    render(<ComponentName />)
    fireEvent.click(screen.getByRole('button'))
    await waitFor(() => {
      expect(screen.getByText('Updated')).toBeInTheDocument()
    })
  })
})
```

### Hook 测试模板

```tsx
import { renderHook, act, waitFor } from '@testing-library/react'
import { useCustomHook } from '../useCustomHook'

describe('useCustomHook', () => {
  it('returns initial state', () => {
    const { result } = renderHook(() => useCustomHook())
    expect(result.current.value).toBe(initialValue)
  })

  it('updates state on action', async () => {
    const { result } = renderHook(() => useCustomHook())
    act(() => {
      result.current.setValue('new value')
    })
    expect(result.current.value).toBe('new value')
  })
})
```

## Mock 策略

| 依赖类型 | Mock 方式 |
|---------|----------|
| API 调用 | `vi.mock('@/lib/api')` |
| Next.js Router | `vi.mock('next/navigation')` |
| Context | 包装 Provider |
| WebSocket | 使用 fake timers |

## 运行测试

```bash
# 运行所有测试
npm test

# 运行测试并生成覆盖率报告
npm run test:coverage

# 运行特定测试文件
npm test -- path/to/test.tsx

# 监听模式
npm test -- --watch
```

## 覆盖率目标

- **Statements**: 30% (初始) -> 60% (目标)
- **Branches**: 30% (初始) -> 60% (目标)
- **Functions**: 30% (初始) -> 60% (目标)
- **Lines**: 30% (初始) -> 60% (目标)
