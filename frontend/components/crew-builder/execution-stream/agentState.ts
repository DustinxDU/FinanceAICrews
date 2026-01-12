import { RunEvent } from '@/lib/types';

export type AgentStatus = 'idle' | 'running' | 'done' | 'failed';

export interface AgentState {
  agentName: string;
  status: AgentStatus;
  currentTaskName?: string;
  currentActionLabel: string;  // "Calling mcp_yfinance_stock_history" / "Waiting LLM" / "Processing result"
  lastToolName?: string;
  lastToolDurationMs?: number;
  lastSeenAt: string;
}

export interface AgentStatesResult {
  agents: AgentState[];
  activeAgentName: string | null;
}

/**
 * 从 RunEvent 中提取 agent 名称
 * 优先使用顶层 agent_name，fallback 到 payload.agent_name
 * 将 "Unknown Agent" 统一显示为 "Reporter"（End 节点的隐式 Reporter Agent）
 */
function getAgentName(event: RunEvent): string | undefined {
  const rawName = event.agent_name ?? (event.payload as any)?.agent_name;
  // 将后端的 "Unknown Agent" fallback 统一为 "Reporter"
  if (rawName === 'Unknown Agent') {
    return 'Reporter';
  }
  return rawName;
}

/**
 * 从事件流聚合 agent 状态
 * @param events - 完整事件流
 * @param manifest - 可选的 run manifest (Phase 2)
 */
export function deriveAgentStates(
  events: RunEvent[],
  manifest?: { agents: Array<{ name: string; role: string }> }
): AgentStatesResult {
  const agentMap = new Map<string, AgentState>();
  let activeAgentName: string | null = null;

  events.forEach(event => {
    const agentName = getAgentName(event);

    // 更新 agent 状态: tool_call
    if (event.event_type === 'tool_call' && agentName) {
      const now = event.timestamp;
      const payload = event.payload as any;

      const existing = agentMap.get(agentName) || {
        agentName,
        status: 'idle' as AgentStatus,
        currentActionLabel: '',
        lastSeenAt: now
      };

      // 状态更新
      agentMap.set(agentName, {
        ...existing,
        status: 'running',
        currentActionLabel: `Calling ${payload?.tool_name || 'unknown'}`,
        lastToolName: payload?.tool_name,
        lastSeenAt: now
      });

      activeAgentName = agentName;
    }

    // 更新 agent 状态: tool_result
    if (event.event_type === 'tool_result' && agentName) {
      const now = event.timestamp;
      const payload = event.payload as any;

      const existing = agentMap.get(agentName) || {
        agentName,
        status: 'idle' as AgentStatus,
        currentActionLabel: '',
        lastSeenAt: now
      };

      agentMap.set(agentName, {
        ...existing,
        status: 'running', // 仍在运行，可能还有后续任务
        currentActionLabel: 'Processing result',
        lastToolName: payload?.tool_name,
        // 真实字段: payload.duration_ms (不是 payload.duration)
        lastToolDurationMs: payload?.duration_ms,
        lastSeenAt: now
      });

      activeAgentName = agentName;
    }

    // 更新 agent 状态: task_output (agent 完成任务)
    if (event.event_type === 'task_output' && agentName) {
      const now = event.timestamp;

      const existing = agentMap.get(agentName) || {
        agentName,
        status: 'idle' as AgentStatus,
        currentActionLabel: '',
        lastSeenAt: now
      };

      agentMap.set(agentName, {
        ...existing,
        status: 'done',
        currentActionLabel: 'Completed',
        lastSeenAt: now
      });

      // 最后看到的 agent 仍然是 active
      activeAgentName = agentName;
    }

    // 更新 agent 状态: task_state (检测失败状态)
    if (event.event_type === 'task_state' && agentName) {
      const now = event.timestamp;
      const payload = event.payload as any;

      const existing = agentMap.get(agentName) || {
        agentName,
        status: 'idle' as AgentStatus,
        currentActionLabel: '',
        lastSeenAt: now
      };

      // 如果是 failed 状态，标记 agent 失败
      if (payload?.status === 'failed') {
        agentMap.set(agentName, {
          ...existing,
          status: 'failed',
          currentActionLabel: payload?.error || 'Failed',
          lastSeenAt: now
        });
      } else if (payload?.status === 'completed' && existing.status !== 'done') {
        // task_state completed 也可以标记为 done
        agentMap.set(agentName, {
          ...existing,
          status: 'done',
          currentActionLabel: 'Completed',
          lastSeenAt: now
        });
      }

      activeAgentName = agentName;
    }

    // 检测 error severity 也标记 agent 失败
    // 注意: 跳过 task_state 事件，因为它们已经在上面处理过了
    if (event.severity === 'error' && agentName && event.event_type !== 'task_state') {
      const now = event.timestamp;
      const existing = agentMap.get(agentName);
      if (existing && existing.status !== 'done') {
        agentMap.set(agentName, {
          ...existing,
          status: 'failed',
          currentActionLabel: (event.payload as any)?.message || (event.payload as any)?.error || 'Error',
          lastSeenAt: now
        });
      }
    }

    // activity 事件也可以用来追踪 agent（如果有 agent_name）
    if (event.event_type === 'activity' && agentName && agentName !== 'System') {
      const now = event.timestamp;
      const payload = event.payload as any;

      if (!agentMap.has(agentName)) {
        agentMap.set(agentName, {
          agentName,
          status: 'running',
          currentActionLabel: payload?.message || 'Working',
          lastSeenAt: now
        });
        activeAgentName = agentName;
      }
    }
  });

  // 添加尚未有事件的 idle agents
  if (manifest) {
    manifest.agents.forEach(a => {
      if (!agentMap.has(a.name)) {
        agentMap.set(a.name, {
          agentName: a.name,
          status: 'idle',
          currentActionLabel: 'Waiting',
          lastSeenAt: ''
        });
      }
    });
  }

  // System 不是 agent
  agentMap.delete('System');

  // 按 lastSeenAt 降序排序，避免 UI 抖动
  const sortedAgents = Array.from(agentMap.values()).sort((a, b) => {
    if (!a.lastSeenAt && !b.lastSeenAt) return 0;
    if (!a.lastSeenAt) return 1;  // 未 seen 的放底部
    if (!b.lastSeenAt) return -1;
    return new Date(b.lastSeenAt).getTime() - new Date(a.lastSeenAt).getTime();
  });

  // 优先选择 status === 'running' 的 agent 作为 activeAgentName
  // 避免 Follow Active 跟到已完成的 agent
  const runningAgent = sortedAgents.find(a => a.status === 'running');
  const finalActiveAgent = runningAgent?.agentName ?? activeAgentName;

  return {
    agents: sortedAgents,
    activeAgentName: finalActiveAgent
  };
}
