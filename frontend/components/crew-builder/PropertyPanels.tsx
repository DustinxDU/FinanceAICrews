"use client";

import React, { useEffect, useState } from "react";
import { Link } from "@/i18n/routing";
import { Trash2, Sparkles, Loader2, CheckCircle, User, ClipboardList, Wrench as WrenchIcon, Database, Settings, Plus, X, ExternalLink, Zap, Target, Workflow, ChevronDown, ChevronUp, GripVertical } from "lucide-react";
import { NodeData, NodeVariable, EXPECTED_OUTPUT_TEMPLATES } from "./types";
import { SCENARIO_TEMPLATES, ROUTER_TEMPLATES, LLM_ROUTING_TIERS, DEFAULT_LLM_TIER } from "./constants";
import { MCPToolDetail, AgentLoadout } from "@/lib/api";
import { getToolIcon } from "./NodeComponents";
import { getToken } from "@/lib/auth";
import { buildApiUrl } from "@/lib/apiClient";
import { SmartVariableInput } from "./SmartVariableInput";
import { SkillSelector } from "./SkillSelector/SkillSelector";
import type { Skill } from "@/types/skills";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// Form Field Renderer
export const renderSchemaField = (field: any, value: any, onChange: (e: any) => void, readOnly = false) => {
  const commonClasses = "w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-emerald-500 transition-colors text-white";
  
  switch (field.type) {
    case 'select':
      return (
        <select value={value || field.default || ''} onChange={onChange} disabled={readOnly} className={commonClasses}>
          {field.options.map((opt: string) => <option key={opt} value={opt}>{opt}</option>)}
        </select>
      );
    case 'radio':
      return (
        <div className="flex flex-wrap gap-2">
          {field.options.map((opt: string) => (
            <label key={opt} className={`cursor-pointer px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${value === opt || (!value && field.default === opt) ? 'bg-green-900/30 border-green-500 text-green-400' : 'bg-zinc-950 border-zinc-700 text-zinc-400'}`}>
              <input type="radio" name={field.key} value={opt} checked={value === opt || (!value && field.default === opt)} onChange={onChange} disabled={readOnly} className="hidden" />
              {opt}
            </label>
          ))}
        </div>
      );
    case 'checkbox_group':
      const currentVals = Array.isArray(value) ? value : (field.default || []);
      return (
        <div className="space-y-1.5">
          {field.options.map((opt: string) => (
            <label key={opt} className="flex items-center gap-2 text-sm text-zinc-400 cursor-pointer">
              <input 
                type="checkbox" 
                checked={currentVals.includes(opt)} 
                onChange={(e) => {
                  if(readOnly) return;
                  const newVals = e.target.checked 
                    ? [...currentVals, opt]
                    : currentVals.filter((v: string) => v !== opt);
                  onChange({ target: { value: newVals } });
                }}
                disabled={readOnly}
                className="rounded border-zinc-700 bg-zinc-800 text-green-500 focus:ring-0" 
              />
              {opt}
            </label>
          ))}
        </div>
      );
    case 'textarea':
      return <textarea value={value || ''} onChange={onChange} disabled={readOnly} placeholder={field.placeholder} className={`${commonClasses} resize-none h-20`} />;
    case 'slider':
      return (
        <div className="flex items-center gap-3">
          <span className="text-xs text-zinc-400">{field.labels[0]}</span>
          <input 
            type="range" 
            min={field.min} 
            max={field.max} 
            value={value || field.default} 
            onChange={onChange}
            disabled={readOnly}
            className="flex-1 h-2 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-emerald-500" 
          />
          <span className="text-xs text-zinc-400">{field.labels[1]}</span>
        </div>
      );
    default:
      return <input type="text" value={value || ''} onChange={onChange} disabled={readOnly} placeholder={field.placeholder} className={commonClasses} />;
  }
};

// Sortable Variable Card Component
interface SortableVariableCardProps {
  variable: NodeVariable;
  index: number;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onUpdate: (updates: Partial<NodeVariable>) => void;
  onRemove: () => void;
}

function SortableVariableCard({ variable, index, isExpanded, onToggleExpand, onUpdate, onRemove }: SortableVariableCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: variable.name || `var-${index}` });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`bg-zinc-900 rounded-lg border ${isDragging ? 'border-emerald-500' : 'border-zinc-700'} overflow-hidden`}
    >
      {/* Header - always visible */}
      <div className="flex items-center gap-2 p-2 bg-zinc-800/50">
        <button
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing text-zinc-500 hover:text-zinc-300 touch-none"
        >
          <GripVertical className="w-4 h-4" />
        </button>
        <span className="text-sm font-mono text-emerald-400 flex-1">{variable.name}</span>
        <span className="text-xs text-zinc-500 px-2 py-0.5 bg-zinc-800 rounded">{variable.type}</span>
        <button
          onClick={onToggleExpand}
          className="text-zinc-500 hover:text-zinc-300 p-1"
        >
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        <button onClick={onRemove} className="text-zinc-500 hover:text-red-400 p-1">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="p-3 space-y-3 border-t border-zinc-700/50">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[10px] text-zinc-500 uppercase mb-1">Label</label>
              <input
                type="text"
                value={variable.label || variable.name}
                onChange={(e) => onUpdate({ label: e.target.value })}
                placeholder="Display name"
                className="w-full bg-zinc-950 border border-zinc-700 rounded px-2 py-1.5 text-xs text-white focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-[10px] text-zinc-500 uppercase mb-1">Type</label>
              <select
                value={variable.type || 'text'}
                onChange={(e) => onUpdate({ type: e.target.value })}
                className="w-full bg-zinc-950 border border-zinc-700 rounded px-2 py-1.5 text-xs text-white focus:border-emerald-500 outline-none"
              >
                <option value="text">Text</option>
                <option value="select">Select</option>
                <option value="number">Number</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-[10px] text-zinc-500 uppercase mb-1">Description (Help Text)</label>
            <textarea
              value={variable.description || ''}
              onChange={(e) => onUpdate({ description: e.target.value })}
              placeholder="Explain what this variable is for..."
              rows={2}
              className="w-full bg-zinc-950 border border-zinc-700 rounded px-2 py-1.5 text-xs text-white focus:border-emerald-500 outline-none resize-none"
            />
          </div>
          {variable.type === 'select' && (
            <div>
              <label className="block text-[10px] text-zinc-500 uppercase mb-1">Options (comma-separated)</label>
              <input
                type="text"
                value={(variable.options || []).join(', ')}
                onChange={(e) => onUpdate({ options: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                placeholder="option1, option2, option3"
                className="w-full bg-zinc-950 border border-zinc-700 rounded px-2 py-1.5 text-xs text-white focus:border-emerald-500 outline-none"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Start Node Panel
export const StartNodePanel = ({ data, updateData }: { data: NodeData; updateData: (d: Partial<NodeData>) => void }) => {
  const inputMode = data.inputMode || 'custom';
  const handleModeChange = (mode: 'custom' | 'template') => updateData({ inputMode: mode });
  const handleTemplateChange = (templateId: string) => {
    const template = SCENARIO_TEMPLATES[templateId];
    const newVariables = template.schema.map((field: any) => ({
      name: field.key,
      label: field.label || field.key,
      type: (field.type === 'number' ? 'number' : field.type === 'select' ? 'select' : 'text'),
      options: field.options,
      description: field.description || ''
    }));
    updateData({ templateId, variables: newVariables, inputSchema: template.schema });
  };

  const [newVar, setNewVar] = useState({ name: '', label: '', type: 'text', description: '' });
  const [expandedVars, setExpandedVars] = useState<Set<number>>(new Set());

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const addVar = () => {
    if(newVar.name) {
      const newVariable: NodeVariable = {
        name: newVar.name,
        label: newVar.label || newVar.name,
        type: newVar.type as any,
        description: newVar.description
      };
      updateData({ variables: [...(data.variables || []), newVariable] });
      setNewVar({ name: '', label: '', type: 'text', description: '' });
      // Auto-expand newly added variable
      setExpandedVars(prev => new Set([...prev, (data.variables || []).length]));
    }
  };

  const removeVar = (idx: number) => {
    const v = [...(data.variables || [])];
    v.splice(idx, 1);
    updateData({ variables: v });
    setExpandedVars(prev => {
      const next = new Set(prev);
      next.delete(idx);
      return next;
    });
  };

  const updateVar = (idx: number, updates: Partial<NodeVariable>) => {
    const vars = [...(data.variables || [])];
    vars[idx] = { ...vars[idx], ...updates };
    updateData({ variables: vars });
  };

  const toggleExpand = (idx: number) => {
    setExpandedVars(prev => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const variables = data.variables || [];
      const oldIndex = variables.findIndex(v => (v.name || `var-${variables.indexOf(v)}`) === active.id);
      const newIndex = variables.findIndex(v => (v.name || `var-${variables.indexOf(v)}`) === over.id);
      if (oldIndex !== -1 && newIndex !== -1) {
        updateData({ variables: arrayMove(variables, oldIndex, newIndex) });
      }
    }
  };

  const variables = data.variables || [];

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-bold uppercase text-zinc-400 mb-4">Input Configuration</h3>
        <div className="flex bg-zinc-900 p-1 rounded-lg border border-zinc-700 mb-4">
          <button onClick={() => handleModeChange('custom')} className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${inputMode === 'custom' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-400 hover:text-white'}`}>Free Text (Custom)</button>
          <button onClick={() => handleModeChange('template')} className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${inputMode === 'template' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-400 hover:text-white'}`}>Structured Template</button>
        </div>
        {inputMode === 'custom' ? (
          <div>
            {/* Variable List with Drag & Drop */}
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={variables.map((v, i) => v.name || `var-${i}`)}
                strategy={verticalListSortingStrategy}
              >
                <div className="space-y-2 mb-4">
                  {variables.map((v, i) => (
                    <SortableVariableCard
                      key={v.name || `var-${i}`}
                      variable={v}
                      index={i}
                      isExpanded={expandedVars.has(i)}
                      onToggleExpand={() => toggleExpand(i)}
                      onUpdate={(updates) => updateVar(i, updates)}
                      onRemove={() => removeVar(i)}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>

            {/* Add New Variable Form */}
            <div className="space-y-2 bg-zinc-900 border border-zinc-700 border-dashed rounded-lg p-3">
              <div className="text-[10px] text-zinc-500 uppercase font-bold mb-2">Add New Variable</div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  value={newVar.name}
                  onChange={(e) => setNewVar(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Key (e.g. ticker)"
                  className="bg-zinc-950 border border-zinc-700 rounded px-3 py-2 text-sm outline-none text-white focus:border-emerald-500"
                />
                <input
                  type="text"
                  value={newVar.label}
                  onChange={(e) => setNewVar(prev => ({ ...prev, label: e.target.value }))}
                  placeholder="Label (Display Name)"
                  className="bg-zinc-950 border border-zinc-700 rounded px-3 py-2 text-sm outline-none text-white focus:border-emerald-500"
                />
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={newVar.type}
                  onChange={(e) => setNewVar(prev => ({ ...prev, type: e.target.value }))}
                  className="flex-1 bg-zinc-950 border border-zinc-700 rounded px-3 py-2 text-sm outline-none text-white focus:border-emerald-500"
                >
                  <option value="text">Text</option>
                  <option value="select">Select</option>
                  <option value="number">Number</option>
                </select>
                <button
                  onClick={addVar}
                  disabled={!newVar.name}
                  className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white px-4 py-2 rounded font-medium transition-colors"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div>
            <div className="mb-4">
              <select 
                value={data.templateId || ''} 
                onChange={(e) => handleTemplateChange(e.target.value)} 
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none text-white"
              >
                <option value="" disabled>-- Choose a Scenario --</option>
                {Object.entries(SCENARIO_TEMPLATES).map(([key, t]) => (
                  <option key={key} value={key}>{t.name}</option>
                ))}
              </select>
            </div>
            {data.templateId && SCENARIO_TEMPLATES[data.templateId] && (
              <div className="space-y-4 animate-in fade-in slide-in-from-top-2">
                <div className="p-3 bg-blue-900/20 border border-blue-900/50 rounded-lg text-xs text-blue-200">
                  <div className="font-bold mb-1">{SCENARIO_TEMPLATES[data.templateId].name}</div>
                  {SCENARIO_TEMPLATES[data.templateId].description}
                </div>
                <div className="bg-zinc-900 border border-zinc-700 rounded-xl p-4 space-y-4 opacity-80 pointer-events-none grayscale-[0.3]">
                  {SCENARIO_TEMPLATES[data.templateId].schema.map((field: any) => (
                    <div key={field.key}>
                      <label className="block text-xs font-medium text-zinc-400 mb-1">{field.label}</label>
                      {renderSchemaField(field, null, () => {}, true)}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Router Node Panel - with variable support
export const RouterNodePanel = ({ 
  data, 
  updateData,
  availableVars = []
}: { 
  data: NodeData; 
  updateData: (d: Partial<NodeData>) => void;
  availableVars?: string[];
}) => {
  const handleAddRoute = () => { 
    const newRoutes = [...(data.routes || [])]; 
    newRoutes.push({ id: `route-${Date.now()}`, label: "New Path", criteria: "", color: "text-zinc-400 border-zinc-500/50 bg-zinc-900/20" }); 
    updateData({ routes: newRoutes }); 
  };
  const handleRemoveRoute = (id: string) => { updateData({ routes: data.routes?.filter(r => r.id !== id) }); };
  const handleRouteChange = (id: string, field: string, value: string) => { 
    updateData({ routes: data.routes?.map(r => r.id === id ? { ...r, [field]: value } : r) }); 
  };
  const applyQuickFill = (templateKey: string) => { 
    const template = ROUTER_TEMPLATES[templateKey]; 
    if (template) { 
      updateData({ name: template.label.replace(/[\u{1F300}-\u{1F9FF}]/gu, '').trim(), instruction: template.instruction, routes: template.routes }); 
    } 
  };

  return (
    <div className="space-y-6">
      <div>
        <label className="text-xs font-bold uppercase text-zinc-400 block mb-2">Identity</label>
        <input 
          type="text" 
          value={data.name || ''} 
          onChange={(e) => updateData({ name: e.target.value })} 
          placeholder="Router Name" 
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none mb-3 text-white" 
        />
      </div>
      <div>
        {/* Routing Instruction - with variable insertion */}
        <SmartVariableInput
          label="Routing Instruction"
          helpText="Routing decision logic - Type {{ to see available variables"
          value={data.instruction || ''}
          onChange={(val) => updateData({ instruction: val })}
          availableVars={availableVars.map(v => ({ name: v, type: 'text' as const }))}
          placeholder="Analyze market sentiment for {{ticker}}: is it bullish or bearish?"
          rows={4}
        />
        <div className="flex flex-wrap gap-2 mb-4">
          {Object.entries(ROUTER_TEMPLATES).map(([key, t]) => (
            <button 
              key={key} 
              onClick={() => applyQuickFill(key)} 
              className="text-[10px] px-2 py-1 rounded bg-zinc-800 border border-zinc-700 hover:border-blue-500 hover:text-white transition-colors flex items-center gap-1 text-zinc-400"
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="space-y-3">
          <div className="flex justify-between items-center text-xs text-zinc-400 uppercase font-bold">
            <span>Branches</span>
            <button onClick={handleAddRoute} className="text-blue-400 hover:text-blue-300">+ Add</button>
          </div>
          {(data.routes || []).map((route) => (
            <div key={route.id} className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 relative group">
              <button 
                onClick={() => handleRemoveRoute(route.id)} 
                className="absolute top-2 right-2 text-zinc-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <div className="flex items-center gap-2 mb-2">
                <div className={`w-2 h-2 rounded-full ${route.color ? route.color.split(' ')[0].replace('text-', 'bg-') : 'bg-zinc-500'}`} />
                <input 
                  type="text" 
                  value={route.label} 
                  onChange={(e) => handleRouteChange(route.id, 'label', e.target.value)} 
                  className="bg-transparent border-b border-transparent hover:border-zinc-700 focus:border-blue-500 outline-none text-sm font-bold w-32 text-white" 
                />
              </div>
              <textarea 
                value={route.criteria} 
                onChange={(e) => handleRouteChange(route.id, 'criteria', e.target.value)} 
                placeholder="Criteria..." 
                className="w-full bg-zinc-800 rounded p-2 text-xs outline-none text-zinc-400 resize-none h-16"
              />
            </div>
          ))}
        </div>
      </div>
      <div>
        <label className="text-xs font-bold uppercase text-zinc-400 block mb-2">Default Route (Fallback)</label>
        <select 
          value={data.defaultRouteId || ''} 
          onChange={(e) => updateData({ defaultRouteId: e.target.value })} 
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none text-white"
        >
          <option value="" disabled>-- Select Fallback --</option>
          {(data.routes || []).map(r => (<option key={r.id} value={r.id}>{r.label}</option>))}
        </select>
      </div>
    </div>
  );
};

// Agent Node Panel - Redesigned with WHO (Agent) + WHAT (Task) tabs
export const AgentNodePanel = ({
  data,
  updateData,
  availableVars,
  connectedKnowledge,
  mcpTools,
  onOpenSkillPanel
}: {
  data: NodeData;
  updateData: (d: Partial<NodeData>) => void;
  availableVars: string[];
  connectedKnowledge: any[];
  mcpTools: MCPToolDetail[];
  onOpenSkillPanel?: () => void;
}) => {
  const [activeTab, setActiveTab] = useState<'agent' | 'task'>('agent');
  const [isAutoRefining, setIsAutoRefining] = useState(false);

  // Skills state - sync from loadout_data
  const [selectedSkillKeys, setSelectedSkillKeys] = useState<string[]>([]);
  const [allSkills, setAllSkills] = useState<Skill[]>([]);

  // Sync selectedSkillKeys with data.loadout_data.skill_keys
  useEffect(() => {
    const skillKeys = data.loadout_data?.skill_keys || data.selectedSkillKeys || [];
    setSelectedSkillKeys(skillKeys);
  }, [data.loadout_data, data.selectedSkillKeys]);

  // Load skill catalog for displaying selected skills
  useEffect(() => {
    const loadSkills = async () => {
      try {
        const { default: apiClient } = await import("@/lib/api");
        const catalog = await apiClient.getSkillCatalog();
        setAllSkills([...catalog.capabilities, ...catalog.presets, ...catalog.strategies, ...catalog.skillsets]);
      } catch (err) {
        if (process.env.NODE_ENV !== 'test') {
          console.warn("Failed to load skill catalog, falling back to raw skill keys:", err);
        }
        setAllSkills([]);
      }
    };
    loadSkills();
  }, []);

  // Remove skill helper
  const removeSkillKey = (skillKey: string) => {
    const newKeys = selectedSkillKeys.filter(k => k !== skillKey);
    setSelectedSkillKeys(newKeys);
    updateData({ loadout_data: { skill_keys: newKeys } });
  };

  // Skill Kind icon helper
  const SkillKindIcon = ({ kind, className }: { kind: string; className?: string }) => {
    const icons = {
      capability: <Database className={className} />,
      preset: <Zap className={className} />,
      strategy: <Target className={className} />,
      skillset: <Workflow className={className} />,
    };
    return icons[kind as keyof typeof icons] || <Database className={className} />;
  };

  const handleAutoRefine = () => {
    if(!data.backstory) return;
    setIsAutoRefining(true);
    setTimeout(() => {
      updateData({ backstory: `[AI Enhanced] ${data.backstory}\n\nSpecifically specialized in high-frequency market data analysis with a focus on volatility indices. Draws upon 15 years of institutional trading experience to identify arbitrage opportunities.` });
      setIsAutoRefining(false);
    }, 1500);
  };

  const applyOutputTemplate = (templateKey: string) => {
    const template = EXPECTED_OUTPUT_TEMPLATES[templateKey as keyof typeof EXPECTED_OUTPUT_TEMPLATES];
    if (template) {
      updateData({ expectedOutput: template.value });
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Tab Headers */}
      <div className="flex border-b border-zinc-700 mb-4">
        <button 
          onClick={() => setActiveTab('agent')} 
          className={`flex-1 pb-3 text-xs font-bold uppercase tracking-wider transition-colors relative flex items-center justify-center gap-2 ${activeTab === 'agent' ? 'text-blue-400' : 'text-zinc-500 hover:text-white'}`}
        >
          <User className="w-4 h-4" />
          <span>🕵️ Agent (WHO)</span>
          {activeTab === 'agent' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />}
        </button>
        <button 
          onClick={() => setActiveTab('task')} 
          className={`flex-1 pb-3 text-xs font-bold uppercase tracking-wider transition-colors relative flex items-center justify-center gap-2 ${activeTab === 'task' ? 'text-emerald-400' : 'text-zinc-500 hover:text-white'}`}
        >
          <ClipboardList className="w-4 h-4" />
          <span>📝 Task (WHAT)</span>
          {activeTab === 'task' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-500" />}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto pr-2 space-y-5">
        {/* ============================================ */}
        {/* TAB 1: Agent Identity (WHO) */}
        {/* ============================================ */}
        {activeTab === 'agent' && (
          <div className="space-y-5 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="p-3 bg-blue-900/10 border border-blue-900/30 rounded-lg">
              <p className="text-xs text-blue-300">Define the executor identity: "Who does this step"</p>
            </div>

            {/* Role Name */}
            <div>
              <label className="text-xs font-bold uppercase text-zinc-400 block mb-2">
                Role <span className="text-red-400">*</span>
                <span className="text-zinc-500 font-normal ml-2">Role Name</span>
              </label>
              <input
                type="text"
                value={data.role || ''}
                onChange={(e) => updateData({ role: e.target.value })}
                placeholder="e.g., Senior Financial Analyst"
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none text-white"
              />
            </div>

            {/* Goal - Required by CrewAI */}
            <SmartVariableInput
              label="Goal"
              helpText="High-level mission that guides the agent's thinking (specific tasks go in the Task tab)"
              value={data.goal || ''}
              onChange={(val) => updateData({ goal: val })}
              availableVars={availableVars.map(v => ({ name: v, type: 'text' as const }))}
              placeholder="e.g., Provide accurate and comprehensive financial analysis to help investors make informed decisions"
              rows={3}
              required
            />

            {/* Routing Tier Selection */}
            <div>
              <label className="text-xs font-bold uppercase text-zinc-400 block mb-2">Routing Tier</label>
              <select
                aria-label="Agent Routing Tier"
                value={data.model || DEFAULT_LLM_TIER}
                onChange={(e) => updateData({ model: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none text-white"
              >
                {LLM_ROUTING_TIERS.map((tier) => (
                  <option key={tier.value} value={tier.value}>
                    {tier.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Backstory */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-bold uppercase text-zinc-400">
                  Backstory <span className="text-zinc-500 font-normal ml-2">Personality / Background Story</span>
                </label>
                <button 
                  onClick={handleAutoRefine} 
                  disabled={!data.backstory || isAutoRefining} 
                  className={`text-[10px] flex items-center gap-1 px-2 py-0.5 rounded border transition-all ${isAutoRefining ? 'bg-purple-900/50 border-purple-500 text-purple-300' : 'bg-purple-900/20 border-purple-900/50 text-purple-400 hover:bg-purple-900/40'}`}
                >
                  {isAutoRefining ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />} AI Enhance
                </button>
              </div>
              <textarea 
                value={data.backstory || ''} 
                onChange={(e) => updateData({ backstory: e.target.value })} 
                placeholder="You are a senior financial analyst with 10 years of experience, specializing in..."
                className="w-full h-28 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none resize-none text-white"
              />
            </div>

            {/* Skills Section - with Skill Selector */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="text-xs font-bold uppercase text-zinc-400">
                  <Sparkles className="w-3 h-3 inline mr-1" />
                  Skills <span className="text-zinc-500 font-normal ml-2">Agent Capability Equipment</span>
                </label>
                <button
                  onClick={() => onOpenSkillPanel?.()}
                  className="flex items-center gap-1 px-2 py-1 text-[10px] bg-blue-600 hover:bg-blue-500 text-white rounded transition-colors"
                >
                  <Plus className="w-3 h-3" />
                  Select Skills
                </button>
              </div>

              {/* Selected Skills Display */}
              {selectedSkillKeys && selectedSkillKeys.length > 0 ? (
                <div className="space-y-2">
                  {selectedSkillKeys.map(skillKey => {
                    const skill = allSkills.find(s => s.skill_key === skillKey);
                    const inferredKind = (() => {
                      const prefix = (skillKey.split(':')[0] || '').trim();
                      if (prefix === 'capability' || prefix === 'preset' || prefix === 'strategy' || prefix === 'skillset') {
                        return prefix;
                      }
                      return 'capability';
                    })();

                    const kind = skill?.kind || inferredKind;
                    const title = skill?.title || skillKey;

                    return (
                      <div
                        key={skillKey}
                        className="flex items-center justify-between p-2 bg-blue-900/20 border border-blue-500/50 rounded-lg group"
                      >
                        <div className="flex items-center gap-2">
                          <SkillKindIcon kind={kind} className="w-4 h-4" />
                          <span className="text-sm text-white">{title}</span>
                        </div>
                        <button
                          onClick={() => removeSkillKey(skillKey)}
                          className="p-1 text-zinc-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div
                  onClick={() => onOpenSkillPanel?.()}
                  className="p-4 border border-dashed border-zinc-700 rounded-lg text-center cursor-pointer hover:border-blue-500/50 hover:bg-blue-900/10 transition-all"
                >
                  <Sparkles className="w-6 h-6 text-zinc-600 mx-auto mb-2" />
                  <p className="text-xs text-zinc-500">Click to equip skills</p>
                  <p className="text-[10px] text-zinc-600 mt-1">
                    AI recommendations based on Agent role
                  </p>
                </div>
              )}
            </div>

            {/* Connected Knowledge */}
            <div>
              <label className="text-xs font-bold uppercase text-zinc-400 block mb-3">
                <Database className="w-3 h-3 inline mr-1" />
                Knowledge <span className="text-zinc-500 font-normal ml-2">Knowledge Sources</span>
              </label>
              {connectedKnowledge && connectedKnowledge.length > 0 ? (
                <div className="space-y-2">
                  {connectedKnowledge.map((node, i) => (
                    <div key={i} className="flex items-center p-2 bg-yellow-900/10 border border-yellow-900/30 rounded-lg">
                      <Database className="w-4 h-4 text-yellow-500 mr-2" />
                      <span className="text-sm text-yellow-100">{node.data.name || "Unnamed"}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-3 border border-dashed border-zinc-700 rounded-lg text-center text-xs text-zinc-500">
                  Drag and drop knowledge nodes to connect to this Agent
                </div>
              )}
            </div>

            {/* Advanced Settings Collapsed */}
            <details className="group">
              <summary className="flex items-center gap-2 text-xs font-bold uppercase text-zinc-400 cursor-pointer hover:text-white">
                <Settings className="w-3 h-3" />
                Advanced Settings
              </summary>
              <div className="mt-3 space-y-4 pl-5 border-l border-zinc-700">
                <div>
                  <label className="text-xs text-zinc-400">Max Iterations ({data.maxIter || 15})</label>
                  <input 
                    type="range" min="1" max="50" 
                    value={data.maxIter || 15} 
                    onChange={(e) => updateData({ maxIter: parseInt(e.target.value) })} 
                    className="w-full h-2 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-emerald-500" 
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-400">Allow Delegation</span>
                  <button 
                    onClick={() => updateData({ allowDelegation: !data.allowDelegation })} 
                    className={`w-10 h-5 rounded-full p-1 transition-colors ${data.allowDelegation ? 'bg-emerald-500' : 'bg-zinc-700'}`}
                  >
                    <div className={`w-3 h-3 bg-white rounded-full transition-transform ${data.allowDelegation ? 'translate-x-5' : 'translate-x-0'}`} />
                  </button>
                </div>
              </div>
            </details>
          </div>
        )}

        {/* ============================================ */}
        {/* TAB 2: Task Definition (WHAT) */}
        {/* ============================================ */}
        {activeTab === 'task' && (
          <div className="space-y-5 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="p-3 bg-emerald-900/10 border border-emerald-900/30 rounded-lg">
              <p className="text-xs text-emerald-300">Define specific task: What to do in this step</p>
            </div>

            {/* Task Name */}
            <div>
              <label className="text-xs font-bold uppercase text-zinc-400 block mb-2">
                Task Name <span className="text-red-400">*</span>
                <span className="text-zinc-500 font-normal ml-2">Task Name</span>
              </label>
              <input 
                type="text" 
                value={data.taskName || ''} 
                onChange={(e) => updateData({ taskName: e.target.value })} 
                placeholder="e.g., Fundamental Analysis"
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none text-white" 
              />
            </div>

            {/* Task Description - with variable insertion */}
            <SmartVariableInput
              label="Description"
              helpText="Task instructions - Type {{ to see available variables"
              value={data.taskDescription || ''}
              onChange={(val) => updateData({ taskDescription: val })}
              availableVars={availableVars.map(v => ({ name: v, type: 'text' as const }))}
              placeholder="Analyze balance sheet, income statement, and cash flow statement of {{ticker}}, identifying key financial metrics..."
              rows={5}
            />

            {/* Expected Output - with variable insertion + templates */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-bold uppercase text-zinc-400">
                  Expected Output <span className="text-zinc-500 font-normal ml-2">Expected Deliverables</span>
                </label>
              </div>
              <div className="flex flex-wrap gap-2 mb-2">
                {Object.entries(EXPECTED_OUTPUT_TEMPLATES).map(([key, template]) => (
                  <button 
                    key={key}
                    onClick={() => applyOutputTemplate(key)}
                    className="text-[10px] px-2 py-1 bg-zinc-800 border border-zinc-700 rounded hover:border-emerald-500 hover:bg-emerald-900/20 text-zinc-400 hover:text-emerald-400 transition-colors"
                  >
                    {template.label}
                  </button>
                ))}
              </div>
              <SmartVariableInput
                value={data.expectedOutput || ''}
                onChange={(val) => updateData({ expectedOutput: val })}
                availableVars={availableVars.map(v => ({ name: v, type: 'text' as const }))}
                placeholder="A detailed financial health diagnosis report in Markdown format..."
                rows={4}
              />
            </div>

            {/* Context & Execution Info */}
            <div className="p-3 bg-zinc-900 border border-zinc-700 rounded-lg space-y-3">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded bg-blue-900/30 flex items-center justify-center">
                    <svg className="w-3 h-3 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <span className="text-xs font-bold text-zinc-300">Context</span>
                </div>
                <p className="text-xs text-zinc-500">
                  Output from upstream nodes will automatically serve as the input context for this task.
                </p>
              </div>
              <div className="border-t border-zinc-700 pt-3">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded bg-emerald-900/30 flex items-center justify-center">
                    <svg className="w-3 h-3 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </div>
                  <span className="text-xs font-bold text-zinc-300">Execution Mode</span>
                </div>
                <p className="text-xs text-zinc-500">
                  <strong className="text-emerald-400">Auto-Inference:</strong> Parallel execution when multiple Agents stem from the same upstream node; serial execution for single-line connections. No manual configuration required.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Knowledge Node Panel
type KnowledgeOption = { id: number; display_name: string; description?: string; is_user: boolean; source_type?: string };

export const KnowledgeNodePanel = ({ data, updateData }: { data: NodeData; updateData: (d: Partial<NodeData>) => void }) => {
  const [options, setOptions] = useState<KnowledgeOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMySources = async () => {
      const token = getToken();
      if (!token) { setOptions([]); return; }
      try {
        setLoading(true);
        setError(null);
        const res = await fetch(buildApiUrl("/api/v1/knowledge/my-sources"), {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Failed to load knowledge base");
        const json = await res.json();
        const subscribed = (json.subscribed_sources || []).map((s: any) => ({ id: s.id, display_name: s.display_name, description: s.description, is_user: false, source_type: s.source_type }));
        const custom = (json.custom_sources || []).map((s: any) => ({ id: s.id, display_name: s.display_name, description: s.description, is_user: true, source_type: s.source_type }));
        setOptions([...subscribed, ...custom]);
      } catch (err: any) {
        setError(err?.message || "Failed to load");
        setOptions([]);
      } finally {
        setLoading(false);
      }
    };
    fetchMySources();
  }, []);

  const handleSelect = (value: string) => {
    const id = parseInt(value, 10);
    const selected = options.find(o => o.id === id);
    if (!selected) {
      updateData({ source_id: undefined, name: undefined, is_user_source: undefined, sourceType: undefined, content: undefined });
      return;
    }
    updateData({ 
      source_id: selected.id, 
      name: selected.display_name, 
      is_user_source: selected.is_user, 
      sourceType: selected.is_user ? 'user' : 'system', 
      content: selected.description 
    });
  };

  const selectedId = data.source_id ? String(data.source_id) : "";

  return (
    <div className="space-y-4">
      <div className="text-xs text-zinc-400">Only sources saved to "My Knowledge Base" (system subscriptions or custom) can be selected.</div>
      <div>
        <label className="text-xs font-bold uppercase text-zinc-400 block mb-2">Saved Knowledge</label>
        <select
          value={selectedId}
          onChange={(e) => handleSelect(e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none text-white"
          disabled={loading}
        >
          <option value="" disabled>{loading ? "Loading..." : "Select a knowledge source"}</option>
          {options.map(opt => (
            <option key={opt.id} value={opt.id}>
              {opt.is_user ? "[Custom]" : "[Subscription]"} {opt.display_name}
            </option>
          ))}
        </select>
        {error && <div className="text-xs text-red-400 mt-1">{error}</div>}
        {!loading && options.length === 0 && !error && (
          <div className="mt-3 p-3 border border-dashed border-zinc-700 rounded-lg text-center">
            <p className="text-xs text-zinc-400 mb-2">No knowledge available.</p>
            <Link href="/tools?category=knowledge" target="_blank">
              <button className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded flex items-center justify-center gap-1 mx-auto transition-colors">
                <Plus className="w-3 h-3" />
                Add from Marketplace
                <ExternalLink className="w-3 h-3 ml-1" />
              </button>
            </Link>
          </div>
        )}
      </div>
      {data.name && (
        <div className="p-3 bg-zinc-900 border border-zinc-700 rounded-lg space-y-1">
          <div className="text-sm text-white">{data.name}</div>
          <div className="text-[10px] text-zinc-400">{data.content || 'No description'}</div>
          <div className="text-[10px] text-emerald-400 uppercase font-bold">
            {data.is_user_source ? 'User' : 'System'}
          </div>
        </div>
      )}
    </div>
  );
};

// End Node Panel
export const EndNodePanel = ({ data, updateData }: { data: NodeData; updateData: (d: Partial<NodeData>) => void }) => (
  <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-300">
    <div>
      <h3 className="text-sm font-bold uppercase text-zinc-400 mb-4 flex items-center gap-2">Output Format</h3>
      <div className="grid grid-cols-2 gap-3 mb-4">
        {['Markdown', 'PDF', 'JSON', 'Email'].map(fmt => (
          <button 
            key={fmt} 
            onClick={() => updateData({ outputFormat: fmt })} 
            className={`flex flex-col items-center justify-center p-3 rounded-lg border transition-all ${data.outputFormat === fmt ? 'bg-red-900/20 border-red-500 text-red-100' : 'bg-zinc-900 border-zinc-700 text-zinc-400'}`}
          >
            <span className="text-xs font-medium">{fmt}</span>
          </button>
        ))}
      </div>
      <div className="mb-2">
        <label className="text-xs font-bold uppercase text-zinc-400 block mb-2">Structure Template</label>
        <select 
          value={data.structureTemplate || 'Standard'} 
          onChange={(e) => updateData({ structureTemplate: e.target.value })} 
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none text-white"
        >
          <option value="Standard">Standard Report</option>
          <option value="TLDR">Executive Summary</option>
          <option value="Raw">Raw Concatenation</option>
        </select>
      </div>
    </div>
    <div className="pt-6 border-t border-zinc-700">
      <h3 className="text-sm font-bold uppercase text-zinc-400 mb-4 flex items-center gap-2">Aggregation Logic</h3>
      <div className="flex bg-zinc-900 p-1 rounded-lg border border-zinc-700 mb-4">
        <button 
          onClick={() => updateData({ aggregationMethod: 'concatenate' })} 
          className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${data.aggregationMethod === 'concatenate' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-400'}`}
        >
          Simple Stitch
        </button>
        <button 
          onClick={() => updateData({ aggregationMethod: 'llm_summary' })} 
          className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${data.aggregationMethod === 'llm_summary' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-400'}`}
        >
          AI Summarize
        </button>
      </div>
      {data.aggregationMethod === 'llm_summary' && (
        <div className="animate-in fade-in slide-in-from-top-2">
          <label className="text-xs font-bold uppercase text-zinc-400 block mb-2">Editor Prompt</label>
          <textarea 
            value={data.summaryPrompt || "You are an editor..."} 
            onChange={(e) => updateData({ summaryPrompt: e.target.value })} 
            className="w-full h-24 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none resize-none text-white"
          />
          <div className="mt-3">
            <label className="text-xs font-bold uppercase text-zinc-400 block mb-2">Summary Routing Tier</label>
            <select
              aria-label="Summary Routing Tier"
              value={data.summaryModel || DEFAULT_LLM_TIER}
              onChange={(e) => updateData({ summaryModel: e.target.value })}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none text-white"
            >
              {LLM_ROUTING_TIERS.map((tier) => (
                <option key={tier.value} value={tier.value}>
                  {tier.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
    <div className="pt-6 border-t border-zinc-700">
      <h3 className="text-sm font-bold uppercase text-zinc-400 mb-4 flex items-center gap-2">Actions</h3>
      <div className="flex items-center justify-between mb-4 p-3 bg-zinc-900 rounded-lg border border-zinc-700">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-yellow-500" />
          <span className="text-sm text-white">Save to Knowledge Base</span>
        </div>
        <button 
          onClick={() => updateData({ saveToHistory: !data.saveToHistory })} 
          className={`w-10 h-5 rounded-full p-1 transition-colors relative ${data.saveToHistory ? 'bg-emerald-500' : 'bg-zinc-700'}`}
        >
          <div className={`w-3 h-3 bg-white rounded-full transition-transform ${data.saveToHistory ? 'translate-x-5' : 'translate-x-0'}`} />
        </button>
      </div>
      <div>
        <label className="text-xs font-bold uppercase text-zinc-400 block mb-2">Notification Channels</label>
        <div className="space-y-2">
          {['Email', 'Slack', 'Webhook'].map(channel => { 
            const active = (data.channels || []).includes(channel); 
            return (
              <div 
                key={channel} 
                onClick={() => { 
                  const current = data.channels || []; 
                  updateData({ channels: active ? current.filter(c => c !== channel) : [...current, channel] }); 
                }} 
                className={`flex items-center p-2 rounded border cursor-pointer transition-all ${active ? 'bg-blue-900/20 border-blue-500' : 'bg-zinc-900 border-zinc-700'}`}
              >
                <div className={`w-4 h-4 rounded border flex items-center justify-center mr-3 ${active ? 'bg-blue-500 border-blue-500' : 'border-zinc-500'}`}>
                  {active && <CheckCircle className="w-3 h-3 text-white" />}
                </div>
                <span className="text-sm text-white">{channel}</span>
              </div>
            ); 
          })}
        </div>
      </div>
    </div>
  </div>
);
