"use client";

import React from "react";
import { 
  Bot, GitBranch, Database, Flag, Target, Wrench, 
  AlertCircle, Cpu, Book, Search, FileText, Calculator, FileCode, PlayCircle, Sparkles
} from "lucide-react";
import { NodeType, NodeData } from "./types";
import { formatRoutingTier, SCENARIO_TEMPLATES } from "./constants";
import { MCPToolDetail } from "@/lib/api";

// Helper to get tool icon
export const getToolIcon = (toolName: string) => {
  const name = toolName.toLowerCase();
  if (name.includes('search') || name.includes('google')) return Search;
  if (name.includes('finance') || name.includes('yahoo') || name.includes('stock')) return PlayCircle;
  if (name.includes('sec') || name.includes('edgar') || name.includes('filing')) return FileText;
  if (name.includes('calc') || name.includes('math')) return Calculator;
  if (name.includes('twitter') || name.includes('social') || name.includes('scrape')) return GitBranch;
  if (name.includes('code') || name.includes('execute')) return FileCode;
  return Wrench;
};

// Node Icon Component
export const NodeIcon = ({ type, className = "" }: { type: NodeType; className?: string }) => {
  const icons = {
    start: Flag,
    agent: Bot,
    router: GitBranch,
    knowledge: Database,
    end: Target,
  };
  const Icon = icons[type] || AlertCircle;
  return <Icon className={className} />;
};

// Handle Component
export const Handle = React.memo(({ type, position, onMouseDown, id }: { 
  type: 'source' | 'target'; 
  position: 'left' | 'right'; 
  onMouseDown: (e: React.MouseEvent, type: 'source' | 'target', id?: string) => void;
  id?: string;
}) => {
  const style: React.CSSProperties = position === 'left' 
    ? { left: -6, top: '50%', transform: 'translateY(-50%)' } 
    : { right: -6, top: '50%', transform: 'translateY(-50%)' };
  
  return (
    <div 
      className={`absolute w-3 h-3 bg-zinc-400 rounded-full border-2 border-zinc-900 cursor-crosshair hover:scale-125 transition-transform z-10 
        ${type === 'source' ? 'hover:bg-emerald-500' : 'hover:bg-blue-500'}`}
      style={style}
      onMouseDown={(e) => { 
        e.stopPropagation(); 
        onMouseDown(e, type, id); 
      }}
    />
  );
});
Handle.displayName = "Handle";

// Start Node
export const StartNode = React.memo(({ data, selected, onHandleMouseDown }: { 
  data: NodeData; 
  selected: boolean; 
  onHandleMouseDown: (e: React.MouseEvent, type: 'source' | 'target', id?: string) => void;
}) => {
  const isTemplate = data.inputMode === 'template' && data.templateId;
  const templateName = isTemplate ? SCENARIO_TEMPLATES[data.templateId!]?.name : null;

  return (
    <div className={`w-72 bg-[var(--bg-card)] border-2 rounded-xl shadow-lg transition-colors relative group select-none
      ${selected ? 'border-[var(--accent-green)] shadow-[0_0_15px_rgba(16,185,129,0.2)]' : 'border-[var(--border-color)] hover:border-green-500/50'}`}>
      <div className="p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-700 flex items-center justify-center shrink-0 shadow-lg">
            <NodeIcon type="start" className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-bold text-sm text-green-100">Start Trigger</div>
            <div className="text-[10px] text-green-300/70">Workflow Entry Point</div>
          </div>
        </div>

        <div className="p-3 bg-[var(--bg-panel)] rounded-lg border border-[var(--border-color)]">
          {isTemplate ? (
            <div className="mb-2">
              <div className="text-[10px] text-emerald-400 uppercase font-bold border border-green-900 bg-green-900/10 px-2 py-0.5 rounded mb-1 inline-block">
                Template
              </div>
              <div className="font-medium text-xs text-white line-clamp-1">{templateName}</div>
            </div>
          ) : (
            <div className="text-xs text-[var(--text-secondary)] uppercase font-semibold mb-1">Input Params</div>
          )}
          
          {data.variables && data.variables.length > 0 ? (
            <div className="space-y-1">
              {data.variables.slice(0, 3).map((v, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px] font-mono text-green-400">
                  <div className="w-1 h-1 rounded-full bg-green-500" />
                  {v.name}
                </div>
              ))}
              {data.variables.length > 3 && (
                <div className="text-[10px] text-zinc-500 italic pl-3">
                  + {data.variables.length - 3} more
                </div>
              )}
            </div>
          ) : (
            <div className="text-[10px] text-zinc-500 italic">No variables configured</div>
          )}
        </div>
      </div>
      <Handle type="source" position="right" onMouseDown={onHandleMouseDown} />
    </div>
  );
});
StartNode.displayName = "StartNode";

// Agent Node - Shows both Agent (WHO) and Task (WHAT)
export const AgentNode = React.memo(({ data, selected, connectedKnowledgeCount = 0, mcpTools = [], onHandleMouseDown }: { 
  data: NodeData; 
  selected: boolean; 
  connectedKnowledgeCount?: number; 
  mcpTools?: MCPToolDetail[];
  onHandleMouseDown: (e: React.MouseEvent, type: 'source' | 'target', id?: string) => void;
}) => {
  const skillCount =
    data.loadout_data?.skill_keys?.length ||
    data.selectedSkillKeys?.length ||
    0;

  return (
  <div className={`w-72 bg-[var(--bg-card)] border-2 rounded-xl shadow-lg transition-colors relative select-none
    ${selected ? 'border-[var(--accent-blue)] shadow-[0_0_15px_rgba(59,130,246,0.2)]' : 'border-[var(--border-color)] hover:border-blue-500/50'}`}>
    <Handle type="target" position="left" onMouseDown={onHandleMouseDown} />
    <div className="p-4">
      {/* Task Name Header (WHAT) */}
      {data.taskName && (
        <div className="mb-2 px-2 py-1 bg-emerald-900/20 border border-emerald-900/30 rounded-lg">
          <div className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            {data.taskName}
          </div>
        </div>
      )}
      
      {/* Agent Info (WHO) */}
      <div className="flex items-start gap-3 mb-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center shrink-0 shadow-inner">
          <NodeIcon type="agent" className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-bold text-sm text-blue-100 truncate">{data.role || "Unnamed Agent"}</div>
          <div className="text-[10px] text-blue-300/70 flex items-center gap-1 mt-0.5">
            <Cpu className="w-3 h-3" />
            {formatRoutingTier(data.model)}
          </div>
        </div>
      </div>
      
      {/* Task Description or Goal */}
      <div className="text-xs text-[var(--text-secondary)] bg-[var(--bg-panel)] p-2 rounded border border-[var(--border-color)] mb-3 line-clamp-2 min-h-[2.5rem]">
        {data.taskDescription || data.goal || "Configure task in sidebar..."}
      </div>
      
      {/* Tools & Knowledge Badges */}
      <div className="flex flex-wrap gap-2">
        {skillCount > 0 && (
          <div className="px-1.5 py-0.5 bg-orange-900/30 border border-orange-900/50 rounded flex items-center gap-1 text-[10px] text-orange-400">
            <Sparkles className="w-3 h-3" />
            {skillCount} Skills
          </div>
        )}
        {data.tools && data.tools.length > 0 && (
          <div className="flex -space-x-1">
            {data.tools.slice(0, 4).map((tId, i) => {
              const tool = mcpTools.find(m => m.tool_name === tId);
              const Icon = tool ? getToolIcon(tool.tool_name) : Wrench;
              return (
                <div key={i} className="w-5 h-5 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-[10px] text-zinc-400" title={tool?.tool_name || tId}>
                  <Icon className="w-3 h-3" />
                </div>
              );
            })}
            {data.tools.length > 4 && (
              <div className="w-5 h-5 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-[8px] text-zinc-500 font-bold">
                +{data.tools.length - 4}
              </div>
            )}
          </div>
        )}
        {connectedKnowledgeCount > 0 && (
          <div className="px-1.5 py-0.5 bg-yellow-900/30 border border-yellow-900/50 rounded flex items-center gap-1 text-[10px] text-yellow-500">
            <Book className="w-3 h-3" />
            {connectedKnowledgeCount} Docs
          </div>
        )}
        {/* Expected Output indicator */}
        {data.expectedOutput && (
          <div className="px-1.5 py-0.5 bg-purple-900/30 border border-purple-900/50 rounded flex items-center gap-1 text-[10px] text-purple-400">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Output
          </div>
        )}
      </div>
    </div>
    <Handle type="source" position="right" onMouseDown={onHandleMouseDown} />
  </div>
  );
});
AgentNode.displayName = "AgentNode";

// Router Node
export const RouterNode = React.memo(({ data, selected, onHandleMouseDown }: { 
  data: NodeData; 
  selected: boolean; 
  onHandleMouseDown: (e: React.MouseEvent, type: 'source' | 'target', id?: string) => void;
}) => {
  const routes = data.routes || [];
  
  return (
    <div className={`w-40 h-40 flex items-center justify-center relative m-8 select-none group ${selected ? 'z-10' : ''}`}>
      <Handle type="target" position="left" onMouseDown={onHandleMouseDown} />
      
      <div className={`absolute inset-0 bg-[var(--bg-card)] border-2 rotate-45 rounded-lg shadow-lg transition-all duration-300
        ${selected ? 'border-purple-500 shadow-[0_0_20px_rgba(168,85,247,0.3)]' : 'border-[var(--border-color)] group-hover:border-purple-500/50'}`}>
      </div>

      <div className="relative z-10 text-center pointer-events-none">
        <div className="w-8 h-8 mx-auto bg-purple-900/30 rounded-lg flex items-center justify-center text-purple-400 mb-1 border border-purple-500/30">
          <NodeIcon type="router" className="w-4 h-4" />
        </div>
        <div className="text-xs font-bold text-purple-200 px-2 line-clamp-2">{data.name || "Router"}</div>
        <div className="text-[8px] text-purple-300/70 mt-1 uppercase tracking-wider font-bold">Logic Gate</div>
      </div>

      {routes.map((route, index) => {
        const topPercent = ((index + 1) * 100) / (routes.length + 1);
        
        return (
          <div 
            key={route.id} 
            className="absolute right-[-8px] flex items-center group/handle"
            style={{ top: `${topPercent}%`, transform: 'translateY(-50%)' }}
          >
            <div className="absolute right-4 bg-[var(--bg-panel)] border border-[var(--border-color)] px-2 py-0.5 rounded text-[10px] text-[var(--text-secondary)] whitespace-nowrap z-20 pointer-events-none shadow-lg">
              {route.label}
            </div>
            <Handle 
              type="source" 
              id={route.id} 
              position="right" 
              onMouseDown={onHandleMouseDown}
            />
          </div>
        );
      })}
    </div>
  );
});
RouterNode.displayName = "RouterNode";

// Knowledge Node
export const KnowledgeNode = React.memo(({ data, selected, onHandleMouseDown }: { 
  data: NodeData; 
  selected: boolean; 
  onHandleMouseDown: (e: React.MouseEvent, type: 'source' | 'target', id?: string) => void;
}) => (
  <div className={`w-56 bg-[var(--bg-card)] border-2 rounded-xl shadow-lg transition-colors relative select-none
    ${selected ? 'border-yellow-500 shadow-[0_0_15px_rgba(234,179,8,0.2)]' : 'border-[var(--border-color)] hover:border-yellow-500/50'}`}>
    <div className="absolute -top-3 left-0 w-20 h-4 bg-[var(--bg-card)] border-t-2 border-l-2 border-r-2 border-[var(--border-color)] rounded-t-lg z-0" />
    
    <div className="p-4 relative z-10 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div className="w-10 h-10 bg-yellow-900/20 rounded-lg flex items-center justify-center text-yellow-500 border border-yellow-500/30 shrink-0">
          <NodeIcon type="knowledge" className="w-5 h-5" />
        </div>
        <div className="px-1.5 py-0.5 rounded text-[9px] uppercase font-bold bg-zinc-800 text-zinc-400 border border-zinc-700">
          {data.sourceType || 'File'}
        </div>
      </div>
      
      <div>
        <div className="font-bold text-sm text-yellow-100 line-clamp-1" title={data.name}>{data.name || "Knowledge Source"}</div>
        <div className="text-[10px] text-[var(--text-secondary)] line-clamp-1 mt-0.5">{data.content || "No content loaded"}</div>
      </div>
    </div>
    <Handle type="source" position="right" onMouseDown={onHandleMouseDown} />
  </div>
));
KnowledgeNode.displayName = "KnowledgeNode";

// End Node
export const EndNode = React.memo(({ data, selected, onHandleMouseDown }: { 
  data: NodeData; 
  selected: boolean; 
  onHandleMouseDown: (e: React.MouseEvent, type: 'source' | 'target', id?: string) => void;
}) => (
  <div className={`w-48 bg-[var(--bg-card)] border-2 rounded-xl shadow-lg transition-colors relative select-none
    ${selected ? 'border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.2)]' : 'border-[var(--border-color)] hover:border-red-500/50'}`}>
    <Handle type="target" position="left" onMouseDown={onHandleMouseDown} />
    <div className="p-3 flex items-center gap-3">
      <div className="w-8 h-8 bg-red-900/20 rounded-full flex items-center justify-center text-red-500 border border-red-500/30 shrink-0">
        <NodeIcon type="end" className="w-4 h-4" />
      </div>
      <div>
        <div className="font-bold text-sm text-red-100">Final Output</div>
        <div className="text-[10px] text-[var(--text-secondary)]">Report Generation</div>
      </div>
    </div>
  </div>
));
EndNode.displayName = "EndNode";
