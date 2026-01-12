"use client";

import React, { useState, useEffect, useMemo } from "react";
import ReactDOM from "react-dom";
import { 
  X, Search, Check, Database, Calculator, Globe, Sparkles,
  ChevronDown, ChevronRight, Loader2, Info, Server, FileText,
  TrendingUp, Activity, BarChart2, Zap, ExternalLink,
  TrendingUp as TrendingUpIcon
} from "lucide-react";
import apiClient, { AgentLoadout, UnifiedTool, ToolTierGroup } from "@/lib/api";
import { createEmptyLoadout } from "@/lib/types";
import { ToolCard } from "./ToolCard";

// ==================== Types ====================
interface ToolItem {
  id: string;           // Namespaced ID: "tier:key"
  name: string;
  display_name: string;
  description: string;
  category: string;
  tier: 'data' | 'quant' | 'external' | 'strategy';
  enabled: boolean;     // Whether user has enabled this in extension
}

interface ToolSelectorFullModalProps {
  isOpen: boolean;
  onClose: () => void;
  loadout?: AgentLoadout;
  onSave: (loadout: AgentLoadout) => void;
}

// ==================== Constants ====================
const TIER_CONFIG = {
  data: {
    label: '📂 Data Feeds',
    description: 'Market data, fundamentals, news feeds',
    color: 'blue',
    icon: Database,
  },
  quant: {
    label: '🧠 Quant Skills',
    description: 'Technical indicators and analysis tools',
    color: 'purple',
    icon: Calculator,
  },
  external: {
    label: '🌍 External Access',
    description: 'Web search, scraping, external APIs',
    color: 'orange',
    icon: Globe,
  },
  strategy: {
    label: '💎 Strategies',
    description: 'User-defined Level-2 trading formulas',
    color: 'emerald',
    icon: Sparkles,
  },
};

// Recommended tools based on agent roles (using tool_key format)
const RECOMMENDED_TOOLS: Record<string, string[]> = {
  data: ['mcp:akshare:stock_zh_a_hist', 'mcp:yfinance:stock_info', 'mcp:openbb:economy'],
  quant: ['quant:indicator:rsi', 'quant:indicator:macd', 'quant:indicator:ma', 'quant:indicator:bollinger'],
  external: ['crewai:search:serper', 'crewai:web:scrape'],
  strategy: ['user:strategy'],
};

// Trending/popular tools (using tool_key format)
const TRENDING_TOOLS: string[] = [
  'mcp:akshare:stock_zh_a_hist',
  'mcp:yfinance:stock_info',
  'quant:indicator:rsi',
  'quant:indicator:macd',
  'crewai:search:serper',
];

// ==================== Component ====================
export function ToolSelectorFullModal({
  isOpen,
  onClose,
  loadout,
  onSave,
}: ToolSelectorFullModalProps) {
  const [activeTier, setActiveTier] = useState<'data' | 'quant' | 'external' | 'strategy'>('data');
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [localLoadout, setLocalLoadout] = useState<AgentLoadout>(loadout || createEmptyLoadout());
  const [isLoading, setIsLoading] = useState(true);
  
  // Unified tools from v2 API
  const [unifiedTools, setUnifiedTools] = useState<ToolTierGroup[]>([]);

  // Load unified tools from v2 API
  useEffect(() => {
    if (!isOpen) return;
    
    console.log('[ToolSelectorFullModal] useEffect triggered, isOpen:', isOpen);
    setIsLoading(true);
    
    // Load all tools using unified v2 API
    console.log('[ToolSelectorFullModal] Fetching tools from v2 API...');
    apiClient.listUnifiedTools()
      .then((response) => {
        console.log('[ToolSelectorFullModal] Unified tools response:', response);
        setUnifiedTools(response.tiers);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error('[ToolSelectorFullModal] listUnifiedTools error:', err);
        setUnifiedTools([]);
        setIsLoading(false);
      });
    
    // Reset local loadout when modal opens
    setLocalLoadout(loadout || createEmptyLoadout());
  }, [isOpen]);

  // Get tools for current tier from unified tools
  const currentTierTools = useMemo(() => {
    const tierGroup = unifiedTools.find(t => t.tier === activeTier);
    if (!tierGroup) return [];
    
    // Only show user-enabled tools
    let tools: ToolItem[] = tierGroup.tools
      .filter(t => t.user_enabled && t.is_active)
      .map(t => ({
        id: t.key,
        name: t.key,
        display_name: t.name,
        description: t.description,
        category: t.category,
        tier: t.tier,
        enabled: t.user_enabled && t.is_active,
      }));
    
    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      tools = tools.filter(t => 
        t.name.toLowerCase().includes(query) ||
        t.display_name.toLowerCase().includes(query) ||
        t.description.toLowerCase().includes(query)
      );
    }
    
    // Apply category filter
    if (categoryFilter !== 'All') {
      tools = tools.filter(t => t.category === categoryFilter);
    }
    
    return tools;
  }, [activeTier, unifiedTools, searchQuery, categoryFilter]);

  // Get categories for current tier
  const categories = useMemo(() => {
    const cats = new Set<string>();
    currentTierTools.forEach(t => cats.add(t.category));
    return ['All', ...Array.from(cats)];
  }, [currentTierTools]);

  // Check if tool is selected
  const isToolSelected = (toolId: string, tier: 'data' | 'quant' | 'external' | 'strategy') => {
    const tierKey = tier === 'strategy' ? 'strategies' : `${tier}_tools` as keyof AgentLoadout;
    return (localLoadout[tierKey] || []).includes(toolId);
  };

  // Toggle tool selection
  const toggleTool = (toolId: string, tier: 'data' | 'quant' | 'external' | 'strategy') => {
    const tierKey = tier === 'strategy' ? 'strategies' : `${tier}_tools` as keyof AgentLoadout;
    
    setLocalLoadout(prev => {
      const current = prev[tierKey] || [];
      const isSelected = current.includes(toolId);
      return {
        ...prev,
        [tierKey]: isSelected 
          ? current.filter((id: string) => id !== toolId)
          : [...current, toolId],
      };
    });
  };

  // Count selected tools per tier
  const getSelectedCount = (tier: 'data' | 'quant' | 'external' | 'strategy') => {
    const tierKey = tier === 'strategy' ? 'strategies' : `${tier}_tools` as keyof AgentLoadout;
    return (localLoadout[tierKey] || []).length;
  };

  // Check if tool is recommended for current tier
  const isRecommendedTool = (tool: ToolItem, tier: string): boolean => {
    const recommended = RECOMMENDED_TOOLS[tier] || [];
    return recommended.some(r => tool.name.includes(r) || tool.display_name.includes(r));
  };

  // Check if tool is trending/popular (using tool_key)
  const isTrendingTool = (toolName: string): boolean => {
    return TRENDING_TOOLS.includes(toolName);
  };

  // Handle save
  const handleSave = () => {
    console.log('[ToolSelectorFullModal] Saving loadout:', localLoadout);
    onSave(localLoadout);
    onClose();
  };

  if (!isOpen) return null;

  const TierIcon = TIER_CONFIG[activeTier].icon;

  // 使用 React Portal 将模态框渲染到 document.body，避免被父容器的 overflow 裁剪
  const modalContent = (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm p-8">
      <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-2xl w-full max-w-5xl h-[75vh] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200 flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-[var(--border-color)] flex justify-between items-center shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-900/30 rounded-lg text-blue-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-lg">Configure Agent Tools</h3>
              <p className="text-xs text-[var(--text-secondary)]">
                Select tools from your enabled extensions
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-[var(--text-secondary)] hover:text-white p-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left Sidebar - Tier Tabs */}
          <div className="w-56 border-r border-[var(--border-color)] p-4 space-y-2 shrink-0">
            {(Object.keys(TIER_CONFIG) as Array<keyof typeof TIER_CONFIG>).map((tier) => {
              const config = TIER_CONFIG[tier];
              const Icon = config.icon;
              const count = getSelectedCount(tier);
              const isActive = activeTier === tier;
              
              return (
                <button
                  key={tier}
                  onClick={() => {
                    setActiveTier(tier);
                    setCategoryFilter('All');
                  }}
                  className={`w-full text-left p-3 rounded-lg transition-all ${
                    isActive 
                      ? `bg-${config.color}-900/30 border border-${config.color}-500/50` 
                      : 'hover:bg-[var(--bg-card)] border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Icon className={`w-4 h-4 ${isActive ? `text-${config.color}-400` : 'text-[var(--text-secondary)]'}`} />
                    <span className={`text-sm font-medium ${isActive ? 'text-white' : 'text-[var(--text-secondary)]'}`}>
                      {config.label}
                    </span>
                    {count > 0 && (
                      <span className={`ml-auto text-xs px-1.5 py-0.5 rounded bg-${config.color}-900/50 text-${config.color}-400`}>
                        {count}
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-[var(--text-secondary)] mt-1 ml-6">
                    {config.description}
                  </p>
                </button>
              );
            })}
          </div>

          {/* Main Content */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Search & Filter Bar */}
            <div className="p-4 border-b border-[var(--border-color)] space-y-3 shrink-0">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-secondary)]" />
                <input
                  type="text"
                  placeholder="Search tools..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg pl-10 pr-4 py-2 text-sm outline-none focus:border-[var(--accent-blue)]"
                />
              </div>
              
              <div className="flex items-center gap-2 flex-wrap">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setCategoryFilter(cat)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors capitalize ${
                      categoryFilter === cat 
                        ? 'bg-[var(--accent-blue)] text-white' 
                        : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-white'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* Tools Grid */}
            <div className="flex-1 overflow-y-auto p-4">
              {isLoading ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="w-6 h-6 animate-spin text-[var(--text-secondary)]" />
                </div>
              ) : currentTierTools.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <Info className="w-12 h-12 text-[var(--text-secondary)] mb-4" />
                  <h4 className="font-medium mb-2">No tools available</h4>
                  <p className="text-sm text-[var(--text-secondary)] max-w-md">
                    {activeTier === 'data' && 'No MCP data tools are currently enabled.'}
                    {activeTier === 'quant' && 'Enable quant tools in the Extension page first.'}
                    {activeTier === 'external' && 'Enable CrewAI tools in the Extension page first.'}
                    {activeTier === 'strategy' && 'Create strategies in the Extension page first.'}
                  </p>
                  <a 
                    href="/tools" 
                    target="_blank"
                    className="mt-4 text-sm text-[var(--accent-blue)] hover:underline flex items-center gap-1"
                  >
                    Go to Extension Settings <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {currentTierTools.map((tool) => {
                    const isSelected = isToolSelected(tool.id, tool.tier);
                    const config = TIER_CONFIG[tool.tier];
                    
                      return (
                      <ToolCard
                        key={tool.id}
                        id={tool.id}
                        name={tool.name}
                        displayName={tool.display_name}
                        description={tool.description}
                        category={tool.category}
                        icon={<TierIcon className="w-5 h-5" />}
                        color={`text-${config.color}-500 border-${config.color}-500`}
                        selected={isSelected}
                        recommended={isRecommendedTool(tool, activeTier)}
                        trending={isTrendingTool(tool.name)}
                        onClick={() => toggleTool(tool.id, tool.tier)}
                      />
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[var(--border-color)] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4 text-xs text-[var(--text-secondary)]">
            <span className="flex items-center gap-1">
              <Database className="w-3 h-3 text-blue-400" />
              {getSelectedCount('data')} Data
            </span>
            <span className="flex items-center gap-1">
              <Calculator className="w-3 h-3 text-purple-400" />
              {getSelectedCount('quant')} Quant
            </span>
            <span className="flex items-center gap-1">
              <Globe className="w-3 h-3 text-orange-400" />
              {getSelectedCount('external')} External
            </span>
            <span className="flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-emerald-400" />
              {getSelectedCount('strategy')} Strategies
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-6 py-2 bg-[var(--accent-blue)] text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors"
            >
              Save Selection
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  // 使用 Portal 渲染到 document.body，确保全屏显示不被裁剪
  return ReactDOM.createPortal(modalContent, document.body);
}
