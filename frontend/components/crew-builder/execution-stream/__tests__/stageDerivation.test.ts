import { describe, it, expect } from 'vitest';
import { getCurrentStage, filterEventsForDisplay } from '../eventMapper';
import {
  phaseEvents,
  marketAgentEvents,
  createRunEvent,
  taskOutputWithTopLevelAgentOnly,
  multiAgentEvents
} from './fixtures';

describe('Stage Derivation', () => {
  describe('getCurrentStage', () => {
    it('should return latest phase message', () => {
      const events = [
        ...phaseEvents,
        createRunEvent({ event_type: 'tool_call' })
      ];

      expect(getCurrentStage(events)).toBe('Assembling crew...');
    });

    it('should fallback to "Thinking" when no phase events', () => {
      const events = [createRunEvent({ event_type: 'tool_call' })];
      expect(getCurrentStage(events)).toBe('Thinking');
    });

    it('should handle empty events array', () => {
      expect(getCurrentStage([])).toBe('Thinking');
    });

    it('should return first phase message when only one phase event', () => {
      const events = [phaseEvents[0]];
      expect(getCurrentStage(events)).toBe('Execution started');
    });
  });

  describe('filterEventsForDisplay', () => {
    it('should hide phase events when hidePhaseEvents=true', () => {
      const events = [...phaseEvents, ...marketAgentEvents];
      const filtered = filterEventsForDisplay(events, { hidePhaseEvents: true });

      expect(filtered.every(e => !((e.payload as any)?.activity_type === 'phase'))).toBe(true);
      expect(filtered.length).toBe(2); // Only tool events
    });

    it('should show phase events when hidePhaseEvents=false', () => {
      const events = [...phaseEvents, ...marketAgentEvents];
      const filtered = filterEventsForDisplay(events, { hidePhaseEvents: false });

      expect(filtered.length).toBe(4); // 2 phase + 2 tool events
    });

    // 使用顶层 agent_name 进行过滤 (关键测试)
    it('should filter by selected agent using top-level agent_name', () => {
      const events = [
        createRunEvent({
          event_type: 'tool_call',
          agent_name: 'Agent A',  // 顶层 agent_name
          payload: { tool_name: 'tool1' }
        }),
        createRunEvent({
          event_type: 'tool_call',
          agent_name: 'Agent B',  // 顶层 agent_name
          payload: { tool_name: 'tool2' }
        })
      ];

      const filtered = filterEventsForDisplay(events, {
        selectedAgentName: 'Agent A'
      });

      expect(filtered.length).toBe(1);
      expect(filtered[0].agent_name).toBe('Agent A');
    });

    // 向后兼容: fallback 到 payload.agent_name
    it('should fallback to payload.agent_name when top-level is missing', () => {
      const events = [
        createRunEvent({
          event_type: 'tool_call',
          payload: { agent_name: 'Legacy Agent A', tool_name: 'tool1' }
        }),
        createRunEvent({
          event_type: 'tool_call',
          payload: { agent_name: 'Legacy Agent B', tool_name: 'tool2' }
        })
      ];

      const filtered = filterEventsForDisplay(events, {
        selectedAgentName: 'Legacy Agent A'
      });

      expect(filtered.length).toBe(1);
      expect((filtered[0].payload as any).agent_name).toBe('Legacy Agent A');
    });

    // task_output 过滤使用顶层 agent_name
    it('should filter task_output by top-level agent_name', () => {
      const events = [
        ...marketAgentEvents,  // Market Data Researcher
        taskOutputWithTopLevelAgentOnly  // Technical Analyst (只有顶层 agent_name)
      ];

      const filtered = filterEventsForDisplay(events, {
        selectedAgentName: 'Technical Analyst'
      });

      // 应该只返回 Technical Analyst 的 task_output
      expect(filtered.length).toBe(1);
      expect(filtered[0].event_type).toBe('task_output');
      expect(filtered[0].agent_name).toBe('Technical Analyst');
    });

    // task_state 过滤
    it('should filter task_state events by agent', () => {
      const events = [
        createRunEvent({
          event_type: 'task_state',
          agent_name: 'Agent A',
          payload: { status: 'completed' }
        }),
        createRunEvent({
          event_type: 'task_state',
          agent_name: 'Agent B',
          payload: { status: 'failed' }
        })
      ];

      const filtered = filterEventsForDisplay(events, {
        selectedAgentName: 'Agent A'
      });

      expect(filtered.length).toBe(1);
      expect(filtered[0].agent_name).toBe('Agent A');
    });

    it('should filter by event types', () => {
      const events = [
        ...phaseEvents,
        ...marketAgentEvents,
        taskOutputWithTopLevelAgentOnly
      ];

      const filtered = filterEventsForDisplay(events, {
        hidePhaseEvents: false,
        eventTypes: ['tool_call', 'tool_result']
      });

      expect(filtered.every(e => ['tool_call', 'tool_result'].includes(e.event_type))).toBe(true);
      expect(filtered.length).toBe(2);
    });

    it('should combine hidePhaseEvents, selectedAgentName, and eventTypes filters', () => {
      const events = [
        ...phaseEvents,
        ...multiAgentEvents
      ];

      const filtered = filterEventsForDisplay(events, {
        hidePhaseEvents: true,
        selectedAgentName: 'Market Data Researcher',
        eventTypes: ['tool_call', 'tool_result']
      });

      // Should only have Market Data Researcher's tool events
      expect(filtered.every(e => e.agent_name === 'Market Data Researcher')).toBe(true);
      expect(filtered.every(e => ['tool_call', 'tool_result'].includes(e.event_type))).toBe(true);
    });

    it('should allow System activity events through when filtering by agent', () => {
      const events = [
        createRunEvent({
          event_type: 'activity',
          agent_name: 'System',
          payload: { activity_type: 'info', message: 'System message' }
        }),
        createRunEvent({
          event_type: 'tool_call',
          agent_name: 'Agent A',
          payload: { tool_name: 'tool1' }
        })
      ];

      const filtered = filterEventsForDisplay(events, {
        selectedAgentName: 'Agent A',
        hidePhaseEvents: true
      });

      // System activity (non-phase) should pass through
      expect(filtered.some(e => e.agent_name === 'System')).toBe(true);
      expect(filtered.some(e => e.agent_name === 'Agent A')).toBe(true);
    });
  });
});
