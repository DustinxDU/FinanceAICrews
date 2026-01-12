export type StepType = 'thought' | 'tool_call' | 'observation' | 'final_answer';

export interface ExecutionStep {
  id: string;
  type: StepType;
  content?: string;
  agentName?: string;
  toolName?: string;
  input?: string;
  timestamp: string;
}

// Backend RunEvent types
export enum RunEventType {
    ACTIVITY = "activity",
    TOOL_CALL = "tool_call",
    TOOL_RESULT = "tool_result",
    LLM_CALL = "llm_call",
    TASK_STATE = "task_state",
    SYSTEM = "system"
}

export interface RunEvent {
    event_id: string;
    run_id: string;
    event_type: RunEventType;
    timestamp: string;
    agent_name?: string;
    task_id?: string;
    severity: string;
    payload: any;
}