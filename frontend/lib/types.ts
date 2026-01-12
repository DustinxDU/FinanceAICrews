/**
 * Unified Type Definitions
 * 
 * Contains all shared types used across the application
 */

// ============================================
// Analysis & Job Types
// ============================================

export interface AnalysisRequest {
  ticker: string;
  crew_name: string;
  date?: string;
  selected_analysts?: string[];
  debate_rounds?: number;
  variables?: Record<string, any>;
}

export interface JobResponse {
  job_id: string;
  message: string;
  status: string;
}

export interface CitationInfo {
  source_name: string;
  display_name?: string;
  description?: string;
  category?: string;
  is_valid?: boolean;
}

export interface StructuredResult {
  text: string;
  citations: CitationInfo[];
  citation_count: number;
  has_citations: boolean;
}

export interface JobStatus {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  progress_message: string;
  result?: string;
  structured_result?: StructuredResult;
  error?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  ticker?: string;
  crew_name?: string;

  // v3 扩展字段
  events?: RunEvent[];
  summary?: RunSummary;
}

export interface CrewInfo {
  name: string;
  description: string;
  phases: string[];
  debate_rounds: number;
  optional_analysts?: Array<{
    name: string;
    task: string;
    default?: boolean;
  }>;
  style_config?: Record<string, unknown>;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

export interface ChatResponse {
  reply: string;
  job_id: string;
  chat_history: ChatMessage[];
}

// ============================================
// Crew Builder Types
// ============================================

export interface AgentDefinition {
  id: number;
  user_id: number | null;
  name: string;
  role: string;
  goal: string;
  backstory: string;
  description: string | null;
  llm_config: Record<string, any> | null;
  allow_delegation: boolean;
  verbose: boolean;
  is_template: boolean;
  is_active: boolean;
  tool_ids: number[] | null;
  knowledge_source_ids: number[] | null;
  mcp_server_ids: number[] | null;
  loadout_data?: {
    skill_keys?: string[];
    [key: string]: any;
  } | null;
  created_at: string;
  updated_at: string;
}

export interface CreateAgentDefinitionRequest {
  name: string;
  role: string;
  goal: string;
  backstory: string;
  description?: string;
  llm_config?: Record<string, any>;
  allow_delegation?: boolean;
  verbose?: boolean;
  is_template?: boolean;
  tool_ids?: number[];
  knowledge_source_ids?: number[];
  mcp_server_ids?: number[];
  loadout_data?: {
    skill_keys?: string[];
    [key: string]: any;
  };
}

export interface TaskDefinition {
  id: number;
  user_id: number | null;
  name: string;
  description: string;
  expected_output: string;
  agent_definition_id: number | null;
  async_execution: boolean;
  context_task_ids: number[] | null;
  created_at: string;
  updated_at: string;
}

export interface CreateTaskDefinitionRequest {
  name: string;
  description: string;
  expected_output: string;
  agent_definition_id?: number;
  async_execution?: boolean;
  context_task_ids?: number[];
}

export interface CrewDefinition {
  id: number;
  user_id: number | null;
  name: string;
  description: string | null;
  process: string;
  structure: CrewStructureEntry[];
  ui_state: Record<string, any> | null;
  input_schema: Record<string, any> | null;
  router_config: Record<string, any> | null;
  memory_enabled: boolean;
  cache_enabled: boolean;
  verbose: boolean;
  max_iter: number | null;
  manager_llm_config: Record<string, any> | null;
  default_variables: Record<string, any> | null;
  is_template: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateCrewDefinitionRequest {
  name: string;
  description?: string;
  process?: string;
  structure?: CrewStructureEntry[];
  ui_state?: Record<string, any>;
  input_schema?: Record<string, any>;
  router_config?: Record<string, any>;
  memory_enabled?: boolean;
  cache_enabled?: boolean;
  verbose?: boolean;
  max_iter?: number;
  manager_llm_config?: Record<string, any>;
  default_variables?: Record<string, any>;
  is_template?: boolean;
}

export interface CrewStructureEntry {
  agent_id: number;
  tasks: number[];
}

export interface CrewDetailExpanded {
  id: number;
  user_id: number | null;
  name: string;
  description: string | null;
  process: string;
  structure: Array<{
    agent: AgentDefinition | null;
    tasks: TaskDefinition[];
  }>;
  ui_state: Record<string, any> | null;
  input_schema: Record<string, any> | null;
  router_config: Record<string, any> | null;
  memory_enabled: boolean;
  cache_enabled: boolean;
  verbose: boolean;
  max_iter: number;
  manager_llm_config: Record<string, any> | null;
  default_variables: Record<string, any> | null;
  is_template: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CrewVersion {
  version_number: number;
  description: string | null;
  created_at: string;
}

export interface VariableInfo {
  name: string;
  default: any | null;
  required: boolean;
}

export interface UnauthorizedKnowledgeInfo {
  source_key: string;
  display_name: string;
  tier: string;
  price: number;
}

export interface PreflightResult {
  success: boolean;
  errors: string[];
  warnings: string[];
  hints?: string[];           // v3 扩展
  missing_variables: string[];
  missing_api_keys: string[];
  unauthorized_knowledge: (string | UnauthorizedKnowledgeInfo)[];
  mcp_health?: Record<string, boolean>; // v3 扩展
  crew_name?: string;
}

// ============================================
// Tool Tier Definitions
// ============================================

export type ToolTier = 'data' | 'quant' | 'external' | 'strategy';

// ============================================
// Unified Tool Registry Types
// ============================================

export type ToolSource = 'mcp' | 'quant' | 'crewai' | 'user';

export interface UnifiedTool {
  key: string;                    // Unique tool key (e.g., "akshare:stock_us_hist")
  name: string;
  description: string;
  source: ToolSource;
  category: string;
  tier: ToolTier;
  icon: string | null;
  is_active: boolean;              // System-level activation
  user_enabled: boolean;           // User-level preference
  requires_api_key: boolean;
  api_key_provider: string | null;
  is_configured: boolean;
  server_key: string | null;
  server_name: string | null;
  sort_order: number;
}

export interface ToolTierGroup {
  tier: ToolTier;
  title: string;
  icon: string;
  tools: UnifiedTool[];
  total: number;
  enabled_count: number;
}

export interface UnifiedToolsResponse {
  tiers: ToolTierGroup[];
  summary: {
    total: number;
    enabled: number;
    mcp: number;
    quant: number;
    crewai: number;
    user: number;
  };
}

export interface MCPServerStatus {
  server_key: string;
  display_name: string;
  description: string | null;
  is_active: boolean;
  is_subscribed: boolean;
  tools_count: number;
  enabled_tools_count: number;
}

export interface ToggleToolResponse {
  tool_key: string;
  user_enabled: boolean;
  message: string;
}

// ============================================
// Legacy 4-Tier Loadout Types (for backward compatibility)
// ============================================

export interface TieredTool {
  id: string;                    // Namespaced ID: "tier:key" (e.g., "data:price", "strategy:123")
  name: string;
  description: string;
  category: string;
  is_system: boolean;
  requires_config: boolean;
  formula?: string;              // Only for Tier 4 strategies
  usage_count?: number;          // Only for user strategies
  is_public?: boolean;           // Only for user strategies
}

export interface TierGroup {
  tier: ToolTier;
  title: string;
  tools: TieredTool[];
  total: number;
}

export interface TieredToolsResponse {
  data: TierGroup;
  quant: TierGroup;
  external: TierGroup;
  strategies: TierGroup;
}

// ============================================
// User Preferences & Copilot Types
// ============================================

export interface UserPreferencesResponse {
  /** @deprecated Use default_model_config_id instead */
  default_llm_config_id: string | null;
  /** New field: UserModelConfig.id for precise model selection */
  default_model_config_id: number | null;
  available_llm_configs: Array<{
    id: string;
    name: string;
    provider_name: string;
    model_name: string;
  }>;
}

export type ThemeOption = 'light' | 'dark' | 'system';

export interface PreferencesResponse {
  theme: ThemeOption;
  locale: string;
  timezone: string;
}

export interface PreferencesUpdateRequest {
  theme?: ThemeOption;
  locale?: string;
  timezone?: string;
}

// ============================================
// User Notification Preferences Types
// ============================================

/**
 * Web Push subscription keys for browser notifications
 */
export interface PushSubscriptionKeys {
  p256dh: string;
  auth: string;
}

/**
 * Web Push subscription data
 */
export interface PushSubscriptionData {
  endpoint: string;
  keys: PushSubscriptionKeys;
}

/**
 * Request to update user notification preferences
 */
export interface UpdateNotificationPreferencesRequest {
  enabled: boolean;
  analysis_completion?: boolean;
  system_updates?: boolean;
  push_subscription?: PushSubscriptionData | null;
}

/**
 * User notification preferences response
 */
export interface UserNotificationPreferences {
  id: number;
  user_id: number;
  enabled: boolean;
  analysis_completion: boolean;
  system_updates: boolean;
  has_push_subscription: boolean;
  created_at: string;
  updated_at: string;
}

// ============================================
// Notifications (Webhook) Types - DEPRECATED
// System webhooks are now configured via environment variables
// ============================================

/** @deprecated Use environment variables for system webhooks */
export type WebhookLastStatus = 'never' | 'success' | 'failed';

/** @deprecated Use environment variables for system webhooks */
export interface WebhookSettingsRequest {
  webhook_url: string;
  shared_secret: string;
}

/** @deprecated Use environment variables for system webhooks */
export interface WebhookSettingsResponse {
  webhook_url: string;
  last_status: WebhookLastStatus | string;
  last_error?: string | null;
  last_delivery_at?: string | null;
}

/** @deprecated Use environment variables for system webhooks */
export type WebhookTestStatus = 'success' | 'failed';

/** @deprecated Use environment variables for system webhooks */
export interface WebhookTestResponse {
  status: WebhookTestStatus | string;
  error?: string | null;
}

export interface CopilotMessage {
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;  // Thinking content from thinking models (GLM-4.6, DeepSeek-R1)
  timestamp?: string;
}

export interface CopilotChatResponse {
  reply: string;
  sources: string[];
  search_performed: boolean;
  execution_time_ms: number;
}

export interface CopilotHistoryResponse {
  messages: CopilotMessage[];
  total_count: number;
}

// ============================================
// Portfolio Types
// ============================================

export interface AssetSearchRequest {
  query: string;
  asset_types?: string[];
  limit?: number;
}

export interface AssetSearchResult {
  ticker: string;
  name: string;
  asset_type: string;
  exchange?: string;
  currency?: string;
  market_cap?: number;
  description?: string;
}

export interface AddAssetRequest {
  ticker: string;
  asset_type: string;
  notes?: string;
  target_price?: number;
}

export interface UpdateAssetRequest {
  notes?: string;
  target_price?: number;
  display_order?: number;
}

export interface UserAssetResponse {
  id: number;
  ticker: string;
  asset_type: string;
  asset_name?: string;
  current_price?: number;
  price_local?: number;      // 本地货币价格（港元/人民币）
  currency_local?: string;   // 本地货币代码（HKD/CNY）
  price_change?: number;
  price_change_percent?: number;
  market_cap?: number;
  volume?: number;
  exchange?: string;
  currency?: string;
  notes?: string;
  target_price?: number;
  display_order: number;
  added_at: string;
  last_updated?: string;
}

export interface PortfolioSummary {
  total_assets: number;
  asset_types: Record<string, number>;
  last_updated?: string;
}

// ============================================
// Library (资产情报局) Types
// ============================================

export interface LibraryInsight {
  id: number;
  ticker: string;
  asset_name?: string;
  asset_type?: string;
  source_type: string;
  source_id?: string;
  crew_name?: string;
  title: string;
  summary?: string;
  content?: string;
  sentiment?: string;
  sentiment_score?: number;
  confidence?: number;
  key_metrics?: Record<string, any>;
  signal?: string;
  target_price?: number;
  stop_loss?: number;
  raw_data?: Record<string, any>;  // 原始数据（news_highlights, price_info 等）
  tags?: string[];
  is_favorite: boolean;
  is_read: boolean;
  analysis_date?: string;
  created_at: string;
  attachments_count: number;
}

export interface LibraryAssetGroup {
  ticker: string;
  asset_name?: string;
  asset_type?: string;
  insights_count: number;
  last_analysis_at?: string;
  latest_sentiment?: string;
  latest_signal?: string;
  insights: LibraryInsight[];
}

export interface LibraryTimelineEntry {
  date: string;
  insights_count: number;
  sources: string[];
  tickers: string[];
}

export interface LibraryInsightDetail {
  insight: LibraryInsight;
  attachments: Array<{
    id: number;
    file_name: string;
    file_type: string;
    file_size?: number;
    description?: string;
  }>;
  traces: Array<{
    id: number;
    agent_name?: string;
    action_type: string;
    content?: string;
    step_order?: number;
    tokens_used?: number;
    duration_ms?: number;
    created_at?: string;
    input_data?: unknown;
    output_data?: unknown;
  }>;
}

export interface LibraryStats {
  total_insights: number;
  total_attachments: number;
  total_tickers: number;
  sentiment_distribution: Record<string, number>;
  source_distribution: Record<string, number>;
}

// ============================================
// Cockpit Indicator Types
// ============================================

export interface CockpitMacroIndicator {
  id: string;
  name: string;
  value: string;
  change: string;
  change_percent: number;
  trend: 'up' | 'down';
  critical: boolean;
  symbol: string;
  type: string;
}

export interface AvailableIndicator {
  indicator_id: string;
  indicator_name: string;
  symbol: string;
  indicator_type: string;
  is_critical: boolean;
  current_value?: string;
  change_percent?: number;
  trend?: string;
  is_selected: boolean;
  last_updated?: string;
}

export interface UserCockpitIndicatorRequest {
  indicator_id: string;
}

export interface UserCockpitIndicatorResponse {
  id: number;
  indicator_id: string;
  indicator_name: string;
  symbol: string;
  current_value?: string;
  change_value?: string;
  change_percent?: number;
  trend?: string;
  is_critical: boolean;
  indicator_type: string;
  display_order: number;
  added_at: string;
}

export interface CockpitMacroResponse {
  indicators: CockpitMacroIndicator[];
  last_updated: string;
  next_update_in_seconds: number;
}

// ============================================
// Chart & Analysis Types
// ============================================

export interface SparklineResponse {
  ticker: string;
  data: number[];
  timestamps: string[];
  change_percent: number;
  high: number;
  low: number;
  cached: boolean;
  current_price?: number;  // 历史数据的最后收盘价（非实时价格）
  last_close_date?: string;  // 最后收盘价的日期 (YYYY-MM-DD)
}

export interface QuickScanResponse {
  ticker: string;
  summary: string;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  news_highlights: string[];
  price_info: Record<string, any>;
  execution_time_ms: number;
}

export interface ChartAnalysisResponse {
  ticker: string;
  technical_summary: string;
  indicators: Record<string, any>;
  support_resistance: Record<string, any>;
  trend_assessment: string;
  execution_time_ms: number;
}

// ============================================
// Market Data Types
// ============================================

export interface MarketIndex {
  code: string;
  name: string;
  symbol: string;
  country: string;
  description: string;
  color: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number | null;
  timestamp: string;
  is_up: boolean;
}

export interface MarketDataResponse {
  markets: MarketIndex[];
  last_updated: string;
  next_update_in_seconds: number;
}

// ============================================
// Tool Usage Statistics Types
// ============================================

export interface ToolUsageStats {
  tool_key: string;
  tool_name: string;
  source: string;
  category: string;
  usage_count: number;
  last_used: string | null;
  avg_daily_usage: number;
}

export interface ToolRecommendation {
  tool_key: string;
  tool_name: string;
  source: string;
  category: string;
  reason: string;
  score: number;
}

export interface ToolUsageStatsResponse {
  total_usage: number;
  most_used_tools: ToolUsageStats[];
  recommendations: ToolRecommendation[];
  usage_by_category: Record<string, number>;
  usage_by_source: Record<string, number>;
}

export interface TrendingTool {
  tool_key: string;
  tool_name: string;
  source: string;
  category: string;
  usage_count: number;
  user_count: number;
  growth_rate: number;
}

export interface TrendingToolsResponse {
  trending_tools: TrendingTool[];
  period_days: number;
  last_updated: string;
}

// ============================================
// LLM Config Types
// ============================================

export interface LLMProviderInfo {
  provider: string;
  display_name: string;
  is_china_provider: boolean;
  requires_custom_model_name: boolean;
  requires_base_url: boolean;
  requires_endpoint_id?: boolean;
  default_base_url?: string;
  available_models: Array<{ name: string; value: string }>;
  env_key_name: string;
}

export interface LLMConfig {
  id: string;
  provider: string;
  display_name: string;
  api_key_masked: string;
  base_url?: string;
  custom_model_name?: string;
  endpoint_id?: string;
  default_model?: string;
  temperature: number;
  max_tokens?: number;
  is_active: boolean;
  is_validated: boolean;
  is_from_env?: boolean;
  env_key_name?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateLLMConfigRequest {
  provider: string;
  display_name: string;
  api_key: string;
  base_url?: string;
  custom_model_name?: string;
  default_model?: string;
  temperature?: number;
  max_tokens?: number;
  endpoint_id?: string;
  is_active?: boolean;
}

export interface ModelConfigResponse {
  provider: string;
  display_name: string;
  source: 'api' | 'static';
  supports_dynamic_models: boolean;
  models: Array<{
    name: string;
    description?: string;
    context_length?: number;
  }>;
  last_updated: string;
}

// ============================================
// LLM Policy Router Types
// ============================================

export interface LLMPolicyProvider {
  provider_key: string;
  display_name: string;
  provider_type: string;
  requires_api_key: boolean;
  requires_base_url: boolean;
  default_api_base: string | null;
}

export interface LLMPolicyStatus {
  enabled: boolean;
  message: string;
}

export interface LLMUserByokProfileResponse {
  id: number;
  tier: string;
  provider: string;
  model: string;
  api_base: string | null;
  api_version: string | null;
  enabled: boolean;
  key_masked: string;
  last_tested_at: string | null;
  last_test_status: string | null;
  last_test_code: string | null;
  last_test_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface LLMUserByokProfileCreate {
  tier: string;
  provider: string;
  model: string;
  api_key: string;
  api_base?: string | null;
  api_version?: string | null;
  enabled?: boolean;
}

export interface LLMUserByokProfileUpdate {
  provider: string;
  model: string;
  api_key?: string | null;
  enabled: boolean;
}

export interface LLMRoutingOverrideResponse {
  id: number;
  scope: string;
  mode: string;
  created_at: string;
  updated_at: string;
  updated_by: string | null;
}

export interface LLMRoutingOverrideCreate {
  scope: string;
  mode: string;
}

export interface LLMVirtualKeyResponse {
  id: number;
  key_type: string;
  status: string;
  allowed_models: string[];
  created_at: string;
  rotated_at: string | null;
}

export interface LLMRoutingPreview {
  routing_effective: string;
  scope: string;
  model_alias: string | null;
  provider: string | null;
  user_model: string | null;
}

// ============================================
// MCP Types
// ============================================

export interface MCPServer {
  id: number;
  server_key: string;
  display_name: string;
  description: string | null;
  transport_type: string;
  url: string | null;
  requires_auth: boolean;
  provider: string | null;
  is_active: boolean;
  is_system: boolean;
  icon: string | null;
  documentation_url: string | null;
  tools_count: number;
  available_tools_count: number;
}

export interface UserMCPServer {
  id: number;
  server_key: string;
  display_name: string;
  description: string | null;
  transport_type: string;
  url: string | null;
  is_active: boolean;
  is_connected: boolean;
  last_connected_at: string | null;
  connection_error: string | null;
  tools_count: number;
  created_at: string;
}

export interface MCPToolDetail {
  id: number;
  server_id: number;
  server_key: string;
  server_name: string;
  tool_name: string;
  display_name: string;
  description: string | null;
  category: string;
  input_schema: Record<string, any> | null;
  requires_api_key: boolean;
  api_key_provider: string | null;
  is_active: boolean;
  tags: string[] | null;
  user_enabled: boolean;
  user_configured: boolean;
  is_validated: boolean;
}

export interface MCPStats {
  system: { servers: number; tools: number };
  by_category: Record<string, number>;
  by_server: Array<{ server_key: string; display_name: string; tools_count: number }>;
  user?: { custom_servers: number; custom_tools: number; configured_tools: number };
}

export interface CreateUserMCPServerRequest {
  server_key: string;
  display_name: string;
  description?: string;
  transport_type?: string;
  url: string;
  api_key?: string;
}

export interface AgentToolBindingConfig {
  id: number;
  crew_name: string;
  agent_role: string;
  binding_mode: string;
  tool_ids: number[] | null;
  categories: string[] | null;
  excluded_tool_ids: number[] | null;
  created_at: string;
}

// ============================================
// Legacy Types (for backward compatibility)
// ============================================

export interface CrewTemplate {
  id: string;
  name: string;
  description: string;
  is_system: boolean;
  crew_name?: string;
  phases: string[];
  debate_rounds: number;
  execution?: Record<string, any>;
  optional_analysts?: Array<{ name: string; task: string; default: boolean }>;
}

export interface CrewSummary {
  id: string;
  name: string;
  description: string;
  agent_count: number;
  task_count: number;
  process: string;
  debate_rounds: number;
  is_template: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AgentConfigType {
  id: string;
  name: string;
  role: string;
  goal: string;
  backstory: string;
  tools: string[];
  llm_config_id?: string;
  llm_type: string;
  verbose: boolean;
  allow_delegation: boolean;
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
  max_iter?: number;
}

export interface TaskConfigType {
  id: string;
  name: string;
  description: string;
  expected_output: string;
  agent_id: string;
  context_task_ids: string[];
  async_execution: boolean;
}

export interface CrewConfigFull {
  id: string;
  name: string;
  description: string;
  agents: AgentConfigType[];
  tasks: TaskConfigType[];
  process: string;
  memory: boolean;
  max_iter: number;
  verbose: boolean;
  debate_rounds: number;
  is_template: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreateAgentRequest extends Omit<AgentConfigType, 'id'> {
  knowledge_config?: any;
}

export interface CreateCrewRequest {
  name: string;
  description: string;
  agents: CreateAgentRequest[];
  tasks: Omit<TaskConfigType, 'id'>[];
  process?: string;
  memory?: boolean;
  max_iter?: number;
  verbose?: boolean;
  debate_rounds?: number;
  is_template?: boolean;
}

export interface LiveStatus {
  job_id: string;
  status: string;
  ticker: string;
  crew_name: string;
  started_at?: string;
  elapsed_ms?: number;
  current_agent?: string;
  current_activity?: string;
  tool_call_count: number;
  llm_call_count: number;
  total_tokens: number;
  recent_activities: Array<{
    timestamp: string;
    agent: string;
    type: string;
    message: string;
  }>;
}

export interface CompletionReport {
  job_id: string;
  ticker: string;
  crew_name: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  tools_summary: {
    total_calls: number;
    success: number;
    failed: number;
    by_tool: Record<string, { count: number; success: number; failed: number; avg_duration_ms: number }>;
  };
  llm_summary: {
    total_calls: number;
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    by_model: Record<string, { count: number; tokens: number; avg_duration_ms: number }>;
  };
  tool_calls: Array<{
    timestamp?: string;
    tool_name: string;
    agent_name: string;
    status: string;
    duration_ms?: number;
    error?: string;
  }>;
  llm_calls: Array<{
    timestamp?: string;
    agent_name: string;
    provider: string;
    model: string;
    status: string;
    tokens?: number;
    duration_ms?: number;
  }>;
}

export interface TrackingHistoryItem {
  job_id: string;
  ticker: string;
  crew_name: string;
  status: string;
  started_at?: string;
  duration_seconds?: number;
  tool_calls: number;
  llm_calls: number;
  total_tokens: number;
}

// System Configuration Types
export interface SystemAgentConfig {
  role: string;
  goal: string;
  backstory: string;
  llm_type: string;
  tools: string[];
  verbose: boolean;
}

export interface SystemTaskConfig {
  description: string;
  expected_output: string;
  agent: string;
  async_execution: boolean;
  context: string[];
}

// Task can be a string reference or an inline task definition
export type PhaseTask = string | {
  name?: string;
  description?: string;
  expected_output?: string;
  agent?: string;
  context?: string[];
};

export interface SystemCrewDetail {
  id: string;
  crew_name: string;
  name: string;
  description: string;
  execution: Record<string, any>;
  debate: Record<string, any>;
  phases: Array<{ name: string; tasks: PhaseTask[]; parallel?: boolean; repeat?: string }>;
  output: Record<string, any>;
  optional_analysts: Array<{ name: string; task: string; default: boolean }>;
  agents: Record<string, SystemAgentConfig>;
  tasks: Record<string, SystemTaskConfig>;
  is_system: boolean;
}

// ============================================
// Tool Registry Legacy Types
// ============================================

export interface ToolConfig {
  name: string;
  description: string;
  category: string;
  is_enabled: boolean;
}

export interface ToolInfo {
  key: string;
  name: string;
  description: string;
  category: string;
  source: string;
  is_enabled: boolean;
  requires_config: boolean;
  tags: string[];
}

export interface ToolCategoryInfo {
  key: string;
  name: string;
  description: string;
  icon: string;
  tool_count: number;
}

export interface UserToolsResponse {
  system_tools: ToolInfo[];
  user_strategies: Array<ToolInfo & { formula: string }>;
  user_mcp_tools: Array<ToolInfo & { server_name: string }>;
  summary: {
    total_system_tools: number;
    total_user_strategies: number;
    total_user_mcp_tools: number;
  };
}

export interface ExpressionEngineInfo {
  supported_functions: string[];
  price_variables: string[];
  operators: string[];
  examples: Array<{
    name: string;
    formula: string;
    description: string;
  }>;
}

// ============================================
// Agent Loadout Configuration
// ============================================

export interface AgentLoadout {
  // Legacy 4-tier format (deprecated, use skill_keys instead)
  data_tools?: string[];      // Tier 1: Data Feeds (e.g., ["data:price", "data:fundamentals"])
  quant_tools?: string[];     // Tier 2: Quant Skills (e.g., ["quant:rsi", "quant:macd"])
  external_tools?: string[];  // Tier 3: External Access (e.g., ["external:web_search"])
  strategies?: string[];      // Tier 4: User Strategies (e.g., ["strategy:123"])

  // New unified skill format (recommended)
  skill_keys?: string[];      // Unified skill keys (e.g., ["cap:equity_quote", "preset:rsi_14", "strategy:ma_cross"])
}

export interface LoadoutSummary {
  data: number;
  quant: number;
  external: number;
  strategies: number;
  total: number;
}

// ============================================
// User Strategy Types
// ============================================

export type StrategyCategory = 'trend' | 'momentum' | 'volatility' | 'custom';

export interface UserStrategy {
  id: number;
  name: string;
  description?: string;
  formula: string;
  category: StrategyCategory;
  variables?: Record<string, any>;
  is_active: boolean;
  is_public: boolean;
  usage_count: number;
  last_used_at?: string;
  last_result?: StrategyEvaluationResult;
  created_at?: string;
  updated_at?: string;
}

export interface StrategyCreateRequest {
  name: string;
  description?: string;
  formula: string;
  category?: StrategyCategory;
  is_public?: boolean;
}

export interface StrategyUpdateRequest {
  name?: string;
  description?: string;
  formula?: string;
  category?: StrategyCategory;
  is_active?: boolean;
  is_public?: boolean;
}

export interface StrategyValidateRequest {
  formula: string;
}

export interface StrategyValidateResponse {
  is_valid: boolean;
  formula: string;
  error?: string;
  supported_functions: string[];
  supported_variables: string[];
}

export interface StrategyEvaluationResult {
  ticker: string;
  result: boolean;
  timestamp: string;
  is_valid?: boolean;
  error?: string;
}

export interface StrategyEvaluateResponse {
  ticker: string;
  strategy_id: number;
  strategy_name: string;
  formula: string;
  result: boolean;
  message: string;
  context: {
    evaluation_time: string;
    note?: string;
  };
}

// ============================================
// Extended Node Data for Crew Builder
// ============================================

export interface ExtendedNodeData {
  // Common
  name?: string;
  
  // Start Node
  inputMode?: 'custom' | 'template';
  templateId?: string;
  variables?: NodeVariable[];
  
  // Agent Node - Basic
  role?: string;
  model?: string;
  llm_config_id?: string;
  goal?: string;
  backstory?: string;
  maxIter?: number;
  allowDelegation?: boolean;
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
  verbose?: boolean;
  
  // Agent Node - Tools (Legacy)
  tools?: string[];
  
  // Agent Node - 4-Tier Loadout (New)
  loadout_data?: AgentLoadout;
  
  // Router Node
  routes?: Route[];
  instruction?: string;
  
  // Knowledge Node
  sourceType?: string;
  content?: string;
  source_id?: number;
  
  // End Node
  outputFormat?: string;
  structureTemplate?: string;
  aggregationMethod?: 'concatenate' | 'llm_summary';
  summaryPrompt?: string;
  saveToHistory?: boolean;
  channels?: string[];
}

export interface NodeVariable {
  name: string;
  type: string;
}

export interface Route {
  id: string;
  label: string;
  criteria: string;
  color: string;
}

// ============================================
// Run Tracking & Execution Types (v3)
// ============================================

export type RunEventType = 'activity' | 'tool_call' | 'tool_result' | 'llm_call' | 'task_state' | 'task_output' | 'system';

export interface RunEvent {
  event_id: string;
  run_id: string;
  event_type: RunEventType;
  timestamp: string;
  agent_name?: string;
  task_id?: string;
  severity: 'debug' | 'info' | 'warning' | 'error';
  payload: Record<string, any>;
}

export interface RunSummary {
  total_duration_ms: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  tool_calls_count: number;
  agent_count: number;
  task_count: number;
  status: string;
  compiled_at: string;
}

// ============================================
// RunEvent Payload Types (for type-safe access)
// ============================================

export interface ActivityPayload {
  activity_type: 'thinking' | 'tool_call' | 'llm_call' | 'delegation' | 'output' | 'task_completed';
  message: string;
  details?: Record<string, any>;
}

export interface ToolCallPayload {
  tool_name: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  input_data?: Record<string, any>;
  output_data?: any;
  duration_ms?: number;
  error_message?: string;
  message?: string;
}

export interface LLMCallPayload {
  llm_provider: string;
  model_name: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  duration_ms?: number;
  error_message?: string;
  prompt_preview?: string;
  response_preview?: string;
  message?: string;
}

export interface TaskOutputPayload {
  summary: {
    raw_preview: string;
    validation_passed: boolean;
    json_dict_preview?: string;
    pydantic_dump?: Record<string, any>;
  };
  artifact_ref: {
    job_id: string;
    task_id: string;
    path?: string;
  };
  diagnostics: {
    output_mode: 'raw' | 'soft_pydantic' | 'soft_json_dict' | 'native_pydantic';
    schema_key?: string;
    citations: Array<Record<string, any>>;
    citation_count: number;
    degraded: boolean;
    warnings: string[];
  };
}

export interface TaskStatePayload {
  status: 'completed' | 'failed';
  error?: string;
  total_duration_ms?: number;
  timestamp?: string;
}

export interface TaskNodeStatus {
  task_id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  agent_name?: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error?: string;
}

// ============================================
// Utility Functions
// ============================================

/**
 * Parse a namespaced tool ID into tier and key
 * @example parseToolId("data:price") => { tier: "data", key: "price" }
 */
export function parseToolId(toolId: string): { tier: ToolTier; key: string } | null {
  const [tier, key] = toolId.split(':');
  if (!tier || !key) return null;
  if (!['data', 'quant', 'external', 'strategy'].includes(tier)) return null;
  return { tier: tier as ToolTier, key };
}

/**
 * Create a namespaced tool ID
 * @example createToolId("data", "price") => "data:price"
 */
export function createToolId(tier: ToolTier, key: string): string {
  return `${tier}:${key}`;
}

/**
 * Calculate loadout summary from AgentLoadout
 */
export function getLoadoutSummary(loadout?: AgentLoadout): LoadoutSummary {
  if (!loadout) {
    return { data: 0, quant: 0, external: 0, strategies: 0, total: 0 };
  }
  
  const data = loadout.data_tools?.length || 0;
  const quant = loadout.quant_tools?.length || 0;
  const external = loadout.external_tools?.length || 0;
  const strategies = loadout.strategies?.length || 0;
  
  return {
    data,
    quant,
    external,
    strategies,
    total: data + quant + external + strategies,
  };
}

/**
 * Get tier icon emoji
 */
export function getTierIcon(tier: ToolTier): string {
  const icons: Record<ToolTier, string> = {
    data: '📂',
    quant: '🧠',
    external: '🌍',
    strategy: '💎',
  };
  return icons[tier] || '🔧';
}

/**
 * Get tier color class
 */
export function getTierColorClass(tier: ToolTier): string {
  const colors: Record<ToolTier, string> = {
    data: 'text-blue-400 border-blue-500/50 bg-blue-900/20',
    quant: 'text-purple-400 border-purple-500/50 bg-purple-900/20',
    external: 'text-orange-400 border-orange-500/50 bg-orange-900/20',
    strategy: 'text-emerald-400 border-emerald-500/50 bg-emerald-900/20',
  };
  return colors[tier] || 'text-zinc-400 border-zinc-500/50 bg-zinc-900/20';
}

/**
 * Check if loadout is empty
 */
export function isLoadoutEmpty(loadout?: AgentLoadout): boolean {
  if (!loadout) return true;
  return (
    (loadout.data_tools?.length || 0) === 0 &&
    (loadout.quant_tools?.length || 0) === 0 &&
    (loadout.external_tools?.length || 0) === 0 &&
    (loadout.strategies?.length || 0) === 0
  );
}

/**
 * Create empty loadout
 */
export function createEmptyLoadout(): AgentLoadout {
  return {
    data_tools: [],
    quant_tools: [],
    external_tools: [],
    strategies: [],
  };
}

/**
 * Merge two loadouts (for combining defaults with user selections)
 */
export function mergeLoadouts(base: AgentLoadout, override: AgentLoadout): AgentLoadout {
  return {
    data_tools: [...new Set([...(base.data_tools || []), ...(override.data_tools || [])])],
    quant_tools: [...new Set([...(base.quant_tools || []), ...(override.quant_tools || [])])],
    external_tools: [...new Set([...(base.external_tools || []), ...(override.external_tools || [])])],
    strategies: [...new Set([...(base.strategies || []), ...(override.strategies || [])])],
  };
}

// ============================================
// Profile Management Types
// ============================================

export interface ProfileUpdateRequest {
  full_name?: string;
  avatar_url?: string;
  email?: string;
  phone_number?: string;
  current_password?: string;
  new_password?: string;
}

export interface ProfileResponse {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  phone_number?: string;
  avatar_url?: string;
  email_verified: boolean;
  pending_email?: string;
  subscription_level: string;
  last_password_change?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ============================================
// Skill Catalog Types (Provider → Capability → Skill)
// ============================================

/**
 * Skill - A unified skill in the 3-layer architecture
 * Skills can be capabilities (raw tools), presets (tool combinations),
 * strategies (analysis approaches), or skillsets (multi-capability bundles)
 */
export interface Skill {
  skill_key: string;
  kind: 'capability' | 'preset' | 'strategy' | 'skillset';
  capability_id: string | null;
  title: string;
  description: string | null;
  icon: string | null;
  tags: string[];
  is_system: boolean;
  is_enabled: boolean;
  is_ready: boolean;
  blocked_reason: string | null;
  args_schema: Record<string, any> | null;
  examples: any[];
}

// ============================================
// Privacy Types (Data Export & Account Deletion)
// ============================================

export interface DataExportRequest {
  include_analysis_reports?: boolean;
  include_portfolios?: boolean;
  include_settings?: boolean;
}

export interface DataExportJobResponse {
  id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'expired';
  error_message?: string | null;
  manifest?: string | null;
  download_url?: string | null;
  download_expires_at?: string | null;
  file_size_bytes?: number | null;
  requested_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface DataExportListResponse {
  jobs: DataExportJobResponse[];
  total: number;
}

export interface AccountDeletionRequest {
  reason?: string | null;
  confirm: boolean;
}

export interface AccountDeletionResponse {
  id: number;
  status: 'scheduled' | 'cancelled' | 'processing' | 'completed';
  reason?: string | null;
  scheduled_for: string;
  cancelled_at?: string | null;
  completed_at?: string | null;
  requested_at: string;
  days_remaining: number;
}

export interface PrivacyStatusResponse {
  has_pending_export: boolean;
  has_scheduled_deletion: boolean;
  deletion_scheduled_for?: string | null;
  deletion_days_remaining?: number | null;
  last_export_at?: string | null;
}
