import { describe, it, expect } from 'vitest';
import { deriveAgentStates } from '../agentState';
import {
  marketAgentEvents,
  agentOutputEvent,
  createRunEvent,
  taskOutputWithTopLevelAgentOnly,
  taskStateFailedEvent,
  taskStateCompletedEvent,
  multiAgentEvents
} from './fixtures';

describe('AgentState Aggregation', () => {
  describe('Basic Status Derivation', () => {
    it('should derive running status from tool calls with top-level agent_name', () => {
      // 使用顶层 agent_name (真实结构)
      const events = [
        createRunEvent({
          event_type: 'tool_call',
          agent_name: 'Market Analyst',  // 顶层 agent_name
          payload: { tool_name: 'mcp_yfinance_stock_history', status: 'pending' }
        })
      ];

      const result = deriveAgentStates(events);

      expect(result.agents.length).toBe(1);
      expect(result.agents[0].status).toBe('running');
      expect(result.agents[0].currentActionLabel).toContain('mcp_yfinance_stock_history');
      expect(result.activeAgentName).toBe('Market Analyst');
    });

    it('should fallback to payload.agent_name when top-level is missing', () => {
      // 测试 fallback 逻辑 (向后兼容)
      const events = [
        createRunEvent({
          event_type: 'tool_call',
          payload: { agent_name: 'Legacy Agent', tool_name: 'old_tool' }
        })
      ];

      const result = deriveAgentStates(events);

      expect(result.agents.length).toBe(1);
      expect(result.agents[0].agentName).toBe('Legacy Agent');
      expect(result.agents[0].status).toBe('running');
    });

    it('should derive done status from task_output with top-level agent_name', () => {
      const events = [agentOutputEvent];

      const result = deriveAgentStates(events);

      expect(result.agents.length).toBe(1);
      expect(result.agents[0].agentName).toBe('Market Data Researcher');
      expect(result.agents[0].status).toBe('done');
      expect(result.agents[0].currentActionLabel).toBe('Completed');
    });

    // P0 关键测试: task_output 只有顶层 agent_name 也能判定 done
    it('should derive done status from task_output with ONLY top-level agent_name (no payload.agent_name)', () => {
      const events = [taskOutputWithTopLevelAgentOnly];

      const result = deriveAgentStates(events);

      expect(result.agents.length).toBe(1);
      expect(result.agents[0].agentName).toBe('Technical Analyst');
      expect(result.agents[0].status).toBe('done');
      expect(result.agents[0].currentActionLabel).toBe('Completed');
    });
  });

  describe('Failed Status Detection', () => {
    it('should derive failed status from task_state with status=failed', () => {
      const events = [taskStateFailedEvent];

      const result = deriveAgentStates(events);

      expect(result.agents.length).toBe(1);
      expect(result.agents[0].status).toBe('failed');
      expect(result.agents[0].currentActionLabel).toContain('Connection timeout');
    });

    it('should derive done status from task_state with status=completed', () => {
      const events = [taskStateCompletedEvent];

      const result = deriveAgentStates(events);

      expect(result.agents.length).toBe(1);
      expect(result.agents[0].status).toBe('done');
    });

    it('should mark agent as failed on error severity event', () => {
      const events = [
        createRunEvent({
          event_type: 'tool_call',
          agent_name: 'Failing Agent',
          payload: { tool_name: 'risky_tool' }
        }),
        createRunEvent({
          event_type: 'tool_result',
          severity: 'error',
          agent_name: 'Failing Agent',
          payload: { tool_name: 'risky_tool', status: 'failed', message: 'API Error' }
        })
      ];

      const result = deriveAgentStates(events);

      expect(result.agents.length).toBe(1);
      expect(result.agents[0].status).toBe('failed');
    });
  });

  describe('Tool Result Duration', () => {
    it('should extract duration_ms from tool_result payload', () => {
      const events = [
        createRunEvent({
          event_type: 'tool_result',
          agent_name: 'Test Agent',
          payload: {
            tool_name: 'test_tool',
            status: 'success',
            duration_ms: 1500  // 真实字段名
          }
        })
      ];

      const result = deriveAgentStates(events);

      expect(result.agents[0].lastToolDurationMs).toBe(1500);
    });
  });

  describe('Multi-Agent Scenarios', () => {
    it('should handle multi-agent scenarios with top-level agent_name', () => {
      const events = [
        createRunEvent({
          event_id: 'evt-1',
          timestamp: '2025-01-09T10:00:00Z',
          event_type: 'tool_call',
          agent_name: 'Agent A',  // 顶层
          payload: { tool_name: 'search' }
        }),
        createRunEvent({
          event_id: 'evt-2',
          timestamp: '2025-01-09T10:00:01Z',
          event_type: 'tool_call',
          agent_name: 'Agent B',  // 顶层
          payload: { tool_name: 'analyze' }
        })
      ];

      const result = deriveAgentStates(events);

      expect(result.agents.length).toBe(2);
      expect(result.activeAgentName).toBe('Agent B'); // Most recent
    });

    it('should correctly track multiple agents through full workflow', () => {
      const result = deriveAgentStates(multiAgentEvents);

      expect(result.agents.length).toBe(2);

      // Market Data Researcher should be running (no task_output yet in multiAgentEvents for this agent)
      const marketResearcher = result.agents.find(a => a.agentName === 'Market Data Researcher');
      expect(marketResearcher?.status).toBe('running');

      // Technical Analyst should be done (has task_output)
      const technicalAnalyst = result.agents.find(a => a.agentName === 'Technical Analyst');
      expect(technicalAnalyst?.status).toBe('done');
    });

    it('should sort agents by lastSeenAt descending', () => {
      const events = [
        createRunEvent({
          timestamp: '2025-01-09T10:00:00Z',
          event_type: 'tool_call',
          agent_name: 'First Agent',
          payload: { tool_name: 'tool1' }
        }),
        createRunEvent({
          timestamp: '2025-01-09T10:00:05Z',
          event_type: 'tool_call',
          agent_name: 'Second Agent',
          payload: { tool_name: 'tool2' }
        }),
        createRunEvent({
          timestamp: '2025-01-09T10:00:02Z',
          event_type: 'tool_call',
          agent_name: 'Middle Agent',
          payload: { tool_name: 'tool3' }
        })
      ];

      const result = deriveAgentStates(events);

      // Should be sorted by lastSeenAt desc
      expect(result.agents[0].agentName).toBe('Second Agent');
      expect(result.agents[1].agentName).toBe('Middle Agent');
      expect(result.agents[2].agentName).toBe('First Agent');
    });
  });

  describe('System Agent Filtering', () => {
    it('should exclude System from agent list', () => {
      const events = [
        createRunEvent({
          event_type: 'activity',
          agent_name: 'System',
          payload: { activity_type: 'phase', message: 'Starting...' }
        }),
        createRunEvent({
          event_type: 'tool_call',
          agent_name: 'Real Agent',
          payload: { tool_name: 'tool1' }
        })
      ];

      const result = deriveAgentStates(events);

      expect(result.agents.length).toBe(1);
      expect(result.agents[0].agentName).toBe('Real Agent');
    });
  });

  describe('Manifest Integration', () => {
    it('should add idle agents from manifest', () => {
      const events = [
        createRunEvent({
          event_type: 'tool_call',
          agent_name: 'Active Agent',
          payload: { tool_name: 'tool1' }
        })
      ];

      const manifest = {
        agents: [
          { name: 'Active Agent', role: 'Worker' },
          { name: 'Idle Agent', role: 'Backup' }
        ]
      };

      const result = deriveAgentStates(events, manifest);

      expect(result.agents.length).toBe(2);

      const idleAgent = result.agents.find(a => a.agentName === 'Idle Agent');
      expect(idleAgent?.status).toBe('idle');
      expect(idleAgent?.currentActionLabel).toBe('Waiting');
    });
  });
});
