import { useState, useEffect, useCallback, useRef } from 'react';
import { ExecutionStep, RunEvent, RunEventType } from './types';

export const useExecutionStream = (runId: string | null) => {
  const [steps, setSteps] = useState<ExecutionStep[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const transformEvent = useCallback((event: RunEvent): ExecutionStep | null => {
    const baseStep = {
      id: event.event_id,
      timestamp: event.timestamp,
      agentName: event.agent_name,
    };

    switch (event.event_type) {
      case RunEventType.ACTIVITY:
        return {
          ...baseStep,
          type: 'thought',
          content: event.payload.message,
        };
      case RunEventType.TOOL_CALL:
        return {
          ...baseStep,
          type: 'tool_call',
          toolName: event.payload.tool_name,
          input: JSON.stringify(event.payload.input_data, null, 2),
        };
      case RunEventType.TOOL_RESULT:
        return {
          ...baseStep,
          type: 'observation',
          content: typeof event.payload.output_data === 'string' 
            ? event.payload.output_data 
            : JSON.stringify(event.payload.output_data, null, 2),
        };
      case RunEventType.LLM_CALL:
        if (event.payload.status === 'success' && event.payload.message?.includes('Final Answer')) {
            // This is a bit heuristic, but if it's the final answer we can treat it specially
             return {
                ...baseStep,
                type: 'final_answer',
                content: event.payload.message,
            };
        }
        // Otherwise treat LLM call as a "thought" step for now
        return {
          ...baseStep,
          type: 'thought',
          content: event.payload.message || `LLM Call: ${event.payload.model_name}`,
        };
      case RunEventType.TASK_STATE:
          if (event.payload.status === 'completed') {
              // Usually the final result comes as a TASK_STATE or in the last LLM call
              // We'll see how to better capture the "Final Result" content specifically.
          }
          return null;
      default:
        return null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!runId) return;

    if (wsRef.current) {
        wsRef.current.close();
    }

    const wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    const socket = new WebSocket(`${wsBaseUrl}/api/v1/realtime/ws/analysis/${runId}`);
    wsRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      console.log(`Connected to execution stream: ${runId}`);
    };

    socket.onmessage = (event) => {
      try {
        const runEvent: RunEvent = JSON.parse(event.data);
        const step = transformEvent(runEvent);
        if (step) {
          setSteps((prev) => [...prev, step]);
        }
      } catch (err) {
        console.error('Failed to parse execution event:', err);
      }
    };

    socket.onclose = () => {
      setIsConnected(false);
      console.log(`Disconnected from execution stream: ${runId}`);
    };

    socket.onerror = (err) => {
      console.error('Execution stream WebSocket error:', err);
    };
  }, [runId, transformEvent]);

  useEffect(() => {
    if (runId) {
      connect();
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [runId, connect]);

  const clearSteps = useCallback(() => {
      setSteps([]);
  }, []);

  return {
    steps,
    isConnected,
    clearSteps
  };
};
