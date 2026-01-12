import { RunEvent, TaskOutputPayload } from '@/lib/types';

// === Phase Events (System) ===
export const phaseEvents: RunEvent[] = [
  {
    event_id: 'phase-1',
    run_id: 'run-1',
    timestamp: new Date().toISOString(),
    event_type: 'activity',
    severity: 'info',
    agent_name: 'System',  // 顶层 agent_name
    payload: {
      activity_type: 'phase',
      message: 'Execution started'
    }
  },
  {
    event_id: 'phase-2',
    run_id: 'run-1',
    timestamp: new Date().toISOString(),
    event_type: 'activity',
    severity: 'info',
    agent_name: 'System',  // 顶层 agent_name
    payload: {
      activity_type: 'phase',
      message: 'Assembling crew...'
    }
  }
];

// === Tool Call/Result Events (Market Data Researcher) ===
// 真实结构: agent_name 在顶层，payload 包含 tool_name, status, input_data
export const marketAgentEvents: RunEvent[] = [
  {
    event_id: 'tool-call-1',
    run_id: 'run-1',
    timestamp: new Date().toISOString(),
    event_type: 'tool_call',
    severity: 'info',
    agent_name: 'Market Data Researcher',  // 顶层 agent_name (关键!)
    payload: {
      tool_name: 'mcp_yfinance_stock_history',
      status: 'pending',
      input_data: { symbol: 'AAPL', period: '1mo', interval: '1d' }
      // 注意: payload 内可能也有 agent_name，但我们优先用顶层
    }
  },
  {
    event_id: 'tool-result-1',
    run_id: 'run-1',
    timestamp: new Date().toISOString(),
    event_type: 'tool_result',
    severity: 'info',
    agent_name: 'Market Data Researcher',  // 顶层 agent_name (关键!)
    payload: {
      tool_name: 'mcp_yfinance_stock_history',
      status: 'success',
      output_data: JSON.stringify({
        symbol: 'AAPL',
        period: '1mo',
        interval: '1d',
        columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'],
        data: [
          { Date: '2025-12-09 00:00:00+08:00', Open: 240.5, High: 242.3, Low: 239.8, Close: 241.5, Volume: 52340000 },
          { Date: '2025-12-10 00:00:00+08:00', Open: 241.5, High: 243.1, Low: 240.9, Close: 242.8, Volume: 48920000 }
        ]
      }),
      duration_ms: 1234,  // 真实字段名 (不是 duration)
      error_message: null
    }
  }
];

// === Agent Output Event (真实 TaskOutputPayload 结构) ===
// 关键: agent_name 在顶层，payload 不一定包含 agent_name
export const agentOutputEvent: RunEvent = {
  event_id: 'task-output-1',
  run_id: 'run-1',
  timestamp: new Date().toISOString(),
  event_type: 'task_output',
  severity: 'info',
  agent_name: 'Market Data Researcher',  // 顶层 agent_name (关键!)
  task_id: 'task-1',
  payload: {
    // 真实 TaskOutputPayload 结构
    summary: {
      raw_preview: 'Apple Inc. (AAPL) stock analysis based on the past month\'s price action reveals several key technical indicators...',
      validation_passed: true,
      pydantic_dump: {
        summary: 'Apple Inc. shows strong momentum...',
        recommendations: ['BUY', 'HOLD'],
        confidence: 0.85
      }
    },
    artifact_ref: {
      job_id: 'job-123',
      task_id: 'task-1',
      path: '/artifacts/task-1.json'
    },
    diagnostics: {
      output_mode: 'soft_pydantic',
      schema_key: 'MarketAnalysisResult',
      citations: [],
      citation_count: 0,
      degraded: false,
      warnings: []
    }
  } as TaskOutputPayload
};

// === Task State Event (用于测试失败状态) ===
export const taskStateFailedEvent: RunEvent = {
  event_id: 'task-state-failed-1',
  run_id: 'run-1',
  timestamp: new Date().toISOString(),
  event_type: 'task_state',
  severity: 'error',
  agent_name: 'Market Data Researcher',  // 顶层 agent_name
  task_id: 'task-1',
  payload: {
    status: 'failed',
    error: 'Connection timeout to MCP server',
    total_duration_ms: 30000
  }
};

export const taskStateCompletedEvent: RunEvent = {
  event_id: 'task-state-completed-1',
  run_id: 'run-1',
  timestamp: new Date().toISOString(),
  event_type: 'task_state',
  severity: 'info',
  agent_name: 'Market Data Researcher',  // 顶层 agent_name
  task_id: 'task-1',
  payload: {
    status: 'completed',
    total_duration_ms: 5000
  }
};

// === Helper to build RunEvent ===
// 注意: 默认 payload 不包含 agent_name，避免误导实现依赖 payload
export function createRunEvent(overrides: Partial<RunEvent>): RunEvent {
  return {
    event_id: `evt-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    run_id: 'run-1',
    timestamp: new Date().toISOString(),
    event_type: 'activity',
    severity: 'info',
    payload: {},  // 默认空 payload，不含 agent_name
    ...overrides
  } as RunEvent;
}

// === 测试用: 只有顶层 agent_name 的 task_output 事件 ===
// 用于验证实现不依赖 payload.agent_name
export const taskOutputWithTopLevelAgentOnly: RunEvent = {
  event_id: 'task-output-top-level-only',
  run_id: 'run-1',
  timestamp: new Date().toISOString(),
  event_type: 'task_output',
  severity: 'info',
  agent_name: 'Technical Analyst',  // 只有顶层 agent_name
  task_id: 'task-2',
  payload: {
    // payload 内没有 agent_name
    summary: {
      raw_preview: 'Technical analysis complete...',
      validation_passed: true
    },
    artifact_ref: {
      job_id: 'job-123',
      task_id: 'task-2'
    },
    diagnostics: {
      output_mode: 'raw',
      citations: [],
      citation_count: 0,
      degraded: false,
      warnings: []
    }
  } as TaskOutputPayload
};

// === 多 Agent 场景测试数据 ===
export const multiAgentEvents: RunEvent[] = [
  createRunEvent({
    event_id: 'evt-1',
    timestamp: '2025-01-09T10:00:00Z',
    event_type: 'tool_call',
    agent_name: 'Market Data Researcher',
    payload: { tool_name: 'mcp_yfinance_stock_info', status: 'pending', input_data: { symbol: 'AAPL' } }
  }),
  createRunEvent({
    event_id: 'evt-2',
    timestamp: '2025-01-09T10:00:01Z',
    event_type: 'tool_result',
    agent_name: 'Market Data Researcher',
    payload: { tool_name: 'mcp_yfinance_stock_info', status: 'success', output_data: '{}', duration_ms: 500 }
  }),
  createRunEvent({
    event_id: 'evt-3',
    timestamp: '2025-01-09T10:00:02Z',
    event_type: 'tool_call',
    agent_name: 'Technical Analyst',
    payload: { tool_name: 'calculate_rsi', status: 'pending', input_data: { period: 14 } }
  }),
  createRunEvent({
    event_id: 'evt-4',
    timestamp: '2025-01-09T10:00:03Z',
    event_type: 'tool_result',
    agent_name: 'Technical Analyst',
    payload: { tool_name: 'calculate_rsi', status: 'success', output_data: '{"rsi": 65.5}', duration_ms: 200 }
  }),
  {
    ...taskOutputWithTopLevelAgentOnly,
    event_id: 'evt-5',
    timestamp: '2025-01-09T10:00:04Z'
  }
];
