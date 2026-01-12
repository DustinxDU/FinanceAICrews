/**
 * Type definitions for the Unified Skills System
 *
 * Provides interfaces for Providers and Skills tabs in the Tools page
 */

export type ProviderType = 'mcp' | 'builtin';
export type SkillKind = 'capability' | 'preset' | 'strategy' | 'skillset';
// Legacy alias for backward compatibility
export type LegacySkillKind = SkillKind | 'workflow';

export interface Provider {
  id: number;
  provider_key: string;
  provider_type: ProviderType;
  url: string | null;
  config: Record<string, any> | null;
  enabled: boolean;
  healthy: boolean;
  last_health_check: string | null;
  priority: number;
  capabilities: string[];  // Array of capability_ids
}

export interface ProviderCapabilityMapping {
  id: number;
  provider_id: number;
  capability_id: string;
  raw_tool_name: string | null;
  config: Record<string, any> | null;
}

export interface Skill {
  skill_key: string;
  kind: SkillKind;
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
  invocation?: Record<string, any> | null;  // Contains required_capabilities for preset/strategy/skillset
}

export interface CreateProviderRequest {
  provider_key: string;
  provider_type: ProviderType;
  url?: string;
  config?: Record<string, any>;
}

export interface CreateSkillRequest {
  skill_key: string;
  kind: SkillKind;
  capability_id: string;
  title: string;
  description?: string;
  icon?: string;
  tags?: string[];
  invocation: Record<string, any>;
  args_schema?: Record<string, any>;
}

export interface UpdateSkillRequest {
  title?: string;
  description?: string;
  icon?: string;
  tags?: string[];
  invocation?: Record<string, any>;
  is_active?: boolean;
}

// Capability Provider Priority Types
export interface CapabilityProviderInfo {
  provider_id: number;
  provider_key: string;
  provider_type: ProviderType;
  priority: number;
  healthy: boolean;
  enabled: boolean;
  raw_tool_name: string | null;
}

export interface CapabilityProvidersResponse {
  capability_id: string;
  providers: CapabilityProviderInfo[];
}

export interface UpdatePriorityItem {
  provider_id: number;
  priority: number;
}

export interface UpdatePriorityRequest {
  priorities: UpdatePriorityItem[];
}
