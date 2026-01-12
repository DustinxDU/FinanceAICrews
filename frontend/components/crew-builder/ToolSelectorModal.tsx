"use client";

import React, { useState, useMemo } from "react";
import { X, Search, Wrench, Check, Sparkles, Filter, ChevronDown } from "lucide-react";
import { UnifiedTool } from "@/lib/types";
import { getToolIcon } from "./NodeComponents";

interface ToolSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  unifiedTools: UnifiedTool[];
  selectedTools: string[];
  onSave: (tools: string[]) => void;
  backstory?: string; // For auto-recommendation
}

/**
 * Calculate simple similarity score between backstory and tool description
 * Uses keyword matching for MVP (could be enhanced with embeddings later)
 */
const calculateRelevanceScore = (backstory: string, tool: UnifiedTool): number => {
  if (!backstory) return 0;
  
  const backstoryLower = backstory.toLowerCase();
  const toolText = `${tool.key} ${tool.name} ${tool.description || ''} ${tool.category || ''}`.toLowerCase();
  
  // Keywords that indicate relevance
  const keywords = toolText.split(/\s+/).filter(w => w.length > 3);
  let score = 0;
  
  for (const keyword of keywords) {
    if (backstoryLower.includes(keyword)) {
      score += 1;
    }
  }
  
  // Boost score for category matches
  const categoryKeywords: Record<string, string[]> = {
    'financial': ['financial', 'finance', 'stock', 'trading', 'investment', 'analyst', 'valuation', 'earnings'],
    'data': ['data', 'analysis', 'research', 'statistics', 'metrics'],
    'search': ['search', 'find', 'lookup', 'query', 'research'],
    'web': ['web', 'internet', 'online', 'browse', 'scrape'],
  };
  
  for (const [category, words] of Object.entries(categoryKeywords)) {
    if (tool.category?.toLowerCase().includes(category)) {
      for (const word of words) {
        if (backstoryLower.includes(word)) {
          score += 2;
        }
      }
    }
  }
  
  return score;
};

export const ToolSelectorModal: React.FC<ToolSelectorModalProps> = ({
  isOpen,
  onClose,
  unifiedTools,
  selectedTools,
  onSave,
  backstory
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [localSelected, setLocalSelected] = useState<string[]>(selectedTools);
  const [showRecommended, setShowRecommended] = useState(true);

  // Calculate categories from tools
  const categories = useMemo(() => {
    const cats: Record<string, number> = {};
    unifiedTools.forEach(tool => {
      const cat = tool.category || 'Other';
      cats[cat] = (cats[cat] || 0) + 1;
    });
    return cats;
  }, [unifiedTools]);

  // Calculate recommendations based on backstory
  const toolsWithScores = useMemo(() => {
    return unifiedTools.map(tool => ({
      tool,
      score: calculateRelevanceScore(backstory || '', tool)
    })).sort((a, b) => b.score - a.score);
  }, [unifiedTools, backstory]);

  // Filter tools
  const filteredTools = useMemo(() => {
    let tools = toolsWithScores;
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      tools = tools.filter(({ tool }) => 
        tool.key.toLowerCase().includes(query) ||
        tool.name.toLowerCase().includes(query) ||
        (tool.description || '').toLowerCase().includes(query)
      );
    }
    
    if (selectedCategory) {
      tools = tools.filter(({ tool }) => (tool.category || 'Other') === selectedCategory);
    }
    
    return tools;
  }, [toolsWithScores, searchQuery, selectedCategory]);

  // Recommended tools (score > 0)
  const recommendedTools = useMemo(() => {
    return toolsWithScores.filter(({ score }) => score > 0).slice(0, 5);
  }, [toolsWithScores]);

  const toggleTool = (toolKey: string) => {
    setLocalSelected(prev => 
      prev.includes(toolKey) 
        ? prev.filter(t => t !== toolKey)
        : [...prev, toolKey]
    );
  };

  const handleSave = () => {
    onSave(localSelected);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] w-full max-w-4xl max-h-[85vh] rounded-xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
              <Wrench className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-[var(--text-primary)]">Select Tools</h2>
              <p className="text-xs text-[var(--text-secondary)]">{localSelected.length} tools selected</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-[var(--bg-card)] rounded-lg transition-colors">
            <X className="w-5 h-5 text-[var(--text-secondary)] hover:text-white" />
          </button>
        </div>

        {/* Search and Filters */}
        <div className="p-4 border-b border-[var(--border-color)] space-y-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-secondary)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search tools..."
              className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg pl-10 pr-4 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-blue)]"
            />
          </div>
          
          {/* Category Pills */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedCategory(null)}
              className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                !selectedCategory 
                  ? 'bg-[var(--accent-blue)] border-[var(--accent-blue)] text-white' 
                  : 'bg-[var(--bg-card)] border-[var(--border-color)] text-[var(--text-secondary)] hover:border-[var(--text-secondary)]'
              }`}
            >
              All ({unifiedTools.length})
            </button>
            {Object.entries(categories).map(([cat, count]) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat === selectedCategory ? null : cat)}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                  selectedCategory === cat 
                    ? 'bg-[var(--accent-blue)] border-[var(--accent-blue)] text-white' 
                    : 'bg-[var(--bg-card)] border-[var(--border-color)] text-[var(--text-secondary)] hover:border-[var(--text-secondary)]'
                }`}
              >
                {cat} ({count})
              </button>
            ))}
            <div className="flex-1"></div>
            <button
              onClick={() => setShowRecommended(!showRecommended)}
              className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                showRecommended 
                  ? 'bg-yellow-900/30 border-yellow-500 text-yellow-400' 
                  : 'bg-[var(--bg-card)] border-[var(--border-color)] text-[var(--text-secondary)]'
              }`}
            >
              {showRecommended ? 'Hide' : 'Show'} AI Recs
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Recommended Section */}
          {showRecommended && recommendedTools.length > 0 && !searchQuery && !selectedCategory && (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-yellow-500" />
                <span className="text-sm font-bold text-yellow-400">Recommended Tools</span>
                <span className="text-xs text-[var(--text-secondary)]">Automatically matched based on Agent background</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {recommendedTools.map(({ tool, score }) => {
                  const isSelected = localSelected.includes(tool.key);
                  const Icon = getToolIcon(tool.name);
                  return (
                    <div
                      key={`rec-${tool.key}`}
                      onClick={() => toggleTool(tool.key)}
                      className={`flex items-start p-3 rounded-lg border cursor-pointer transition-all ${
                        isSelected 
                          ? 'bg-yellow-900/20 border-yellow-500/50' 
                          : 'bg-[var(--bg-card)]/50 border-[var(--border-color)] hover:border-yellow-500/30'
                      }`}
                    >
                      <div className={`w-5 h-5 rounded border flex items-center justify-center mr-3 mt-0.5 shrink-0 ${
                        isSelected ? 'bg-yellow-500 border-yellow-500' : 'border-zinc-500'
                      }`}>
                        {isSelected && <Check className="w-3 h-3 text-black" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Icon className="w-4 h-4 text-yellow-400" />
                          <span className="text-sm font-medium text-[var(--text-primary)] truncate">{tool.name}</span>
                          <span className="text-[10px] px-1.5 py-0.5 bg-yellow-900/50 text-yellow-400 rounded">Relevance {score}</span>
                        </div>
                        <p className="text-xs text-[var(--text-secondary)] mt-1 line-clamp-1">{tool.description}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* All Tools */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Filter className="w-4 h-4 text-[var(--text-secondary)]" />
              <span className="text-sm font-bold text-[var(--text-primary)]">
                {selectedCategory || 'All Tools'} ({filteredTools.length})
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {filteredTools.map(({ tool }) => {
                const isSelected = localSelected.includes(tool.key);
                const Icon = getToolIcon(tool.name);
                return (
                  <div
                    key={tool.key}
                    onClick={() => toggleTool(tool.key)}
                    className={`flex items-start p-3 rounded-lg border cursor-pointer transition-all ${
                      isSelected 
                        ? 'bg-blue-900/20 border-[var(--accent-blue)]' 
                        : 'bg-[var(--bg-card)]/50 border-[var(--border-color)] hover:border-[var(--text-secondary)]'
                    }`}
                  >
                    <div className={`w-5 h-5 rounded border flex items-center justify-center mr-3 mt-0.5 shrink-0 ${
                      isSelected ? 'bg-blue-500 border-blue-500' : 'border-zinc-500'
                    }`}>
                      {isSelected && <Check className="w-3 h-3 text-white" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Icon className="w-4 h-4 text-[var(--text-secondary)]" />
                        <span className="text-sm font-medium text-[var(--text-primary)] truncate">{tool.name}</span>
                        {tool.category && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-[var(--bg-card)] text-[var(--text-secondary)] rounded">{tool.category}</span>
                        )}
                      </div>
                      <p className="text-xs text-[var(--text-secondary)] mt-1 line-clamp-2">{tool.description}</p>
                    </div>
                  </div>
                );
              })}
            </div>
            
            {filteredTools.length === 0 && (
              <div className="text-center py-8 text-[var(--text-secondary)]">
                <Wrench className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No matching tools found</p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[var(--border-color)] bg-[var(--bg-card)]/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="crewai-filter"
              className="rounded border-[var(--border-color)]"
              defaultChecked
            />
            <label htmlFor="crewai-filter" className="text-xs text-[var(--text-secondary)]">
              Enable CrewAI Smart Tool Selection <span className="text-[var(--text-muted)]">(Even if multiple tools are selected, the AI will automatically choose the most relevant ones)</span>
            </label>
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 text-sm bg-[var(--accent-blue)] hover:bg-blue-500 text-white rounded-lg transition-colors"
            >
              Save Selection ({localSelected.length})
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ToolSelectorModal;
