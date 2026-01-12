import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useExecutionStream } from '../useExecutionStream'
import { RunEventType } from '../types'

describe('useExecutionStream', () => {
  let mockWebSocket: any;
  const wsUrl = 'ws://localhost:8000/api/v1/realtime/ws/analysis/test-run'

  beforeEach(() => {
    mockWebSocket = {
      send: vi.fn(),
      close: vi.fn(),
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null,
    };
    
    // @ts-ignore
    global.WebSocket = vi.fn(function() {
      return mockWebSocket;
    });
    
    // Mock NEXT_PUBLIC_WS_URL
    process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000'
  })

  afterEach(() => {
    vi.clearAllMocks();
  })

  it('connects to WebSocket and initializes empty steps', () => {
    const { result } = renderHook(() => useExecutionStream('test-run'))
    
    expect(global.WebSocket).toHaveBeenCalledWith(wsUrl)
    expect(result.current.steps).toEqual([])
    expect(result.current.isConnected).toBe(false)
  })

  it('updates isConnected when socket opens', () => {
    const { result } = renderHook(() => useExecutionStream('test-run'))
    
    act(() => {
      if (mockWebSocket.onopen) mockWebSocket.onopen()
    })
    
    expect(result.current.isConnected).toBe(true)
  })

  it('transforms ACTIVITY event into thought step', () => {
    const { result } = renderHook(() => useExecutionStream('test-run'))
    
    const mockEvent = {
      event_id: 'e1',
      run_id: 'test-run',
      event_type: RunEventType.ACTIVITY,
      timestamp: new Date().toISOString(),
      agent_name: 'Analyst',
      payload: {
        activity_type: 'thinking',
        message: 'Thinking about stocks'
      }
    }

    act(() => {
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage({ data: JSON.stringify(mockEvent) })
      }
    })

    expect(result.current.steps).toHaveLength(1)
    expect(result.current.steps[0]).toMatchObject({
      id: 'e1',
      type: 'thought',
      content: 'Thinking about stocks',
      agentName: 'Analyst'
    })
  })

  it('transforms TOOL_CALL and TOOL_RESULT events', () => {
    const { result } = renderHook(() => useExecutionStream('test-run'))
    
    // 1. Tool Call
    const callEvent = {
      event_id: 'e2',
      event_type: RunEventType.TOOL_CALL,
      agent_name: 'Researcher',
      payload: {
        tool_name: 'Search',
        input_data: { q: 'AAPL' }
      }
    }

    act(() => {
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage({ data: JSON.stringify(callEvent) })
      }
    })

    expect(result.current.steps).toHaveLength(1)
    expect(result.current.steps[0].type).toBe('tool_call')

    // 2. Tool Result (Observation)
    const resultEvent = {
      event_id: 'e3',
      event_type: RunEventType.TOOL_RESULT,
      agent_name: 'Researcher',
      payload: {
        tool_name: 'Search',
        output_data: 'Found some data'
      }
    }

    act(() => {
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage({ data: JSON.stringify(resultEvent) })
      }
    })

    expect(result.current.steps).toHaveLength(2)
    expect(result.current.steps[1].type).toBe('observation')
    expect(result.current.steps[1].content).toBe('Found some data')
  })

  it('transforms LLM_CALL event', () => {
    const { result } = renderHook(() => useExecutionStream('test-run'))
    
    const llmEvent = {
      event_id: 'e4',
      event_type: RunEventType.LLM_CALL,
      agent_name: 'Analyst',
      payload: {
        model_name: 'gpt-4',
        message: 'Final Answer: Buy AAPL',
        status: 'success'
      }
    }

    act(() => {
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage({ data: JSON.stringify(llmEvent) })
      }
    })

    expect(result.current.steps).toHaveLength(1)
    expect(result.current.steps[0].type).toBe('final_answer')
  })

  it('handles TASK_STATE event (returns null)', () => {
    const { result } = renderHook(() => useExecutionStream('test-run'))
    
    const taskEvent = {
      event_id: 'e5',
      event_type: RunEventType.TASK_STATE,
      payload: { status: 'completed' }
    }

    act(() => {
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage({ data: JSON.stringify(taskEvent) })
      }
    })

    expect(result.current.steps).toHaveLength(0)
  })

  it('clears steps', () => {
    const { result } = renderHook(() => useExecutionStream('test-run'))
    
    act(() => {
        if (mockWebSocket.onmessage) {
            mockWebSocket.onmessage({ data: JSON.stringify({
                event_id: 'e1',
                event_type: RunEventType.ACTIVITY,
                payload: { message: 'thinking' }
            })})
        }
    })
    
    expect(result.current.steps).toHaveLength(1)
    
    act(() => {
        result.current.clearSteps()
    })
    
    expect(result.current.steps).toHaveLength(0)
  })

  it('handles socket close and error', () => {
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    
    const { result } = renderHook(() => useExecutionStream('test-run'))
    
    act(() => {
      if (mockWebSocket.onclose) mockWebSocket.onclose()
    })
    expect(result.current.isConnected).toBe(false)
    expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Disconnected'))

    act(() => {
        if (mockWebSocket.onerror) mockWebSocket.onerror(new Error('fail'))
    })
    expect(consoleErrorSpy).toHaveBeenCalledWith(
        expect.stringContaining('WebSocket error'),
        expect.anything()
    )
  })
})
