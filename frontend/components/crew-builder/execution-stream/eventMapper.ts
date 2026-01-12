/**
 * Event Mapper Utility
 *
 * Maps backend RunEvent types to visual card types for the execution stream display.
 * Provides type guards and helper functions for processing events.
 */

import {
  RunEvent,
  RunEventType,
  ActivityPayload,
  ToolCallPayload,
  LLMCallPayload,
  TaskOutputPayload,
  TaskStatePayload
} from '@/lib/types';
import {
  ThoughtCard,
  ToolCallCard,
  ObservationCard,
  LLMCallCard,
  AgentOutputCard,
  StatusCard,
  SystemCard,
} from './cards';

export type CardType =
  | 'thought'       // Agent thinking/planning (from ACTIVITY)
  | 'tool_call'     // Tool invocation (from TOOL_CALL)
  | 'tool_result'   // Tool output (from TOOL_RESULT)
  | 'llm_call'      // LLM interaction (from LLM_CALL)
  | 'agent_output'  // Agent task completion (from TASK_OUTPUT)
  | 'status'        // Job state changes (from TASK_STATE)
  | 'system';       // System messages (from SYSTEM)

export interface MappedEvent {
  id: string;
  type: CardType;
  timestamp: string;
  agentName?: string;
  taskId?: string;
  severity: 'debug' | 'info' | 'warning' | 'error';
  content: EventContent;
}

export type EventContent =
  | ThoughtContent
  | ToolCallContent
  | ToolResultContent
  | LLMCallContent
  | AgentOutputContent
  | StatusContent
  | SystemContent;

export interface ThoughtContent {
  type: 'thought';
  activityType: string;
  message: string;
  details?: Record<string, any>;
}

export interface ToolCallContent {
  type: 'tool_call';
  toolName: string;
  status: string;
  input?: Record<string, any>;
}

export interface ToolResultContent {
  type: 'tool_result';
  toolName: string;
  status: string;
  output?: any;
  durationMs?: number;
  error?: string;
}

export interface LLMCallContent {
  type: 'llm_call';
  provider: string;
  model: string;
  status: string;
  tokens?: {
    prompt: number;
    completion: number;
    total: number;
  };
  durationMs?: number;
  promptPreview?: string;
  responsePreview?: string;
  error?: string;
}

export interface AgentOutputContent {
  type: 'agent_output';
  rawPreview: string;
  validationPassed: boolean;
  outputMode: string;
  schemaKey?: string;
  citationCount: number;
  isDegraded: boolean;
  warnings: string[];
  pydanticDump?: Record<string, any>;
}

export interface StatusContent {
  type: 'status';
  status: 'completed' | 'failed';
  error?: string;
  durationMs?: number;
}

export interface SystemContent {
  type: 'system';
  message: string;
}

export interface ChartableData {
  type: 'line' | 'bar' | 'pie' | 'multi-bar';
  data: any[];
  title?: string;
  series?: string[]; // For multi-series charts
}

export interface StructuredData {
  type: 'news' | 'quote' | 'income_statement' | 'balance_sheet' | 'cashflow' | 'stock_info';
  data: any;
  title?: string;
}

// Key financial metrics to extract from statements
const INCOME_METRICS = ['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income', 'EBITDA'];
const BALANCE_METRICS = ['Total Assets', 'Total Liabilities', 'Total Equity', 'Cash And Cash Equivalents'];
const CASHFLOW_METRICS = ['Operating Cash Flow', 'Free Cash Flow', 'Capital Expenditure'];

function formatLargeNumber(num: number): string {
  if (Math.abs(num) >= 1e12) return (num / 1e12).toFixed(1) + 'T';
  if (Math.abs(num) >= 1e9) return (num / 1e9).toFixed(1) + 'B';
  if (Math.abs(num) >= 1e6) return (num / 1e6).toFixed(1) + 'M';
  if (Math.abs(num) >= 1e3) return (num / 1e3).toFixed(1) + 'K';
  return num.toFixed(0);
}

export function detectChartableData(payload: any): ChartableData | null {
  if (!payload) return null;

  // Handle JSON string input - try to parse it
  let data = payload;
  if (typeof payload === 'string') {
    try {
      data = JSON.parse(payload);
    } catch {
      return null; // Not valid JSON
    }
  }

  if (typeof data !== 'object') return null;

  // Reassign payload to parsed data for rest of function
  payload = data;

  // Pattern 1: Price history array
  // Looks for array of objects with value/close/price and optional timestamp/date
  if (Array.isArray(payload.prices) || Array.isArray(payload.history)) {
    const arr = payload.prices || payload.history;
    if (arr.length > 0) {
      const data = arr.map((item: any) => ({
        value: typeof item === 'number' ? item : (item.close || item.price || item.value),
        timestamp: item.date || item.timestamp || item.time
      }));
      return {
        type: 'line',
        data,
        title: 'Price Trend'
      };
    }
  }

  // Pattern 2: Indicator values object
  // Looks for "indicators" object with numeric values
  if (payload.indicators && typeof payload.indicators === 'object') {
    return {
      type: 'bar',
      data: Object.entries(payload.indicators)
        .filter(([_, v]) => typeof v === 'number')
        .map(([k, v]) => ({ name: k, value: v as number })),
      title: 'Indicators'
    };
  }

  // Pattern 3: Distribution/allocation data
  // Looks for "allocation" or "distribution" object
  if (payload.allocation || payload.distribution) {
    const obj = payload.allocation || payload.distribution;
    return {
      type: 'pie',
      data: Object.entries(obj)
        .filter(([_, v]) => typeof v === 'number')
        .map(([k, v]) => ({ name: k, value: v as number })),
      title: 'Distribution'
    };
  }

  // Pattern 4: Financial statement data (income, balance sheet, cash flow)
  // Format: { data: [...], columns: [...], statement_type?: string, symbol?: string }
  if (Array.isArray(payload.data) && Array.isArray(payload.columns) && payload.data.length > 0) {
    // Pattern 4a: OHLCV Stock History (has period, interval, symbol, and Close/Open columns)
    // Check for both 'Close' and 'close' (case-insensitive)
    const hasCloseColumn = payload.columns.some((c: string) => c.toLowerCase() === 'close');
    if (payload.period && payload.interval && payload.symbol && hasCloseColumn) {
      // Use a simpler date parsing that handles timezone format
      const parseDate = (dateStr: string): Date => {
        // Handle "2025-12-09 00:00:00+08:00" format
        const match = dateStr.match(/^(\d{4}-\d{2}-\d{2})/);
        if (match) {
          return new Date(match[1]);
        }
        return new Date(dateStr);
      };

      const sortedData = [...payload.data]
        // Find the close column key (could be 'Close' or 'close')
        .filter((row: any) => {
          const closeKey = Object.keys(row).find(k => k.toLowerCase() === 'close');
          return closeKey && typeof row[closeKey] === 'number';
        })
        .sort((a: any, b: any) => parseDate(a.Date || 0).getTime() - parseDate(b.Date || 0).getTime());

      if (sortedData.length > 0) {
        const chartData = sortedData.map((row: any) => {
          const closeKey = Object.keys(row).find(k => k.toLowerCase() === 'close') || 'Close';
          return {
            name: row.Date ? parseDate(row.Date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '',
            value: row[closeKey],
            _formatted: row[closeKey]?.toFixed(2)
          };
        });

        return {
          type: 'line',
          data: chartData,
          title: `${payload.symbol} Price (${payload.period})`
        };
      }
    }

    // Pattern 4b: Financial Statement Data (income, balance sheet, cash flow)
    const statementType = payload.statement_type || 'financial';
    const symbol = payload.symbol || '';

    // Determine which metrics to extract based on statement type
    let metricsToExtract: string[] = [];
    if (statementType === 'income') {
      metricsToExtract = INCOME_METRICS;
    } else if (statementType === 'balance' || statementType === 'balance_sheet') {
      metricsToExtract = BALANCE_METRICS;
    } else if (statementType === 'cash_flow' || statementType === 'cashflow') {
      metricsToExtract = CASHFLOW_METRICS;
    } else {
      // Try to auto-detect based on available columns
      const cols = new Set(payload.columns);
      if (cols.has('Total Revenue') || cols.has('Net Income')) {
        metricsToExtract = INCOME_METRICS;
      } else if (cols.has('Total Assets')) {
        metricsToExtract = BALANCE_METRICS;
      } else if (cols.has('Operating Cash Flow')) {
        metricsToExtract = CASHFLOW_METRICS;
      }
    }

    // Filter to only metrics that exist in the data
    const availableCols = new Set(payload.columns);
    const validMetrics = metricsToExtract.filter(m => availableCols.has(m));

    if (validMetrics.length > 0) {
      // Sort data by date (newest first) and take last 4 years
      const sortedData = [...payload.data]
        .filter((row: any) => row.Date && validMetrics.some(m => typeof row[m] === 'number' && !isNaN(row[m])))
        .sort((a: any, b: any) => new Date(b.Date).getTime() - new Date(a.Date).getTime())
        .slice(0, 4)
        .reverse(); // Oldest to newest for chart

      if (sortedData.length > 0) {
        // Transform to chart format: [{ name: '2023', metric1: value, metric2: value, ... }]
        const chartData = sortedData.map((row: any) => {
          const year = new Date(row.Date).getFullYear().toString();
          const entry: any = { name: year };
          validMetrics.forEach(metric => {
            const value = row[metric];
            if (typeof value === 'number' && !isNaN(value)) {
              // Store raw value for chart, formatted value for tooltip
              entry[metric] = value / 1e9; // Convert to billions for readability
              entry[`${metric}_formatted`] = formatLargeNumber(value);
            }
          });
          return entry;
        });

        const titleMap: Record<string, string> = {
          'income': 'Income Statement',
          'balance': 'Balance Sheet',
          'balance_sheet': 'Balance Sheet',
          'cash_flow': 'Cash Flow',
          'cashflow': 'Cash Flow',
        };

        return {
          type: 'multi-bar',
          data: chartData,
          series: validMetrics,
          title: `${symbol ? symbol + ' ' : ''}${titleMap[statementType] || 'Financial Data'} (Billions USD)`
        };
      }
    }
  }

  return null;
}

/**
 * Detect structured data types (news, quote, etc.) from tool output
 */
export function detectStructuredData(payload: any): StructuredData | null {
  if (!payload || typeof payload !== 'object') return null;

  // Handle JSON string input
  let data = payload;
  if (typeof payload === 'string') {
    try {
      data = JSON.parse(payload);
    } catch {
      return null;
    }
  }

  if (typeof data !== 'object') return null;

  // Pattern 1: News data (has news array with title, summary, provider)
  if (Array.isArray(data.news) && data.news.length > 0) {
    const news = data.news;
    const displayNews = news.slice(0, 5).map((item: any) => ({
      title: item.content?.title || item.title || 'No title',
      summary: item.content?.summary || item.summary || '',
      provider: item.provider?.displayName || item.provider || '',
      pubDate: item.content?.pubDate || item.pubDate || '',
    }));

    return {
      type: 'news',
      data: {
        symbol: data.symbol,
        news: displayNews,
        totalCount: news.length,
      },
      title: `${data.symbol || ''} News`,
    };
  }

  // Pattern 2: Stock quote data (has price, change, symbol)
  if (typeof data.price === 'number' && typeof data.change === 'number' && data.symbol) {
    const isPositive = data.change >= 0;
    return {
      type: 'quote',
      data: {
        symbol: data.symbol,
        price: data.price,
        change: data.change,
        changePercent: data.change_percent || data.change_percent || (data.change / (data.price - data.change)) * 100,
        volume: data.volume,
        marketCap: data.market_cap,
        previousClose: data.previous_close,
        open: data.open,
        dayHigh: data.day_high,
        dayLow: data.day_low,
      },
      title: `${data.symbol} Quote`,
    };
  }

  // Pattern 3: Stock info (has symbol and company profile data)
  if (data.symbol && (data.company_name || data.sector || data.industry)) {
    return {
      type: 'stock_info',
      data: {
        symbol: data.symbol,
        companyName: data.company_name || data.name,
        sector: data.sector,
        industry: data.industry,
        marketCap: data.market_cap || data.marketCap,
        peRatio: data.pe_ratio || data.peRatio,
        eps: data.eps,
        dividend: data.dividend,
        beta: data.beta,
      },
      title: `${data.symbol} Company Info`,
    };
  }

  return null;
}

/**
 * Maps a RunEvent to a MappedEvent for display
 */
export function mapEvent(event: RunEvent): MappedEvent | null {
  const base = {
    id: event.event_id,
    timestamp: event.timestamp,
    agentName: event.agent_name,
    taskId: event.task_id,
    severity: event.severity,
  };

  switch (event.event_type) {
    case 'activity':
      return {
        ...base,
        type: 'thought',
        content: mapActivityPayload(event.payload as ActivityPayload),
      };

    case 'tool_call':
      return {
        ...base,
        type: 'tool_call',
        content: mapToolCallPayload(event.payload as ToolCallPayload),
      };

    case 'tool_result':
      return {
        ...base,
        type: 'tool_result',
        content: mapToolResultPayload(event.payload as ToolCallPayload),
      };

    case 'llm_call':
      return {
        ...base,
        type: 'llm_call',
        content: mapLLMCallPayload(event.payload as LLMCallPayload),
      };

    case 'task_output':
      return {
        ...base,
        type: 'agent_output',
        content: mapTaskOutputPayload(event.payload as TaskOutputPayload),
      };

    case 'task_state':
      return {
        ...base,
        type: 'status',
        content: mapTaskStatePayload(event.payload as TaskStatePayload),
      };

    case 'system':
      return {
        ...base,
        type: 'system',
        content: {
          type: 'system',
          message: event.payload?.message || 'System event',
        },
      };

    default:
      return null;
  }
}

function mapActivityPayload(payload: ActivityPayload): ThoughtContent {
  return {
    type: 'thought',
    activityType: payload.activity_type || 'thinking',
    message: payload.message || '',
    details: payload.details,
  };
}

function mapToolCallPayload(payload: ToolCallPayload): ToolCallContent {
  return {
    type: 'tool_call',
    toolName: payload.tool_name || 'Unknown Tool',
    status: payload.status || 'pending',
    input: payload.input_data,
  };
}

function mapToolResultPayload(payload: ToolCallPayload): ToolResultContent {
  return {
    type: 'tool_result',
    toolName: payload.tool_name || 'Unknown Tool',
    status: payload.status || 'success',
    output: payload.output_data,
    durationMs: payload.duration_ms,
    error: payload.error_message,
  };
}

function mapLLMCallPayload(payload: LLMCallPayload): LLMCallContent {
  return {
    type: 'llm_call',
    provider: payload.llm_provider || 'Unknown',
    model: payload.model_name || 'Unknown',
    status: payload.status || 'pending',
    tokens: payload.total_tokens ? {
      prompt: payload.prompt_tokens || 0,
      completion: payload.completion_tokens || 0,
      total: payload.total_tokens,
    } : undefined,
    durationMs: payload.duration_ms,
    promptPreview: payload.prompt_preview,
    responsePreview: payload.response_preview,
    error: payload.error_message,
  };
}

function mapTaskOutputPayload(payload: TaskOutputPayload): AgentOutputContent {
  const summary = payload.summary || {};
  const diagnostics = payload.diagnostics || {};

  return {
    type: 'agent_output',
    rawPreview: summary.raw_preview || '',
    validationPassed: summary.validation_passed ?? true,
    outputMode: diagnostics.output_mode || 'raw',
    schemaKey: diagnostics.schema_key,
    citationCount: diagnostics.citation_count || 0,
    isDegraded: diagnostics.degraded || false,
    warnings: diagnostics.warnings || [],
    pydanticDump: summary.pydantic_dump,
  };
}

function mapTaskStatePayload(payload: TaskStatePayload): StatusContent {
  return {
    type: 'status',
    status: payload.status || 'completed',
    error: payload.error,
    durationMs: payload.total_duration_ms,
  };
}

/**
 * Filters events for display based on severity and type
 * Updated for Agent-Centric Console (Phase 2/3)
 */
export function filterEventsForDisplay(
  events: RunEvent[],
  options: {
    // Legacy options (kept for backward compat if needed, but new UI uses viewMode)
    showDebug?: boolean;
    hideLLMCalls?: boolean;
    // New options
    hidePhaseEvents?: boolean;     // 默认 true
    selectedAgentName?: string | null;
    eventTypes?: string[];
  } = {}
): RunEvent[] {
  const { 
    hidePhaseEvents = true, 
    selectedAgentName, 
    eventTypes,
    showDebug = false,
    hideLLMCalls = false
  } = options;

  let filtered = [...events];

  // 0. Base filters (Legacy)
  filtered = filtered.filter(event => {
    if (!showDebug && event.severity === 'debug') return false;
    if (hideLLMCalls && event.event_type === 'llm_call') return false;
    return true;
  });

  // 1. 过滤 phase events（agent-centric 模式下）
  if (hidePhaseEvents) {
    filtered = filtered.filter(
      e => !(e.event_type === 'activity' && (e.payload as any)?.activity_type === 'phase')
    );
  }

  // 2. 按 agent 过滤（如果选择了特定 agent）
  // 重要: 优先使用顶层 event.agent_name，fallback 到 payload.agent_name
  if (selectedAgentName) {
    filtered = filtered.filter(e => {
      // 获取 agent 名称: 优先顶层，fallback payload
      const eventAgentName = e.agent_name ?? (e.payload as any)?.agent_name;

      // tool_call/tool_result: 检查 agent_name
      if (e.event_type === 'tool_call' || e.event_type === 'tool_result') {
        return eventAgentName === selectedAgentName;
      }
      // task_output: 检查 agent_name (真实 payload 不一定含 agent_name，用顶层)
      if (e.event_type === 'task_output') {
        return eventAgentName === selectedAgentName;
      }
      // task_state: 也需要按 agent 过滤
      if (e.event_type === 'task_state') {
        return eventAgentName === selectedAgentName;
      }
      // activity 事件: 如果有 agent_name 则过滤
      if (e.event_type === 'activity' && eventAgentName) {
         return eventAgentName === selectedAgentName || eventAgentName === 'System';
      }
      // system 事件不过滤
      return true;
    });
  }

  // 3. 按事件类型过滤（clean mode 只显示工具相关）
  if (eventTypes && eventTypes.length > 0) {
    filtered = filtered.filter(e => eventTypes.includes(e.event_type));
  }

  return filtered;
}

export interface AgentGroup {
  agentName: string;
  events: MappedEvent[];
  status: 'idle' | 'active' | 'completed' | 'failed';
  startTime?: string;
  endTime?: string;
  eventCount: number;
}

/**
 * Groups consecutive events by agent for visual grouping
 */
export function groupEventsByAgent(events: MappedEvent[]): AgentGroup[] {
  const groups = new Map<string, MappedEvent[]>();

  // 1. Group events by agent
  for (const event of events) {
    const key = event.agentName || 'System';
    const existing = groups.get(key) || [];
    existing.push(event);
    groups.set(key, existing);
  }

  // 2. Convert to array with metadata
  return Array.from(groups.entries()).map(([name, agentEvents]) => {
    // Infer status
    const hasTaskOutput = agentEvents.some(e => e.type === 'agent_output');
    const hasError = agentEvents.some(e => e.severity === 'error');
    
    // Check if this is the active agent (has most recent event)
    const lastEvent = events[events.length - 1];
    const isActive = lastEvent && lastEvent.agentName === name && !hasTaskOutput;

    let status: 'idle' | 'active' | 'completed' | 'failed' = 'idle';
    if (hasError) status = 'failed';
    else if (hasTaskOutput) status = 'completed';
    else if (isActive) status = 'active';

    return {
      agentName: name,
      events: agentEvents,
      status,
      startTime: agentEvents[0]?.timestamp,
      endTime: agentEvents[agentEvents.length - 1]?.timestamp,
      eventCount: agentEvents.length,
    };
  });
}

export interface ProgressInfo {
  percentage: number;
  completedAgents: number;
  totalAgents: number;
  currentAgent: string | null;
  status: 'idle' | 'running' | 'completed' | 'failed';
}

export function calculateProgress(events: RunEvent[], summary?: { agent_count?: number }, jobStatus?: string): ProgressInfo {
  // 1. Get unique agents from events (more reliable than summary.agent_count)
  const agentSet = new Set<string>();
  const completedAgents = new Set<string>();
  let currentAgent: string | null = null;

  for (const event of events) {
    if (event.agent_name) {
      agentSet.add(event.agent_name);

      // Track current agent (most recent activity)
      if (event.event_type === 'activity') {
        currentAgent = event.agent_name;
      }

      // Mark agent as completed if they have a task_output
      if (event.event_type === 'task_output') {
        completedAgents.add(event.agent_name);
      }
    }
  }

  const totalAgents = Math.max(agentSet.size, summary?.agent_count || 1, 1);
  const completed = completedAgents.size;

  // 2. Calculate percentage
  let percentage = 0;
  if (jobStatus === 'completed') {
    percentage = 100;
  } else if (jobStatus === 'failed') {
    percentage = (completed / totalAgents) * 100;
  } else if (totalAgents > 0) {
    // Running: add partial progress for current agent
    const baseProgress = (completed / totalAgents) * 100;
    const partialProgress = currentAgent && !completedAgents.has(currentAgent)
      ? (0.5 / totalAgents) * 100  // 50% credit for in-progress agent
      : 0;
    percentage = Math.min(baseProgress + partialProgress, 99); // Cap at 99% until completed
  }

  return {
    percentage: Math.round(percentage),
    completedAgents: completed,
    totalAgents,
    currentAgent,
    status: (jobStatus as any) || 'idle',
  };
}

/**
 * 从事件流中提取当前阶段
 * 优先级: 最新 phase activity message
 */
export function getCurrentStage(events: RunEvent[]): string {
  const phaseEvents = events.filter(
    e => e.event_type === 'activity' &&
        (e.payload as any)?.activity_type === 'phase' &&
        (e.payload as any)?.message
  );

  if (phaseEvents.length > 0) {
    // 返回最新的 phase message
    const latestPhase = phaseEvents[phaseEvents.length - 1];
    return (latestPhase.payload as any).message;
  }

  // 回退: 传统行为 - 尝试从 activity 推导
  const activities = events.filter(e => e.event_type === 'activity');
  const latest = activities[activities.length - 1];
  
  if (latest) {
     const type = (latest.payload as any).activity_type;
     switch (type) {
        case 'thinking': return 'Thinking';
        case 'observation': return 'Observing';
        case 'tool_selection': return 'Selecting Tool';
        case 'delegation': return 'Delegating';
        default: return type || 'Working';
     }
  }

  return 'Thinking'; // Default
}

export interface CardMapping {
  component: React.ComponentType<any>;
  props: any;
}

export function mapEventToCard(event: RunEvent, index: number): CardMapping | null {
  const mapped = mapEvent(event);
  if (!mapped) return null;

  const commonProps = {
    id: mapped.id || `evt-${index}`,
    content: mapped.content,
    agentName: mapped.agentName,
    timestamp: mapped.timestamp
  };

  switch (mapped.type) {
    case 'thought':
      return { component: ThoughtCard, props: commonProps };
    case 'tool_call':
      return { component: ToolCallCard, props: commonProps };
    case 'tool_result':
      return { component: ObservationCard, props: commonProps };
    case 'llm_call':
      return { component: LLMCallCard, props: commonProps };
    case 'agent_output':
      return { component: AgentOutputCard, props: commonProps };
    case 'status':
      return { component: StatusCard, props: commonProps };
    case 'system':
      return { component: SystemCard, props: commonProps };
    default:
      return null;
  }
}

