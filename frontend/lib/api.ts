/**
 * API Client - Client for communicating with backend
 * 
 * Supports JWT Token authentication
 */

import { getToken, clearAuth } from './auth';
import { redirectToLogin } from './authRoutes';
// 从 types.ts 导入所有必要类型
import type { 
  // Analysis & Job Types
  AnalysisRequest,
  JobResponse,
  JobStatus,
  CrewInfo,
  ChatMessage,
  ChatResponse,
  
  // Crew Builder Types
  AgentDefinition,
  CreateAgentDefinitionRequest,
  TaskDefinition,
  CreateTaskDefinitionRequest,
  CrewDefinition,
  CreateCrewDefinitionRequest,
  CrewDetailExpanded,
  CrewVersion,
  VariableInfo,
  PreflightResult,
  
  // Unified Tool Registry Types
  UnifiedToolsResponse, 
  UnifiedTool, 
  ToolTierGroup,
  ToggleToolResponse,
  MCPServerStatus,
  
  // User Preferences & Copilot Types
  UserPreferencesResponse,
  PreferencesResponse,
  PreferencesUpdateRequest,
  UserNotificationPreferences,
  UpdateNotificationPreferencesRequest,
  PushSubscriptionData,
  WebhookSettingsRequest,
  WebhookSettingsResponse,
  WebhookTestResponse,
  CopilotMessage,
  CopilotChatResponse,
  CopilotHistoryResponse,
  
  // Portfolio Types
  AssetSearchRequest,
  AssetSearchResult,
  AddAssetRequest,
  UpdateAssetRequest,
  UserAssetResponse,
  PortfolioSummary,
  
  // Library Types
  LibraryInsight,
  LibraryAssetGroup,
  LibraryTimelineEntry,
  LibraryInsightDetail,
  LibraryStats,
  
  // Cockpit Indicator Types
  CockpitMacroIndicator,
  AvailableIndicator,
  CockpitMacroResponse,
  UserCockpitIndicatorResponse,
  UserCockpitIndicatorRequest,
  
  // Chart & Analysis Types
  SparklineResponse,
  QuickScanResponse,
  ChartAnalysisResponse,
  
  // Market Data Types
  MarketIndex,
  MarketDataResponse,
  
  // Tool Usage Statistics Types
  ToolUsageStatsResponse,
  TrendingToolsResponse,
  
  // LLM Config Types
  LLMProviderInfo,
  LLMConfig,
  CreateLLMConfigRequest,
  ModelConfigResponse,

  // LLM Policy Router Types
  LLMPolicyProvider,
  LLMPolicyStatus,
  LLMUserByokProfileResponse,
  LLMUserByokProfileCreate,
  LLMUserByokProfileUpdate,
  LLMRoutingOverrideResponse,
  LLMRoutingOverrideCreate,
  LLMVirtualKeyResponse,
  LLMRoutingPreview,

  // MCP Types
  MCPServer,
  UserMCPServer,
  MCPToolDetail,
  MCPStats,
  CreateUserMCPServerRequest,
  AgentToolBindingConfig,
  
  // User Strategy Types
  UserStrategy,
  StrategyEvaluationResult,
  
  // Tracking Types
  TrackingHistoryItem,
  CompletionReport,
  LiveStatus,
  
  // Tool Registry Legacy Types
  TieredToolsResponse,

  // 4-Tier Loadout Types
  AgentLoadout,
  ToolTier,

  // Profile Management Types
  ProfileUpdateRequest,
  ProfileResponse,

  // Skill Catalog Types
  Skill
} from './types';

// Skill Catalog API Types (local to api.ts)

interface SkillCatalogResponse {
  capabilities: Skill[];
  presets: Skill[];
  strategies: Skill[];
  skillsets: Skill[];
}

// Default use same domain (Next.js API proxy rewrites to backend), replace if configured
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL
  ? process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "")
  : "";

// ============================================
// API Client Class
// ============================================

class ApiClient {
  private baseUrl: string;
  private DEFAULT_TIMEOUT = 10000; // 10秒默认超时

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * 带超时控制的请求方法
   * @param endpoint API 端点
   * @param options 请求选项
   * @param requiresAuth 是否需要认证
   * @param timeout 超时时间（毫秒），默认 10 秒
   */
  private async requestWithTimeout<T>(
    endpoint: string,
    options: RequestInit = {},
    requiresAuth: boolean = true,
    timeout: number = this.DEFAULT_TIMEOUT
  ): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const result = await this.request<T>(
        endpoint,
        { ...options, signal: controller.signal },
        requiresAuth
      );
      clearTimeout(timeoutId);
      return result;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    requiresAuth: boolean = true
  ): Promise<T> {
    const base = this.baseUrl || "";
    const url = `${base}${endpoint}`;
    
    // Build headers, automatically add Token
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };
    
    if (requiresAuth) {
      const token = getToken();
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Clear auth and redirect to login when 401 Unauthorized
    if (response.status === 401) {
      clearAuth();
      redirectToLogin();
      throw new Error('Authentication expired, please log in again');
    }

    if (!response.ok) {
      let error: any = {};
      let jsonParseError = false;
      
      // Try to parse JSON response, fallback to empty object if it fails
      try {
        error = await response.json();
      } catch (parseError) {
        jsonParseError = true;
        console.warn('Failed to parse error response as JSON:', parseError);
        // Try to get response text instead
        try {
          const text = await response.text();
          if (text) {
            error = { message: text };
          }
        } catch (textError) {
          console.warn('Failed to get response text:', textError);
        }
      }
      
      let detail = "分析失败，请重试";  // Default Chinese error message
      
      // Handle different error response formats
      if (typeof error === "string" && error.trim()) {
        detail = error;
      } else if (error?.detail) {
        if (typeof error.detail === "string") {
          // Simple string detail
          detail = error.detail;
        } else if (typeof error.detail === "object" && error.detail !== null) {
          // New structured error format from backend
          if (error.detail.message) {
            detail = error.detail.message;
          } else {
            // Don't stringify empty objects
            const detailStr = JSON.stringify(error.detail);
            if (detailStr !== '{}') {
              detail = detailStr;
            }
          }
        } else if (Array.isArray(error.detail)) {
          // Array of error details
          detail = error.detail.map((d: any) => (typeof d === "string" ? d : JSON.stringify(d))).join("; ");
        }
      } else if (typeof error?.message === "string" && error.message.trim()) {
        detail = error.message;
      } else if (jsonParseError) {
        // If JSON parsing failed, provide a better error message
        detail = `服务器响应格式错误 (HTTP ${response.status})`;
      } else if (!error || Object.keys(error).length === 0) {
        // Handle empty error objects
        detail = `服务器内部错误 (HTTP ${response.status})`;
      }
      
      // Create a custom error object that preserves the original response data
      const apiError = new Error(`${detail} (HTTP ${response.status})`);
      (apiError as any).response = { data: error, status: response.status };
      throw apiError;
    }

    const text = await response.text();
    if (!text || !text.trim()) {
      return undefined as T;
    }

    try {
      return JSON.parse(text) as T;
    } catch (parseError) {
      console.error('Failed to parse successful response JSON:', parseError);
      throw new Error(`服务器响应格式错误 (HTTP ${response.status})`);
    }
  }

  // Analysis Task API
  async startAnalysis(request: AnalysisRequest): Promise<JobResponse> {
    return this.request<JobResponse>("/api/v1/analysis/start", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /** @deprecated Use getJobStatus instead */
  async getAnalysisStatus(jobId: string): Promise<JobStatus> {
    return this.request<JobStatus>(`/api/v1/analysis/status/${jobId}`);
  }

  async listAnalysisJobs(
    status?: string,
    limit: number = 50
  ): Promise<{ jobs: JobStatus[]; total: number }> {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    params.set("limit", limit.toString());
    return this.request(`/api/v1/analysis/list?${params.toString()}`);
  }

  async cancelAnalysis(jobId: string): Promise<{ message: string }> {
    return this.request(`/api/v1/analysis/${jobId}`, {
      method: "DELETE",
    });
  }

  // ============================================
  // Crew Execution v2 API (Database-driven)
  // ============================================

  /**
   * Start analysis using v2 crew-builder API (database-driven)
   * @param request - crew_id and variables
   */
  async startAnalysisV2(request: {
    crew_id: number;
    variables?: Record<string, any>;
    skip_preflight?: boolean;
  }): Promise<JobResponse> {
    return this.request<JobResponse>(`/api/v1/crew-builder/crews/${request.crew_id}/run`, {
      method: "POST",
      body: JSON.stringify({
        variables: request.variables || {},
        skip_preflight: request.skip_preflight || false,
      }),
    });
  }

  /**
   * Run preflight check for a crew before execution
   * @param crewId - ID of the crew to check
   * @param variables - Variables for the execution
   */
  async runPreflightCheck(crewId: number, variables?: Record<string, any>): Promise<{
    success: boolean;
    errors: string[];
    warnings?: string[];
    crew_name: string;
    variables_checked: string[];
  }> {
    return this.request(`/api/v1/crew-builder/crews/${crewId}/preflight`, {
      method: "POST",
      body: JSON.stringify({
        variables: variables || {},
      }),
    });
  }

  /**
   * Get job status using unified crew-builder API
   * @param jobId - ID of the job to check
   */
  async getJobStatus(jobId: string): Promise<JobStatus> {
    return this.request<JobStatus>(`/api/v1/crew-builder/jobs/${jobId}`);
  }

  // Crew/Strategy API (v1 - deprecated, use v2 crew-builder API)
  /** @deprecated Use listCrewDefinitions instead */
  async listCrews(): Promise<{ crews: string[] }> {
    return this.request("/api/v1/strategies");
  }

  /** @deprecated Use getCrewDefinition instead */
  async getCrewInfo(crewName: string): Promise<CrewInfo> {
    return this.request(`/api/v1/strategies/${crewName}`);
  }

  // Copilot Chat API
  async sendChatMessage(
    jobId: string,
    message: string
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, message }),
    });
  }

  // Health Check
  async healthCheck(): Promise<{ status: string; version: string; message: string }> {
    return this.request("/health");
  }

  // ============================================
  // LLM Config API (Deprecated - Please use LLMContext)
  // ============================================
  // 
  // ⚠️ DEPRECATED: The following LLM methods are deprecated
  // Please use contexts/LLMContext.tsx or hooks/useLLM.ts instead
  // They use the unified v2 API and provide better state management
  //
  // Migration example:
  //   import { useLLMContext } from '@/contexts/LLMContext';
  //   const { providers, configs, availableModels, refreshAll } = useLLMContext();
  //


  // ============================================
  // LLM v1 API Methods
  // ============================================

  async listConfigModels(configId: number, includeInactive: boolean = false): Promise<any[]> {
    return this.request(`/api/v1/llm/configs/${configId}/models?include_inactive=${includeInactive}`);
  }

  async updateModelStatus(modelConfigId: number, isActive: boolean): Promise<any> {
    return this.request(`/api/v1/llm/model-configs/${modelConfigId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    });
  }

  // ============================================
  // MCP v2 API Methods
  // ============================================
  // 注意：以下 MCP 方法已被统一工具注册 API (v2/tool-registry) 替代
  // 请使用 listUnifiedTools(), toggleUnifiedTool(), listMCPServersV2() 等方法

  /** @deprecated 请使用 listUnifiedTools() 和 toggleUnifiedTool() 替代 */
  async listSystemMCPServers(): Promise<MCPServer[]> {
    return this.request("/api/v2/mcp/v2/servers/system", {}, false);
  }

  /** @deprecated 请使用 listUnifiedTools() 和 toggleUnifiedTool() 替代 */
  async getSystemMCPServer(serverKey: string): Promise<{ server: MCPServer; tools_by_category: Record<string, any[]>; total_tools: number }> {
    return this.request(`/api/v2/mcp/v2/servers/system/${serverKey}`, {}, false);
  }

  /** @deprecated 请使用 listUnifiedTools() 和 toggleUnifiedTool() 替代 */
  async syncSystemMCPServer(serverKey: string, force: boolean = false): Promise<{ success: boolean; message: string; tools_count: number }> {
    return this.request(`/api/v2/mcp/v2/servers/system/${serverKey}/sync?force=${force}`, { method: "POST" });
  }

  /** @deprecated 请使用 listMCPServersV2() 替代 */
  async listUserMCPServers(): Promise<UserMCPServer[]> {
    return this.request("/api/v2/mcp/v2/servers/user");
  }

  /** @deprecated 请使用 createUserMCPServer() (来自统一工具注册 API) 替代 */
  async createUserMCPServer(data: CreateUserMCPServerRequest): Promise<{ id: number; server_key: string; message: string }> {
    return this.request("/api/v2/mcp/v2/servers/user", { method: "POST", body: JSON.stringify(data) });
  }

  /** @deprecated 请使用 createUserMCPServer() (来自统一工具注册 API) 替代 */
  async deleteUserMCPServer(serverId: number): Promise<{ message: string }> {
    return this.request(`/api/v2/mcp/v2/servers/user/${serverId}`, { method: "DELETE" });
  }

  /** @deprecated 请使用 listUnifiedTools() 替代 */
  async connectUserMCPServer(serverId: number): Promise<{ success: boolean; tools_count: number }> {
    return this.request(`/api/v2/mcp/v2/servers/user/${serverId}/connect`, { method: "POST" });
  }

  /** @deprecated 请使用 listUnifiedTools() 替代 */
  async listMCPTools(params?: { category?: string; server_key?: string; search?: string }): Promise<{ system_tools: MCPToolDetail[]; user_tools: any[]; total_system: number; categories: Record<string, number> }> {
    const query = new URLSearchParams();
    if (params?.category) query.set("category", params.category);
    if (params?.server_key) query.set("server_key", params.server_key);
    if (params?.search) query.set("search", params.search);
    return this.request(`/api/v1/mcp/tools?${query.toString()}`, {}, false);
  }

  /** @deprecated 请使用 listUnifiedTools() 替代 */
  async getMCPToolDetail(toolId: number): Promise<MCPToolDetail & { user_config: any }> {
    return this.request(`/api/v2/mcp/v2/tools/${toolId}`);
  }

  /** @deprecated 请使用 listUnifiedTools() 和 toggleUnifiedTool() 替代 */
  async configureMCPTool(toolId: number, apiKey: string): Promise<{ message: string }> {
    return this.request(`/api/v2/mcp/v2/tools/${toolId}/configure`, { method: "POST", body: JSON.stringify({ api_key: apiKey }) });
  }

  /** @deprecated 请使用 listUnifiedTools() 和 toggleUnifiedTool() 替代 */
  async validateMCPTool(toolId: number): Promise<{ success: boolean; message: string }> {
    return this.request(`/api/v2/mcp/v2/tools/${toolId}/validate`, { method: "POST" });
  }

  /** @deprecated 请使用 toggleUnifiedTool() 替代 */
  async toggleMCPTool(toolId: number, enabled: boolean): Promise<{ message: string }> {
    return this.request(`/api/v2/mcp/v2/tools/${toolId}/toggle?enabled=${enabled}`, { method: "POST" });
  }

  /** @deprecated 请使用 listUnifiedTools() 替代 */
  async searchMCPTools(query: string, categories?: string[], limit?: number): Promise<{ results: MCPToolDetail[]; count: number }> {
    return this.request("/api/v2/mcp/v2/tools/search", { method: "POST", body: JSON.stringify({ query, categories, limit: limit || 10 }) });
  }

  /** @deprecated 请使用 listUnifiedTools() 替代 */
  async getMCPStats(): Promise<MCPStats> {
    return this.request("/api/v2/mcp/v2/stats", {}, false);
  }

  /** @deprecated Crew Builder Agent 工具绑定功能已移除，请使用 Crew Builder UI 配置 */
  async listAgentToolBindings(crewName?: string): Promise<AgentToolBindingConfig[]> {
    const query = crewName ? `?crew_name=${crewName}` : "";
    return this.request(`/api/v2/mcp/v2/bindings${query}`);
  }

  /** @deprecated Crew Builder Agent 工具绑定功能已移除，请使用 Crew Builder UI 配置 */
  async upsertAgentToolBinding(data: { crew_name: string; agent_role: string; binding_mode: string; tool_ids?: number[]; categories?: string[]; excluded_tool_ids?: number[] }): Promise<{ id: number; message: string }> {
    return this.request("/api/v2/mcp/v2/bindings", { method: "POST", body: JSON.stringify(data) });
  }

  /** @deprecated Crew Builder Agent 工具绑定功能已移除，请使用 Crew Builder UI 配置 */
  async deleteAgentToolBinding(bindingId: number): Promise<{ message: string }> {
    return this.request(`/api/v2/mcp/v2/bindings/${bindingId}`, { method: "DELETE" });
  }

  /** @deprecated MCP 初始化功能已集成到统一工具注册 API */
  async initMCPServers(): Promise<{ message: string; servers: string[] }> {
    return this.request("/api/v2/mcp/v2/init", { method: "POST" });
  }

  // User Profile API
  async getCurrentUser(): Promise<{ id: number; email: string; subscription_level: string; created_at: string }> {
    return this.request("/api/v1/auth/me");
  }

  // ============================================
  // Profile Management API
  // ============================================

  async getProfile(): Promise<ProfileResponse> {
    return this.request("/api/v1/profile");
  }

  async updateProfile(data: ProfileUpdateRequest): Promise<ProfileResponse> {
    return this.request("/api/v1/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  // ============================================
  // Usage Activity API
  // ============================================

  async getUsageStats(): Promise<{
    total_tokens_current_month: number;
    total_tokens_previous_month: number;
    token_growth_percentage: number;
    reports_generated_current_month: number;
    estimated_cost_current_month: number;
    currency: string;
  }> {
    return this.request("/api/v1/usage/stats");
  }

  async getUsageActivity(params?: {
    page?: number;
    page_size?: number;
    start_date?: string;
    end_date?: string;
  }): Promise<{
    items: Array<{
      id: number;
      date: string;
      time: string;
      activity: string;
      model: string;
      reports: number;
      tokens: number;
    }>;
    total_count: number;
    current_page: number;
    total_pages: number;
  }> {
    const query = new URLSearchParams();
    if (params?.page) query.set('page', params.page.toString());
    if (params?.page_size) query.set('page_size', params.page_size.toString());
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);

    return this.request(`/api/v1/usage/activity?${query.toString()}`);
  }

  async exportUsageData(data: {
    start_date: string;
    end_date: string;
    format?: string;
  }): Promise<any> {
    return this.request("/api/v1/usage/export", {
      method: "POST",
      body: JSON.stringify({
        start_date: data.start_date,
        end_date: data.end_date,
        format: data.format || 'csv'
      }),
    });
  }

  /**
   * Download a file (blob) with authentication
   * Returns the raw Response object so caller can access headers and blob
   */
  async downloadBlob(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<Response> {
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    return fetch(url, {
      ...options,
      headers,
    });
  }

  // LLM Provider Management API (extended from deprecated method above)

  /**
   * @deprecated Use /api/v1/llm-policy/byok-profiles or validated-providers API instead.
   * This method calls the same deprecated endpoint as listLLMConfigs().
   * See frontend/app/settings/page.tsx for migration plan details.
   */

  async listValidatedProviders(): Promise<Array<any>> {
    return this.request("/api/v1/llm/validated-providers");
  }

  /**
   * @deprecated Use Policy Router API instead.
   * This method calls the same deprecated endpoint as getLLMProviderModels().
   */

  async saveProviderConfig(data: { 
    provider_key: string; 
    api_key: string; 
    base_url?: string; 
    endpoints?: any; 
    config_name?: string; 
    temperature?: number; 
    max_tokens?: number;
    config_id?: number;
  }): Promise<{ id: number; config_name: string; is_validated: boolean }> {
    const payload: any = {
      provider_key: data.provider_key,
      api_key: data.api_key,
      base_url: data.base_url,
      config_name: data.config_name || data.provider_key,
      temperature: data.temperature,
      max_tokens: data.max_tokens,
      config_id: data.config_id,
    };
    if (data.provider_key === "volcengine" && data.endpoints) {
      payload.volcengine_endpoints = data.endpoints;
    }
    // v2 create/update single config per provider per user
    return this.request("/api/v1/llm/configs", { method: "POST", body: JSON.stringify(payload) });
  }

  async verifyProviderConfig(provider_key: string, api_key: string, base_url?: string, endpoints?: string[]): Promise<{ 
    valid: boolean; 
    message?: string; 
    error?: string;
    available_models?: string[];
    error_details?: {
      status_code?: number;
      error_code?: string | number;
      raw_response?: any;
      provider?: string;
    };
  }> {
    return this.request("/api/v1/llm/validate", {
      method: "POST",
      body: JSON.stringify({
        provider_key,
        api_key,
        base_url,
        volcengine_endpoints: endpoints,
      }),
    });
  }

  async deleteProviderConfig(configId: number): Promise<{ message: string }> {
    return this.request(`/api/v1/llm/configs/${configId}`, { method: "DELETE" });
  }

  // ============================================
  // Crew Builder v2 API Methods
  // ============================================

  // Agent Definitions
  async listAgentDefinitions(includeTemplates: boolean = true): Promise<AgentDefinition[]> {
    return this.request(`/api/v1/crew-builder/agents?include_templates=${includeTemplates}`);
  }

  async createAgentDefinition(data: CreateAgentDefinitionRequest): Promise<AgentDefinition> {
    return this.request("/api/v1/crew-builder/agents", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getAgentDefinition(agentId: number): Promise<AgentDefinition> {
    return this.request(`/api/v1/crew-builder/agents/${agentId}`);
  }

  async updateAgentDefinition(agentId: number, data: Partial<CreateAgentDefinitionRequest>): Promise<AgentDefinition> {
    return this.request(`/api/v1/crew-builder/agents/${agentId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteAgentDefinition(agentId: number): Promise<{ message: string }> {
    return this.request(`/api/v1/crew-builder/agents/${agentId}`, {
      method: "DELETE",
    });
  }

  // Task Definitions
  async listTaskDefinitions(): Promise<TaskDefinition[]> {
    return this.request("/api/v1/crew-builder/tasks");
  }

  async createTaskDefinition(data: CreateTaskDefinitionRequest): Promise<TaskDefinition> {
    return this.request("/api/v1/crew-builder/tasks", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getTaskDefinition(taskId: number): Promise<TaskDefinition> {
    return this.request(`/api/v1/crew-builder/tasks/${taskId}`);
  }

  async updateTaskDefinition(taskId: number, data: Partial<CreateTaskDefinitionRequest>): Promise<TaskDefinition> {
    return this.request(`/api/v1/crew-builder/tasks/${taskId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteTaskDefinition(taskId: number): Promise<{ message: string }> {
    return this.request(`/api/v1/crew-builder/tasks/${taskId}`, {
      method: "DELETE",
    });
  }

  // Crew Definitions
  async listCrewDefinitions(includeTemplates: boolean = true): Promise<CrewDefinition[]> {
    return this.request(`/api/v1/crew-builder/crews?include_templates=${includeTemplates}`);
  }

  async createCrewDefinition(data: CreateCrewDefinitionRequest): Promise<CrewDefinition> {
    return this.request("/api/v1/crew-builder/crews", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getCrewDefinition(crewId: number): Promise<CrewDefinition> {
    return this.request(`/api/v1/crew-builder/crews/${crewId}`);
  }

  async getCrewDetail(crewId: number): Promise<CrewDetailExpanded> {
    return this.request(`/api/v1/crew-builder/crews/${crewId}/detail`);
  }

  async updateCrewDefinition(crewId: number, data: Partial<CreateCrewDefinitionRequest>): Promise<CrewDefinition> {
    return this.request(`/api/v1/crew-builder/crews/${crewId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteCrewDefinition(crewId: number): Promise<{ message: string }> {
    return this.request(`/api/v1/crew-builder/crews/${crewId}`, {
      method: "DELETE",
    });
  }

  // Template Cloning
  async cloneCrew(crewId: number, newName?: string): Promise<CrewDefinition> {
    return this.request(`/api/v1/crew-builder/crews/${crewId}/clone`, {
      method: "POST",
      body: JSON.stringify({ new_name: newName }),
    });
  }

  // Version Control
  async listCrewVersions(crewId: number): Promise<CrewVersion[]> {
    return this.request(`/api/v1/crew-builder/crews/${crewId}/versions`);
  }

  async saveCrewVersion(crewId: number, description?: string): Promise<CrewVersion> {
    return this.request(`/api/v1/crew-builder/crews/${crewId}/versions`, {
      method: "POST",
      body: JSON.stringify({ description }),
    });
  }

  async restoreCrewVersion(crewId: number, versionNumber: number): Promise<CrewDefinition> {
    return this.request(`/api/v1/crew-builder/crews/${crewId}/versions/${versionNumber}/restore`, {
      method: "POST",
    });
  }

  // Runtime Variables & Preflight
  async getCrewVariables(crewId: number): Promise<VariableInfo[]> {
    return this.request(`/api/v1/crew-builder/crews/${crewId}/variables`);
  }

  async preflightCrew(crewId: number, variables: Record<string, any>): Promise<PreflightResult> {
    return this.request(`/api/v1/crew-builder/crews/${crewId}/preflight`, {
      method: "POST",
      body: JSON.stringify(variables),
    });
  }

  // ============================================
  // 4-Tier Loadout System API (Strategy Studio)
  // ============================================

  async getTieredTools(): Promise<TieredToolsResponse> {
    return this.requestWithTimeout<TieredToolsResponse>('/api/v1/crew-builder/tools/tiered', {}, true, 15000);
  }

  async getUserToolsConfig(): Promise<{ config: Record<string, Record<string, boolean>>; message: string }> {
    return this.requestWithTimeout<{ config: Record<string, Record<string, boolean>>; message: string }>('/api/v1/user-tools/config', {}, true, 5000);
  }

  async listUserStrategies(): Promise<UserStrategy[]> {
    return this.request('/api/v1/strategies');
  }

  async createUserStrategy(data: {
    name: string;
    description?: string;
    formula: string;
    category?: string;
    is_public?: boolean;
  }): Promise<{ id: number; name: string; formula: string; message: string }> {
    return this.request('/api/v1/strategies', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getUserStrategy(strategyId: number): Promise<UserStrategy> {
    return this.request(`/api/v1/strategies/${strategyId}`);
  }

  async updateUserStrategy(strategyId: number, data: {
    name?: string;
    description?: string;
    formula?: string;
    category?: string;
    is_active?: boolean;
    is_public?: boolean;
  }): Promise<{ id: number; name: string; message: string }> {
    return this.request(`/api/v1/strategies/${strategyId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteUserStrategy(strategyId: number): Promise<{ message: string }> {
    return this.request(`/api/v1/strategies/${strategyId}`, {
      method: 'DELETE',
    });
  }

  async validateStrategyFormula(formula: string): Promise<StrategyEvaluationResult> {
    return this.request('/api/v1/strategies/validate', {
      method: 'POST',
      body: JSON.stringify({ formula }),
    });
  }

  async evaluateStrategy(strategyId: number, ticker: string): Promise<StrategyEvaluationResult> {
    return this.request(`/api/v1/strategies/evaluate`, {
      method: 'POST',
      body: JSON.stringify({ strategy_id: strategyId, ticker }),
    });
  }

  // ============================================
  // Global Market Data API
  // ============================================

  async getGlobalMarketData(forceRefresh: boolean = false): Promise<MarketDataResponse> {
    const query = forceRefresh ? '?force_refresh=true' : '';
    return this.request(`/api/v1/market/global${query}`, {}, false);
  }

  async getSingleMarket(code: string): Promise<MarketIndex> {
    return this.request(`/api/v1/market/global/${code}`, {}, false);
  }

  async getMarketStatus(): Promise<{
    last_updated: string;
    is_expired: boolean;
    markets_count: number;
    next_update_in_seconds: number;
  }> {
    return this.request('/api/v1/market/status', {}, false);
  }

  async refreshMarketData(): Promise<{ message: string }> {
    return this.request('/api/v1/market/refresh', { method: 'POST' }, false);
  }

  // ============================================
  // Cockpit Global Context API
  // ============================================

  async getCockpitMacroData(forceRefresh: boolean = false): Promise<CockpitMacroResponse> {
    const query = forceRefresh ? '?force_refresh=true' : '';
    return this.request(`/api/v1/market/cockpit/macro${query}`, {}, false);
  }

  async getSingleIndicator(indicatorId: string): Promise<CockpitMacroIndicator> {
    return this.request(`/api/v1/market/cockpit/macro/${indicatorId}`, {}, false);
  }

  async getCockpitStatus(): Promise<{
    last_updated: string;
    is_expired: boolean;
    indicators_count: number;
    next_update_in_seconds: number;
  }> {
    return this.request('/api/v1/market/cockpit/status', {}, false);
  }

  async refreshCockpitData(): Promise<{ message: string }> {
    return this.request('/api/v1/market/cockpit/refresh', { method: 'POST' }, false);
  }

  // ============================================
  // Chart Data APIs
  // ============================================

  async getSparklineData(ticker: string, period: string = '5d', forceRefresh: boolean = false): Promise<SparklineResponse> {
    const params = new URLSearchParams();
    params.set('period', period);
    if (forceRefresh) params.set('force_refresh', 'true');
    return this.request(`/api/v1/charts/sparkline/${ticker}?${params.toString()}`, {}, false);
  }

  // ============================================
  // Quick Analysis APIs (无CrewAI)
  // ============================================

  async runQuickScan(ticker: string, thesis?: string): Promise<QuickScanResponse> {
    return this.request('/api/v1/analysis/quick-scan', {
      method: 'POST',
      body: JSON.stringify({ ticker, thesis })
    });
  }

  async runChartAnalysis(ticker: string, thesis?: string): Promise<ChartAnalysisResponse> {
    return this.request('/api/v1/analysis/chart-analysis', {
      method: 'POST',
      body: JSON.stringify({ ticker, thesis })
    });
  }

  // ============================================
  // Copilot & User Preferences APIs
  // ============================================

  async getUserPreferences(): Promise<UserPreferencesResponse> {
    return this.request('/api/v1/copilot/preferences', {});
  }

  async updateUserPreferences(preferences: {
    /** @deprecated Use default_model_config_id instead */
    default_llm_config_id?: string | null;
    /** New field: UserModelConfig.id for precise model selection */
    default_model_config_id?: number | null;
  }): Promise<UserPreferencesResponse> {
    return this.request('/api/v1/copilot/preferences', {
      method: 'PUT',
      body: JSON.stringify(preferences)
    });
  }

  async getPreferences(): Promise<PreferencesResponse> {
    return this.request('/api/v1/preferences/general', {});
  }

  async updatePreferences(preferences: PreferencesUpdateRequest): Promise<PreferencesResponse> {
    return this.request('/api/v1/preferences/general', {
      method: 'PUT',
      body: JSON.stringify(preferences)
    });
  }

  // ============================================
  // User Notification Preferences API
  // ============================================

  async getNotificationPreferences(): Promise<UserNotificationPreferences> {
    return this.request('/api/v1/preferences/notifications', {});
  }

  async updateNotificationPreferences(
    preferences: UpdateNotificationPreferencesRequest
  ): Promise<UserNotificationPreferences> {
    return this.request('/api/v1/preferences/notifications', {
      method: 'PUT',
      body: JSON.stringify(preferences),
    });
  }

  async unsubscribePushNotifications(): Promise<UserNotificationPreferences> {
    return this.request('/api/v1/preferences/notifications/push-subscription', {
      method: 'DELETE',
    });
  }

  // ============================================
  // Notifications (Webhook) APIs - DEPRECATED
  // System webhooks are now configured via environment variables
  // ============================================

  /** @deprecated System webhooks are now configured via environment variables */
  async getWebhookSettings(): Promise<WebhookSettingsResponse> {
    return this.request('/api/v1/notifications/webhook', {});
  }

  /** @deprecated System webhooks are now configured via environment variables */
  async updateWebhookSettings(payload: WebhookSettingsRequest): Promise<WebhookSettingsResponse> {
    return this.request('/api/v1/notifications/webhook', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  /** @deprecated System webhooks are now configured via environment variables */
  async sendTestWebhook(): Promise<WebhookTestResponse> {
    return this.request('/api/v1/notifications/webhook/test', { method: 'POST' });
  }

  // ============================================
  // LLM Policy Router Methods
  // ============================================

  async getLlmPolicyStatus(): Promise<LLMPolicyStatus> {
    return this.request('/api/v1/llm-policy/status', {});
  }

  async listLlmPolicyProviders(): Promise<LLMPolicyProvider[]> {
    return this.request('/api/v1/llm-policy/providers', {});
  }

  async listByokProfiles(): Promise<LLMUserByokProfileResponse[]> {
    return this.request('/api/v1/llm-policy/byok-profiles', {});
  }

  async upsertByokProfileByTier(
    tier: string,
    payload: LLMUserByokProfileUpdate
  ): Promise<LLMUserByokProfileResponse> {
    return this.request(`/api/v1/llm-policy/byok-profiles/${tier}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  async testByokProfile(tier: string): Promise<LLMUserByokProfileResponse> {
    return this.request(`/api/v1/llm-policy/byok-profiles/${tier}/test`, {
      method: 'POST',
    });
  }

  async deleteByokProfileByTier(tier: string): Promise<void> {
    return this.request(`/api/v1/llm-policy/byok-profiles/${tier}`, {
      method: 'DELETE',
    });
  }

  async listRoutingOverrides(): Promise<LLMRoutingOverrideResponse[]> {
    return this.request('/api/v1/llm-policy/routing-overrides', {});
  }

  async upsertRoutingOverride(
    payload: LLMRoutingOverrideCreate
  ): Promise<LLMRoutingOverrideResponse> {
    return this.request('/api/v1/llm-policy/routing-overrides', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async deleteRoutingOverride(overrideId: number): Promise<void> {
    return this.request(`/api/v1/llm-policy/routing-overrides/${overrideId}`, {
      method: 'DELETE',
    });
  }

  async listVirtualKeys(): Promise<LLMVirtualKeyResponse[]> {
    return this.request('/api/v1/llm-policy/virtual-keys', {});
  }

  async getRoutingPreview(scope: string): Promise<LLMRoutingPreview> {
    return this.request(`/api/v1/llm-policy/routing-preview/${scope}`, {});
  }

  // ============================================
  // Agent Models API Methods
  // ============================================

  async getAgentModels(): Promise<{
    use_own_llm_keys: boolean;
    scenarios: Array<{
      scenario: string;
      scenario_name: string;
      scenario_description: string;
      scenario_icon: string;
      provider_config_id?: number;
      provider_name?: string;
      model_config_id?: number;
      model_name?: string;
      volcengine_endpoint?: string;
      enabled: boolean;
      last_tested_at?: string;
      last_test_status?: string;
      last_test_message?: string;
    }>;
    available_providers: Array<{
      config_id: number;
      provider_key: string;
      provider_name: string;
      is_validated: boolean;
      model_count: number;
      endpoints?: string[];
    }>;
  }> {
    return this.request('/api/v1/agent-models', {});
  }

  async toggleByokMode(enabled: boolean): Promise<{
    success: boolean;
    use_own_llm_keys: boolean;
    message: string;
  }> {
    return this.request('/api/v1/agent-models/toggle-byok', {
      method: 'PUT',
      body: JSON.stringify({ enabled }),
    });
  }

  async getAgentModelProviderModels(providerId: number): Promise<Array<{
    model_config_id: number;
    model_key: string;
    model_name: string;
    context_length?: number;
    volcengine_endpoint_id?: string;
  }>> {
    return this.request(`/api/v1/agent-models/providers/${providerId}/models`, {});
  }

  async updateAgentModelScenario(scenario: string, data: {
    provider_config_id: number;
    model_config_id: number;
    volcengine_endpoint?: string | null;
    enabled: boolean;
  }): Promise<{ message: string }> {
    return this.request(`/api/v1/agent-models/${scenario}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async testAgentModelScenario(scenario: string): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.request(`/api/v1/agent-models/${scenario}/test`, {
      method: 'POST',
    });
  }

  async sendCopilotMessage(message: string, context?: string, enableWebSearch: boolean = true): Promise<CopilotChatResponse> {
    return this.request('/api/v1/copilot/chat', {
      method: 'POST',
      body: JSON.stringify({ message, context, enable_web_search: enableWebSearch })
    });
  }

  async streamCopilotMessage(
    message: string,
    onChunk: (data: { type?: 'thinking' | 'content'; content: string }) => void,
    context?: string,
    enableWebSearch: boolean = true,
    signal?: AbortSignal
  ): Promise<void> {
    const params = new URLSearchParams({
      message,
      enable_web_search: String(enableWebSearch)
    });
    if (context) params.append('context', context);

    const token = getToken();
    
    if (!token) {
      throw new Error('No authentication token found. Please log in first.');
    }
    
    // ✅ 使用相对路径，让 SSE 流式响应走 Next.js 代理
    // 这样无需配置环境变量，自动适配开发/生产环境
    const streamUrl = `/api/v1/copilot/chat/stream?${params.toString()}`;
    
    // 调试日志
    console.debug('[Copilot] Stream URL:', streamUrl);
    console.debug('[Copilot] Environment:', process.env.NODE_ENV);
    
    try {
      const response = await fetch(streamUrl, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache'
        },
        signal
      });

      // 检查 401 未授权错误
      if (response.status === 401) {
        const errorDetail = await response.json().catch(() => ({}));
        clearAuth();
        redirectToLogin();
        throw new Error('Authentication expired, please log in again');
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        const detail = typeof error?.detail === 'string' 
          ? error.detail 
          : error?.message 
          || `HTTP ${response.status}`;
        throw new Error(detail);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('Response body is not readable');

      const decoder = new TextDecoder();
      let buffer = '';
      let retryCount = 0;
      const maxRetries = 3;

      while (true) {
        // 检查是否被中止
        if (signal?.aborted) {
          reader.cancel();
          throw new DOMException('Stream aborted', 'AbortError');
        }

        try {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.content) {
                  // Pass full data object with type (defaults to 'content' for backward compatibility)
                  onChunk({
                    type: data.type || 'content',
                    content: data.content
                  });
                }
                // 重置重试计数
                retryCount = 0;
              } catch (e) {
                // JSON 解析错误可能是分块问题，继续处理
                if (retryCount < maxRetries) {
                  retryCount++;
                  console.warn('Failed to parse SSE data, retrying:', e);
                } else {
                  console.error('Failed to parse SSE data after retries:', e);
                  throw new Error('Data parsing failed after multiple retries');
                }
              }
            }
          }
        } catch (error: any) {
          if (error.name === 'AbortError') {
            throw error;
          }
          throw error;
        }
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        throw new DOMException('Stream aborted by user', 'AbortError');
      }
      throw error;
    }
  }

  async getCopilotHistory(): Promise<CopilotHistoryResponse> {
    return this.request('/api/v1/copilot/history', {});
  }

  async clearCopilotHistory(): Promise<{ message: string }> {
    return this.request('/api/v1/copilot/history', { method: 'DELETE' });
  }

  // ============================================
  // Portfolio Management APIs
  // ============================================

  async searchAssets(request: AssetSearchRequest): Promise<AssetSearchResult[]> {
    return this.request('/api/v1/portfolio/search', {
      method: 'POST',
      body: JSON.stringify(request)
    });
  }

  async getUserAssets(): Promise<UserAssetResponse[]> {
    return this.request('/api/v1/portfolio/assets');
  }

  async addUserAsset(request: AddAssetRequest): Promise<UserAssetResponse> {
    return this.request('/api/v1/portfolio/assets', {
      method: 'POST', 
      body: JSON.stringify(request)
    });
  }

  async updateUserAsset(ticker: string, request: UpdateAssetRequest): Promise<UserAssetResponse> {
    return this.request(`/api/v1/portfolio/assets/${ticker}`, {
      method: 'PUT',
      body: JSON.stringify(request)
    });
  }

  async removeUserAsset(ticker: string): Promise<{ message: string }> {
    return this.request(`/api/v1/portfolio/assets/${ticker}`, {
      method: 'DELETE'
    });
  }

  async getPortfolioSummary(): Promise<PortfolioSummary> {
    return this.request('/api/v1/portfolio/summary');
  }

  // ============================================
  // User Cockpit Indicator Management APIs
  // ============================================

  async getUserCockpitIndicators(): Promise<UserCockpitIndicatorResponse[]> {
    return this.request('/api/v1/market/cockpit/user-indicators');
  }

  async addUserCockpitIndicator(request: UserCockpitIndicatorRequest): Promise<{ message: string }> {
    return this.request('/api/v1/market/cockpit/user-indicators', {
      method: 'POST',
      body: JSON.stringify(request)
    });
  }

  async removeUserCockpitIndicator(indicatorId: string): Promise<{ message: string }> {
    return this.request(`/api/v1/market/cockpit/user-indicators/${indicatorId}`, {
      method: 'DELETE'
    });
  }

  async getAvailableCockpitIndicators(): Promise<AvailableIndicator[]> {
    return this.request('/api/v1/market/cockpit/available-indicators');
  }

  async updateIndicatorOrder(indicatorId: string, newOrder: number): Promise<{ message: string }> {
    return this.request(`/api/v1/market/cockpit/user-indicators/${indicatorId}/order`, {
      method: 'PUT',
      body: JSON.stringify({ new_order: newOrder })
    });
  }

  async getPersonalizedCockpitData(forceRefresh: boolean = false): Promise<CockpitMacroResponse> {
    const query = forceRefresh ? '?force_refresh=true' : '';
    return this.request(`/api/v1/market/cockpit/macro/personalized${query}`);
  }

  // ============================================
  // User Strategies API
  // ============================================

  async listStrategies(category?: string, includePublic = false): Promise<any[]> {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (includePublic) params.append('include_public', 'true');
    return this.request(`/api/v1/strategies?${params.toString()}`);
  }

  async createStrategy(data: any): Promise<any> {
    return this.request('/api/v1/strategies', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getStrategy(id: number): Promise<any> {
    return this.request(`/api/v1/strategies/${id}`);
  }

  async updateStrategy(id: number, data: any): Promise<any> {
    return this.request(`/api/v1/strategies/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteStrategy(id: number): Promise<void> {
    return this.request(`/api/v1/strategies/${id}`, { method: 'DELETE' });
  }

  async batchEvaluateStrategy(strategyId: number, tickers: string[]): Promise<any> {
    return this.request(`/api/v1/strategies/batch-evaluate?strategy_id=${strategyId}`, {
      method: 'POST',
      body: JSON.stringify(tickers),
    });
  }

  async getPopularStrategies(category?: string, limit = 10): Promise<any[]> {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    params.append('limit', limit.toString());
    return this.request(`/api/v1/strategies/market/popular?${params.toString()}`);
  }

  async cloneStrategy(strategyId: number, newName?: string): Promise<any> {
    const params = newName ? `?new_name=${encodeURIComponent(newName)}` : '';
    return this.request(`/api/v1/strategies/${strategyId}/clone${params}`, { method: 'POST' });
  }

  // ============================================
  // Unified Tool Registry API v2
  // ============================================

  async listUnifiedTools(params?: {
    source?: string;
    tier?: string;
    enabled_only?: boolean;
    server_key?: string;
  }): Promise<UnifiedToolsResponse> {
    const queryParams = new URLSearchParams();
    if (params?.source) queryParams.append('source', params.source);
    if (params?.tier) queryParams.append('tier', params.tier);
    if (params?.enabled_only) queryParams.append('enabled_only', 'true');
    if (params?.server_key) queryParams.append('server_key', params.server_key);
    return this.request(`/api/v1/tool-registry/tools?${queryParams.toString()}`);
  }

  async toggleUnifiedTool(toolKey: string, enabled: boolean): Promise<ToggleToolResponse> {
    return this.request(`/api/v1/tool-registry/tools/${encodeURIComponent(toolKey)}/toggle`, {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    });
  }

  async listMCPServersV2(): Promise<MCPServerStatus[]> {
    return this.request('/api/v1/tool-registry/servers');
  }

  async subscribeMCPServer(serverKey: string, enabled: boolean): Promise<{ server_key: string; is_subscribed: boolean; message: string }> {
    return this.request(`/api/v1/tool-registry/servers/${encodeURIComponent(serverKey)}/subscribe?enabled=${enabled}`, {
      method: 'POST',
    });
  }

  async resetToolPreferences(): Promise<{ message: string }> {
    return this.request('/api/v1/tool-registry/reset', { method: 'POST' });
  }

  async listToolSources(): Promise<any[]> {
    return this.request('/api/v1/tool-registry/sources');
  }

  async listToolTiers(): Promise<any[]> {
    return this.request('/api/v1/tool-registry/tiers');
  }

  // ============================================
  // MCP Tool API Key Verification
  // ============================================

  async verifyServerAPIKey(serverKey: string, apiKey: string): Promise<{ valid: boolean; message: string }> {
    return this.request(`/api/v1/tool-registry/servers/${encodeURIComponent(serverKey)}/verify`, {
      method: 'POST',
      body: JSON.stringify({ api_key: apiKey }),
    });
  }

  async verifyToolAPIKey(toolKey: string, apiKey: string): Promise<{ valid: boolean; message: string }> {
    return this.request(`/api/v1/tool-registry/tools/${encodeURIComponent(toolKey)}/verify`, {
      method: 'POST',
      body: JSON.stringify({ api_key: apiKey }),
    });
  }

  // ============================================
  // Tool Usage Statistics API
  // ============================================

  async getToolUsageStats(params?: {
    days?: number;
    limit?: number;
  }): Promise<ToolUsageStatsResponse> {
    const queryParams = new URLSearchParams();
    if (params?.days) queryParams.append('days', params.days.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    
    return this.request(`/api/v1/tool-usage/stats?${queryParams.toString()}`);
  }

  async recordToolUsage(toolKey: string): Promise<{ message: string }> {
    return this.request(`/api/v1/tool-usage/record?tool_key=${encodeURIComponent(toolKey)}`, {
      method: 'POST'
    });
  }

  async getTrendingTools(params?: {
    days?: number;
    limit?: number;
  }): Promise<TrendingToolsResponse> {
    const queryParams = new URLSearchParams();
    if (params?.days) queryParams.append('days', params.days.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    
    return this.request(`/api/v1/tool-usage/trending?${queryParams.toString()}`);
  }

  // ============================================
  // Library (资产情报局) API
  // ============================================

  async getLibraryAssets(): Promise<LibraryAssetGroup[]> {
    return this.request('/api/v1/library/assets');
  }

  async getLibraryTimeline(params?: { ticker?: string; days?: number }): Promise<LibraryTimelineEntry[]> {
    const queryParams = new URLSearchParams();
    if (params?.ticker) queryParams.append('ticker', params.ticker);
    if (params?.days) queryParams.append('days', params.days.toString());
    return this.request(`/api/v1/library/timeline?${queryParams.toString()}`);
  }

  async listLibraryInsights(params?: {
    ticker?: string;
    source_type?: string;
    sentiment?: string;
    signal?: string;
    limit?: number;
    offset?: number;
  }): Promise<LibraryInsight[]> {
    const queryParams = new URLSearchParams();
    if (params?.ticker) queryParams.append('ticker', params.ticker);
    if (params?.source_type) queryParams.append('source_type', params.source_type);
    if (params?.sentiment) queryParams.append('sentiment', params.sentiment);
    if (params?.signal) queryParams.append('signal', params.signal);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    return this.request(`/api/v1/library/insights?${queryParams.toString()}`);
  }

  async getLibraryInsightDetail(insightId: number): Promise<LibraryInsightDetail> {
    return this.request(`/api/v1/library/insights/${insightId}`);
  }

  async toggleLibraryInsightFavorite(insightId: number, isFavorite: boolean): Promise<{ success: boolean; is_favorite: boolean }> {
    return this.request(`/api/v1/library/insights/${insightId}/favorite?is_favorite=${isFavorite}`, { method: 'POST' });
  }

  async markLibraryInsightAsRead(insightId: number): Promise<{ success: boolean }> {
    return this.request(`/api/v1/library/insights/${insightId}/read`, { method: 'POST' });
  }

  async getLibraryStats(): Promise<LibraryStats> {
    return this.request('/api/v1/library/stats');
  }

  // Ingest endpoints (for Cockpit/Workbench integration)
  async ingestQuickScan(data: {
    ticker: string;
    title: string;
    summary: string;
    sentiment: string;
    sentiment_score?: number;
    key_metrics?: Record<string, any>;
    signal?: string;
    target_price?: number;
    stop_loss?: number;
    content?: string;
    raw_data?: Record<string, any>;
    tags?: string[];
  }): Promise<{ insight_id: number; message: string }> {
    return this.request('/api/v1/library/ingest/quick-scan', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async ingestTechnicalDiagnostic(data: {
    ticker: string;
    title: string;
    summary: string;
    sentiment: string;
    sentiment_score?: number;
    key_metrics?: Record<string, any>;
    signal?: string;
    content?: string;
    raw_data?: Record<string, any>;
    tags?: string[];
  }): Promise<{ insight_id: number; message: string }> {
    return this.request('/api/v1/library/ingest/technical-diagnostic', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async ingestCrewAnalysis(data: {
    ticker: string;
    crew_name: string;
    run_id: string;
    title: string;
    summary: string;
    content: string;
    sentiment?: string;
    sentiment_score?: number;
    signal?: string;
    key_metrics?: Record<string, any>;
    tags?: string[];
    artifacts?: Array<{
      file_name: string;
      file_type: string;
      storage_path: string;
      file_size?: number;
      description?: string;
    }>;
    traces?: Array<{
      agent_name?: string;
      action_type: string;
      content?: string;
      step_order?: number;
      input_data?: Record<string, any>;
      output_data?: Record<string, any>;
      tokens_used?: number;
      duration_ms?: number;
      model_name?: string;
    }>;
  }): Promise<{ insight_id: number; message: string }> {
    return this.request('/api/v1/library/ingest/crew-analysis', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getExpressionEngineInfo(): Promise<any> {
    return this.request('/api/v1/tool-registry/expression-engine/info');
  }

  // ============================================
  // Cockpit Real-Time Dashboard API (新架构)
  // ============================================

  async getCockpitDashboard(forceRefresh: boolean = false): Promise<{
    markets: Array<{
      id: string;
      name: string;
      value: string;
      change: string;
      change_percent: number;
      trend: 'up' | 'down';
      critical: boolean;
      type: string;
    }>;
    assets: Array<{
      ticker: string;
      name?: string;
      asset_type?: string;
      exchange?: string;
      currency?: string;
      notes?: string;
      target_price?: number;
      price?: number;
      price_local?: number;
      currency_local?: string;
      change_percent?: number;
      change_value?: number;
      volume?: number;
      market_cap?: number;
      is_market_open?: boolean;
      source: 'cache' | 'database' | 'pending';
      last_updated?: string;
    }>;
    last_updated: string;
    cache_expired: boolean;
  }> {
    const query = forceRefresh ? '?force_refresh=true' : '';
    return this.request(`/api/v1/cockpit/dashboard${query}`);
  }

  async getAssetPrice(ticker: string): Promise<{
    ticker: string;
    name?: string;
    price?: number;
    change_percent?: number;
    change_value?: number;
    volume?: number;
    source: 'cache' | 'database' | 'pending';
    last_updated?: string;
  }> {
    return this.request(`/api/v1/cockpit/assets/${ticker}/price`);
  }

  async subscribeAsset(ticker: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/api/v1/cockpit/assets/${ticker}/subscribe`, { method: 'POST' });
  }

  async unsubscribeAsset(ticker: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/api/v1/cockpit/assets/${ticker}/subscribe`, { method: 'DELETE' });
  }

  // ============================================
  // User Tools Configuration API
  // ============================================

  async updateUserToolsConfig(config: Record<string, Record<string, boolean>>): Promise<{ config: Record<string, Record<string, boolean>>; message: string }> {
    return this.request('/api/v1/user-tools/config', {
      method: 'PUT',
      body: JSON.stringify({ config }),
    });
  }

  async resetUserToolsConfig(): Promise<{ config: Record<string, Record<string, boolean>>; message: string }> {
    return this.requestWithTimeout<{ config: Record<string, Record<string, boolean>>; message: string }>('/api/v1/user-tools/config/reset', { method: 'POST' }, true, 5000);
  }

  async getAvailableTools(): Promise<{
    categories: Array<{
      tier: string;
      title: string;
      tools: Array<{
        key: string;
        name: string;
        description: string;
        icon: string;
        enabled: boolean;
      }>;
    }>;
  }> {
    return this.request('/api/v1/user-tools/available');
  }

  async toggleTool(tier: string, toolKey: string): Promise<{ config: Record<string, Record<string, boolean>>; message: string }> {
    return this.request(`/api/v1/user-tools/toggle?tier=${tier}&tool_key=${toolKey}`, { method: 'POST' });
  }

  // Tracking API methods
  async getLiveStatus(jobId: string): Promise<LiveStatus> {
    return this.request(`/api/v1/tracking/${jobId}/live`);
  }

  async getCompletionReport(jobId: string): Promise<CompletionReport> {
    return this.request(`/api/v1/tracking/${jobId}/report`);
  }

  async listTrackingHistory(limit: number = 30): Promise<TrackingHistoryItem[]> {
    return this.request(`/api/v1/tracking/history?limit=${limit}`);
  }

  // ============================================
  // Provider Management API
  // ============================================

  async listProviders(): Promise<any[]> {
    return this.request('/api/v1/providers');
  }

  async getProvider(providerId: number): Promise<any> {
    return this.request(`/api/v1/providers/${providerId}`);
  }

  async discoverProviderTools(
    providerId: number,
    params?: { refresh?: boolean }
  ): Promise<{ tools: string[]; error?: string }> {
    const query = params?.refresh ? "?refresh=true" : "";
    return this.request(`/api/v1/providers/${providerId}/discover${query}`);
  }

  async createProvider(data: {
    provider_key: string;
    provider_type: 'mcp' | 'builtin';
    url?: string;
    config?: Record<string, any>;
  }): Promise<{ provider_id: number; discovered_tools: any[]; message: string }> {
    return this.request('/api/v1/providers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async submitCapabilityMapping(providerId: number, mappings: Record<string, string>): Promise<{ message: string; mapped_count: number }> {
    return this.request(`/api/v1/providers/${providerId}/mapping`, {
      method: 'POST',
      body: JSON.stringify({ mappings }),
    });
  }

  async enableProvider(providerId: number): Promise<{ message: string }> {
    return this.request(`/api/v1/providers/${providerId}/enable`, { method: 'POST' });
  }

  async disableProvider(providerId: number): Promise<{ message: string }> {
    return this.request(`/api/v1/providers/${providerId}/disable`, { method: 'POST' });
  }

  async deleteProvider(providerId: number): Promise<{ message: string }> {
    return this.request(`/api/v1/providers/${providerId}`, { method: 'DELETE' });
  }

  async healthcheckProvider(providerId: number): Promise<{
    provider_id: number;
    healthy: boolean;
    latency_ms: number;
    error: string | null;
    last_health_check: string;
    metrics_24h?: Record<string, any>;
    credential_status?: {
      has_credential: boolean;
      is_verified: boolean;
      requires_credential: boolean;
      uses_env_var: boolean;
    };
  }> {
    return this.request(`/api/v1/providers/${providerId}/healthcheck`, { method: 'POST' });
  }

  // ============================================
  // Capability Provider Priority Management
  // ============================================

  /**
   * Get all providers that implement a specific capability, sorted by priority.
   */
  async getCapabilityProviders(capabilityId: string): Promise<{
    capability_id: string;
    providers: Array<{
      provider_id: number;
      provider_key: string;
      provider_type: 'mcp' | 'builtin';
      priority: number;
      healthy: boolean;
      enabled: boolean;
      raw_tool_name: string | null;
    }>;
  }> {
    return this.request(`/api/v1/providers/capabilities/${capabilityId}/providers`);
  }

  /**
   * Update provider priorities for a specific capability.
   * Higher priority = tried first when resolving the capability.
   */
  async updateCapabilityPriorities(
    capabilityId: string,
    priorities: Array<{ provider_id: number; priority: number }>
  ): Promise<{
    capability_id: string;
    updated_count: number;
    message: string;
  }> {
    return this.request(`/api/v1/providers/capabilities/${capabilityId}/priorities`, {
      method: 'PUT',
      body: JSON.stringify({ priorities }),
    });
  }

  // ============================================
  // Provider API Key Management
  // ============================================

  async saveProviderApiKey(providerId: number, apiKey: string): Promise<{
    provider_id: number;
    provider_key: string;
    has_credential: boolean;
    is_verified: boolean;
    message: string;
  }> {
    return this.request(`/api/v1/providers/${providerId}/save-api-key`, {
      method: 'POST',
      body: JSON.stringify({ api_key: apiKey }),
    });
  }

  async deleteProviderApiKey(providerId: number): Promise<{
    provider_id: number;
    provider_key: string;
    deleted: boolean;
    message: string;
  }> {
    return this.request(`/api/v1/providers/${providerId}/api-key`, {
      method: 'DELETE',
    });
  }

  // ============================================
  // Provider Multi-Credential Management (for MCP providers like OpenBB)
  // ============================================

  async getProviderCredentials(providerId: number): Promise<{
    provider_id: number;
    provider_key: string;
    credentials: Array<{
      key: string;
      display_name: string;
      description: string;
      required: boolean;
      get_key_url: string;
      has_credential: boolean;
      is_verified: boolean;
      uses_env_var: boolean;
    }>;
  }> {
    return this.request(`/api/v1/providers/${providerId}/credentials`);
  }

  async saveProviderCredential(
    providerId: number,
    credentialType: string,
    apiKey: string
  ): Promise<{
    provider_id: number;
    provider_key: string;
    credential_type: string;
    has_credential: boolean;
    is_verified: boolean;
    message: string;
  }> {
    return this.request(`/api/v1/providers/${providerId}/credentials/${credentialType}`, {
      method: 'POST',
      body: JSON.stringify({ api_key: apiKey }),
    });
  }

  async deleteProviderCredential(providerId: number, credentialType: string): Promise<{
    provider_id: number;
    provider_key: string;
    credential_type: string;
    deleted: boolean;
    message: string;
  }> {
    return this.request(`/api/v1/providers/${providerId}/credentials/${credentialType}`, {
      method: 'DELETE',
    });
  }

  // ============================================
  // Skills Catalog API
  // ============================================

  async listSkills(params?: { kind?: string; search?: string }): Promise<any[]> {
    const query = new URLSearchParams(params as any).toString();
    const response = await this.request<{
      capabilities: any[];
      presets: any[];
      strategies: any[];
      skillsets: any[];
    }>(`/api/v1/skills/catalog${query ? `?${query}` : ''}`);

    // Flatten the grouped response into a single array
    return [
      ...response.capabilities,
      ...response.presets,
      ...response.strategies,
      ...response.skillsets,
    ];
  }

  async getSkill(skillKey: string): Promise<any> {
    return this.request(`/api/v1/skills/${skillKey}`);
  }

  async createSkill(data: {
    skill_key?: string;
    kind: string;
    name?: string;
    title?: string;
    description?: string;
    capability_id?: string;
    capability_keys?: string[];
    tool_filters?: Record<string, any>;
    invocation?: Record<string, any>;
    args_schema?: any;
  }): Promise<any> {
    return this.request('/api/v1/skills', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async toggleSkill(skillKey: string, enabled: boolean): Promise<{ skill_key: string; is_enabled: boolean }> {
    return this.request(`/api/v1/skills/${skillKey}/toggle`, {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    });
  }

  /**
   * Get the complete skill catalog (grouped by Kind)
   * Reuses the existing listSkills API, but performs grouping on the client side
   */
  async getSkillCatalog(params?: { kind?: string; search?: string }): Promise<SkillCatalogResponse> {
    const allSkills = await this.listSkills(params);

    // Client-side grouping (API returns flat array)
    return {
      capabilities: allSkills.filter(s => s.kind === 'capability'),
      presets: allSkills.filter(s => s.kind === 'preset'),
      strategies: allSkills.filter(s => s.kind === 'strategy'),
      skillsets: allSkills.filter(s => s.kind === 'skillset'),
    };
  }

  // ============================================
  // Billing & Subscription API
  // ============================================

  async getSubscription(): Promise<any> {
    return this.request('/api/v1/billing/subscription');
  }

  async getInvoices(page: number = 1, limit: number = 20): Promise<any> {
    return this.request(`/api/v1/billing/invoices?page=${page}&limit=${limit}`);
  }

  async createCheckoutSession(priceId: string, successUrl: string, cancelUrl: string): Promise<any> {
    return this.request('/api/v1/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({
        price_id: priceId,
        success_url: successUrl,
        cancel_url: cancelUrl,
      }),
    });
  }

  async createPortalSession(returnUrl: string): Promise<any> {
    return this.request('/api/v1/billing/portal', {
      method: 'POST',
      body: JSON.stringify({
        return_url: returnUrl,
      }),
    });
  }

  // ============================================
  // Security & Sessions API
  // ============================================

  async get2FAStatus(): Promise<any> {
    return this.request('/api/v1/security/2fa/status');
  }

  async setup2FA(method: 'totp' | 'sms' = 'totp'): Promise<any> {
    return this.request('/api/v1/security/2fa/setup', {
      method: 'POST',
      body: JSON.stringify({ method }),
    });
  }

  async verify2FA(code: string): Promise<any> {
    return this.request('/api/v1/security/2fa/verify', {
      method: 'POST',
      body: JSON.stringify({ code }),
    });
  }

  async disable2FA(password: string, code: string): Promise<any> {
    return this.request('/api/v1/security/2fa/disable', {
      method: 'POST',
      body: JSON.stringify({ password, code }),
    });
  }

  async getSessions(): Promise<any> {
    return this.request('/api/v1/security/sessions');
  }

  async revokeSession(sessionId: number): Promise<any> {
    return this.request('/api/v1/security/sessions/revoke', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    });
  }

  async revokeAllSessions(): Promise<any> {
    return this.request('/api/v1/security/sessions/revoke-all', { method: 'POST' });
  }

  async getLoginHistory(limit: number = 30): Promise<any> {
    return this.request(`/api/v1/security/login-history?limit=${limit}`);
  }

  // ============================================
  // Privacy APIs (Data Export & Account Deletion)
  // ============================================

  async getPrivacyStatus(): Promise<import('./types').PrivacyStatusResponse> {
    return this.request('/api/v1/privacy/status', {});
  }

  async requestDataExport(
    request: import('./types').DataExportRequest
  ): Promise<import('./types').DataExportJobResponse> {
    return this.request('/api/v1/privacy/export', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async listDataExports(limit: number = 10): Promise<import('./types').DataExportListResponse> {
    return this.request(`/api/v1/privacy/export?limit=${limit}`, {});
  }

  async getDataExportJob(jobId: number): Promise<import('./types').DataExportJobResponse> {
    return this.request(`/api/v1/privacy/export/${jobId}`, {});
  }

  async requestAccountDeletion(
    request: import('./types').AccountDeletionRequest
  ): Promise<import('./types').AccountDeletionResponse> {
    return this.request('/api/v1/privacy/deletion', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getDeletionStatus(): Promise<import('./types').AccountDeletionResponse> {
    return this.request('/api/v1/privacy/deletion', {});
  }

  async cancelAccountDeletion(): Promise<import('./types').AccountDeletionResponse> {
    return this.request('/api/v1/privacy/deletion', { method: 'DELETE' });
  }
}

// Re-export all types for backward compatibility
export * from './types';

export const apiClient = new ApiClient();

// Helper function to build API URLs (for use with SWR/fetch)
export const buildApiUrl = (endpoint: string): string => {
  const base = API_BASE_URL || "";
  return `${base}${endpoint}`;
};

// Simple fetcher for SWR that uses the API client
export const fetcher = async <T>(url: string): Promise<T> => {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error?.detail || `HTTP ${response.status}`);
  }

  return response.json();
};

export default apiClient;
