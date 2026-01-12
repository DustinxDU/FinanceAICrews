import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiClient } from '../api'

vi.mock('../auth', () => ({
  getToken: () => null,
  clearAuth: vi.fn(),
}))

describe('ApiClient', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('handles 204 No Content responses for delete endpoints', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }))

    await expect(apiClient.deleteByokProfileByTier('fast')).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenCalledOnce()
  })
})
