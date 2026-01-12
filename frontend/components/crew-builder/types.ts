// Types for Crew Builder
export type NodeType = "start" | "agent" | "router" | "knowledge" | "end";

export interface NodeVariable {
  name: string;
  label?: string;
  type: 'text' | 'select' | 'number' | string;
  options?: string[];
  description?: string;  // Help text for the variable
}

export interface Route {
  id: string;
  label: string;
  criteria: string;
  color: string;
}

export interface NodeData {
  // Common
  name?: string;
  label?: string;
  
  // Start Node
  inputMode?: 'custom' | 'template';
  templateId?: string;
  variables?: NodeVariable[];
  inputSchema?: any[];
  
  // ============================================
  // Agent Node: WHO (Agent Identity)
  // ============================================
  role?: string;              // Role name
  model?: string;             // Routing tier (agents_fast/balanced/best)
  llm_config_id?: string;     // Model configuration ID
  goal?: string;              // Agent's overall goal
  backstory?: string;         // Persona/backstory
  tools?: string[];           // Bound tools
  selectedSkillKeys?: string[]; // Selected skills for the agent
  loadout_data?: { skill_keys?: string[]; tools?: string[] }; // Skill loadout data
  maxIter?: number;           // Max iterations
  allowDelegation?: boolean;  // Allow delegation
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
  verbose?: boolean;
  
  // ============================================
  // Agent Node: WHAT (Task Definition)
  // ============================================
  taskName?: string;          // Task name (e.g., "Fundamental Analysis")
  taskDescription?: string;   // Task description/instruction (supports {{variable}} interpolation)
  expectedOutput?: string;    // Expected output format
  asyncExecution?: boolean;   // Asynchronous execution
  
  // Router Node
  routes?: Route[];
  instruction?: string;
  defaultRouteId?: string;
  routerModel?: string;
  
  // Knowledge Node
  sourceType?: string;
  content?: string;
  source_id?: number;
  is_user_source?: boolean;
  
  // End Node
  outputFormat?: string;
  structureTemplate?: string;
  aggregationMethod?: 'concatenate' | 'llm_summary';
  summaryPrompt?: string;
  summaryModel?: string;      // Routing tier for summarization
  saveToHistory?: boolean;
  channels?: string[];
}

// Expected Output Templates
export const EXPECTED_OUTPUT_TEMPLATES = {
  markdown: {
    label: "📝 Markdown Report",
    value: "A detailed analytical report in Markdown format with clear sections, bullet points, and data tables where appropriate."
  },
  json: {
    label: "📊 JSON Structure",
    value: "A strict JSON object following the schema: { \"summary\": string, \"key_findings\": string[], \"metrics\": object, \"recommendation\": string }"
  },
  bullets: {
    label: "📋 Bullet Points",
    value: "A concise list of 5-10 key findings and actionable insights, each as a clear bullet point."
  },
  executive: {
    label: "📈 Executive Summary",
    value: "A 2-3 paragraph executive summary suitable for senior leadership, focusing on key insights and strategic recommendations."
  }
};

export interface Node {
  id: string;
  type: NodeType;
  x: number;
  y: number;
  w: number;
  h: number;
  data: NodeData;
}

export interface Edge {
  from: string;
  to: string;
  handleId?: string;
  type?: 'control' | 'resource';
}

export interface SavedCrew {
  id: number;
  name: string;
  description: string;
  agents: number;
  lastRun: string;
  status: 'active' | 'inactive';
  isTemplate?: boolean;
}
