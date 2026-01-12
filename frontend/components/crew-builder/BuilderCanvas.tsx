"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import {
  PlayCircle, ArrowLeft, Plus, Trash2, Save, X, Info, Minus, History, Loader2, Sparkles
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Node, Edge, NodeType, NodeData, NodeVariable } from "./types";
import { SCENARIO_TEMPLATES, ROUTER_TEMPLATES, DEFAULT_LLM_TIER } from "./constants";
import {
  StartNode, AgentNode, RouterNode, KnowledgeNode, EndNode, NodeIcon
} from "./NodeComponents";
import {
  StartNodePanel, AgentNodePanel, RouterNodePanel, KnowledgeNodePanel, EndNodePanel, renderSchemaField
} from "./PropertyPanels";
import { useToast } from "./Toast";
import { VariableAwareTextarea, getUndefinedVariables } from "./VariableAwareTextarea";
import apiClient, { MCPToolDetail } from "@/lib/api";
import { ExecutionStreamContainer } from "./execution-steps/ExecutionStreamContainer";
import { useExecutionStream } from "./execution-steps/useExecutionStream";
import { SkillSelector } from "./SkillSelector/SkillSelector";
import { useSkillCatalog } from "@/hooks/useSkillCatalog";

interface BuilderCanvasProps {
  onBack: () => void;
  onSave: (crewData: any) => Promise<void>;
  onDelete?: () => Promise<void> | void;
  mcpTools: MCPToolDetail[];
  isLoading?: boolean;
  crewId?: number | null;  // If provided, load existing crew
}

// Default nodes for new crew
const DEFAULT_NODES: Node[] = [
  { id: 'start-1', type: 'start', x: 50, y: 300, w: 288, h: 140, data: { inputMode: 'custom', variables: [{name: 'ticker', label: 'Ticker Symbol', type: 'text'}] } },
  { id: 'agent-1', type: 'agent', x: 400, y: 150, w: 288, h: 220, data: { role: 'Researcher', model: DEFAULT_LLM_TIER, goal: 'Research and analyze {{ticker}}', backstory: '', tools: [] } },
  { id: 'end-1', type: 'end', x: 800, y: 300, w: 192, h: 100, data: { outputFormat: 'Markdown', aggregationMethod: 'llm_summary' } }
];
const DEFAULT_EDGES: Edge[] = [
  { from: 'start-1', to: 'agent-1', type: 'control' },
  { from: 'agent-1', to: 'end-1', type: 'control' }
];

/**
 * Convert NodeVariable[] array to JSONSchema format for backend compatibility.
 * This ensures Dashboard's SchemaForm and Preflight's variable_defaults can properly
 * parse the input_schema.
 *
 * Input:  [{name: 'target_asset', label: 'Target Asset', type: 'text', options: [...]}]
 * Output: {type: 'object', properties: {target_asset: {type: 'string', title: 'Target Asset', ...}}, required: [...]}
 */
function convertVariablesToJsonSchema(variables: NodeVariable[] | undefined): Record<string, any> | null {
  if (!variables || variables.length === 0) {
    return null;
  }

  const properties: Record<string, any> = {};
  const required: string[] = [];

  for (const v of variables) {
    const prop: Record<string, any> = {
      title: v.label || v.name,
    };

    // Map NodeVariable type to JSONSchema type
    switch (v.type) {
      case 'number':
        prop.type = 'number';
        break;
      case 'select':
        prop.type = 'string';
        if (v.options && v.options.length > 0) {
          prop.enum = v.options;
          prop.default = v.options[0]; // First option as default
        }
        break;
      case 'text':
      default:
        prop.type = 'string';
        break;
    }

    // Add description if available
    if (v.description) {
      prop.description = v.description;
    }

    properties[v.name] = prop;
    // All variables defined in Start Node are required
    required.push(v.name);
  }

  return {
    type: 'object',
    properties,
    required,
  };
}

/**
 * Convert JSONSchema format back to NodeVariable[] array for Visual Builder display.
 * This handles loading existing crews that were saved with the new JSONSchema format.
 *
 * Input:  {type: 'object', properties: {target_asset: {type: 'string', title: 'Target Asset', enum: [...]}}}
 * Output: [{name: 'target_asset', label: 'Target Asset', type: 'text', options: [...]}]
 */
function convertJsonSchemaToVariables(schema: any): NodeVariable[] | undefined {
  // Handle legacy array format (backwards compatibility)
  if (Array.isArray(schema)) {
    return schema as NodeVariable[];
  }

  // Handle JSONSchema format
  if (schema && typeof schema === 'object' && schema.properties) {
    const variables: NodeVariable[] = [];
    for (const [name, prop] of Object.entries(schema.properties as Record<string, any>)) {
      const variable: NodeVariable = {
        name,
        label: prop.title || name,
        type: 'text', // default
      };

      // Map JSONSchema type back to NodeVariable type
      if (prop.type === 'number') {
        variable.type = 'number';
      } else if (prop.enum && Array.isArray(prop.enum)) {
        variable.type = 'select';
        variable.options = prop.enum;
      }

      // Restore description
      if (prop.description) {
        variable.description = prop.description;
      }

      variables.push(variable);
    }
    return variables.length > 0 ? variables : undefined;
  }

  return undefined;
}

export function BuilderCanvas({ onBack, onSave, onDelete, mcpTools, isLoading, crewId }: BuilderCanvasProps) {
  const toast = useToast();
  const canvasRef = useRef<HTMLDivElement>(null);
  
  // Node and Edge State
  const [nodes, setNodes] = useState<Node[]>(DEFAULT_NODES);
  const [edges, setEdges] = useState<Edge[]>(DEFAULT_EDGES);
  const [loadedCrewName, setLoadedCrewName] = useState<string>("");
  const [isLoadingCrew, setIsLoadingCrew] = useState(false);
  
  // Viewport State
  const [viewport, setViewport] = useState({ x: 0, y: 0, k: 1 });
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  
  // Interaction State
  const [isDraggingNode, setIsDraggingNode] = useState<string | null>(null);
  const [isPanning, setIsPanning] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  
  // Connection State
  const [connecting, setConnecting] = useState<{ nodeId: string; type: 'source' | 'target'; handleId?: string; startX: number; startY: number } | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Run Modal
  const [isRunModalOpen, setIsRunModalOpen] = useState(false);
  const [runInputs, setRunInputs] = useState<Record<string, string>>({});
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [isExecutionPanelOpen, setIsExecutionPanelOpen] = useState(false);
  // Save Modal
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
  const [crewNameInput, setCrewNameInput] = useState<string>("");
  const [isSaving, setIsSaving] = useState(false);

  // Skill Panel State - Sliding panel for skill selection
  const [isSkillPanelOpen, setIsSkillPanelOpen] = useState(false);
  const [skillPanelNodeId, setSkillPanelNodeId] = useState<string | null>(null);

  // Skills catalog for skill panel
  const { catalog: skillCatalog, allSkills } = useSkillCatalog();

  // Helper to open skill panel for a specific node
  const openSkillPanel = (nodeId: string) => {
    console.log('[SkillPanel] Opening panel for node:', nodeId);
    setSkillPanelNodeId(nodeId);
    setIsSkillPanelOpen(true);
  };

  // Helper to get skill keys from a node
  const getNodeSkillKeys = (nodeId: string): string[] => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return [];
    const loadout = (node as any).data.loadout_data;
    if (loadout?.skill_keys) return loadout.skill_keys;
    if (loadout?.tools) return loadout.tools;
    return [];
  };

  // Helper to update skill keys for a node
  const updateNodeSkillKeys = (nodeId: string, keys: string[]) => {
    updateNodeData(nodeId, {
      loadout_data: { skill_keys: keys }
    });
  };

  const { steps, clearSteps } = useExecutionStream(activeRunId);

  // --- Load existing crew data ---
  useEffect(() => {
    if (!crewId) {
      // New crew - use defaults
      setNodes(DEFAULT_NODES);
      setEdges(DEFAULT_EDGES);
      setLoadedCrewName("");
      return;
    }

    const loadCrew = async () => {
      setIsLoadingCrew(true);
      try {
        const crew = await apiClient.getCrewDefinition(crewId);
        
        setLoadedCrewName(crew.name || "");
        setCrewNameInput(crew.name || "");
        
        // Load ui_state if available
        if (crew.ui_state && crew.ui_state.nodes && crew.ui_state.nodes.length > 0) {
          // Validate and transform nodes to ensure correct format
          let loadedNodes: Node[] = crew.ui_state.nodes.map((n: any) => ({
            id: n.id,
            type: n.type as NodeType,
            x: n.x ?? n.position?.x ?? 100,
            y: n.y ?? n.position?.y ?? 100,
            w: n.w ?? 288,
            h: n.h ?? (n.type === 'end' ? 100 : n.type === 'start' ? 140 : 220),
            data: n.data || {}
          }));

          // Sync loadout_data from DB agents (ui_state may be stale)
          if (crew.structure && crew.structure.length > 0) {
            const agentIds = crew.structure.map((s: any) => s.agent_id).filter(Boolean) as number[];
            const agents = await Promise.all(agentIds.map(async (id) => {
              try {
                return await apiClient.getAgentDefinition(id);
              } catch {
                return null;
              }
            }));
            const agentById = new Map<number, any>(agents.filter(Boolean).map((a: any) => [a.id, a]));

            // Merge loadout_data into agent nodes by matching structure order
            const agentNodeIds = loadedNodes.filter(n => n.type === 'agent').map(n => n.id);
            loadedNodes = loadedNodes.map(node => {
              if (node.type !== 'agent') return node;
              const nodeIndex = agentNodeIds.indexOf(node.id);
              if (nodeIndex >= 0 && nodeIndex < crew.structure.length) {
                const agentId = crew.structure[nodeIndex]?.agent_id;
                const agent = agentById.get(agentId);
                if (agent?.loadout_data) {
                  return { ...node, data: { ...node.data, loadout_data: agent.loadout_data } };
                }
              }
              return node;
            });
          }

          const loadedEdges: Edge[] = (crew.ui_state.edges || []).map((e: any) => ({
            from: e.from ?? e.source,
            to: e.to ?? e.target,
            type: e.type || 'control',
            handleId: e.handleId
          }));

          setNodes(loadedNodes);
          setEdges(loadedEdges);
          
          // Set viewport if available
          if (crew.ui_state.viewport) {
            setViewport({
              x: crew.ui_state.viewport.x || 0,
              y: crew.ui_state.viewport.y || 0,
              k: crew.ui_state.viewport.zoom || crew.ui_state.viewport.k || 1
            });
          }
        } else if (crew.structure && crew.structure.length > 0) {
          // No ui_state, but DB structure exists: materialize a readable canvas for templates/seeded crews.
          const agentIds = crew.structure.map((s: any) => s.agent_id).filter(Boolean) as number[];
          const taskIds = crew.structure.flatMap((s: any) => s.tasks || []).filter(Boolean) as number[];
          const uniqueTaskIds = Array.from(new Set(taskIds));

          const [agents, tasks] = await Promise.all([
            Promise.all(agentIds.map(async (id) => {
              try {
                return await apiClient.getAgentDefinition(id);
              } catch (err) {
                console.warn(`[CrewBuilder] Failed to load agent ${id}:`, err);
                return null;
              }
            })),
            Promise.all(uniqueTaskIds.map(async (id) => {
              try {
                return await apiClient.getTaskDefinition(id);
              } catch (err) {
                console.warn(`[CrewBuilder] Failed to load task ${id}:`, err);
                return null;
              }
            }))
          ]);

          const agentById = new Map<number, any>(agents.filter(Boolean).map((a: any) => [a.id, a]));
          const taskById = new Map<number, any>(tasks.filter(Boolean).map((t: any) => [t.id, t]));

          const spacingX = 360;
          const baseX = 100;
          const baseY = 140;

          const materializedNodes: Node[] = [];
          const materializedEdges: Edge[] = [];

          materializedNodes.push({
            id: "start",
            type: "start",
            x: baseX,
            y: baseY,
            w: 288,
            h: 140,
            data: {
              name: crew.name || "Start",
              variables: convertJsonSchemaToVariables(crew.input_schema)
            }
          });

          const agentNodeIds: string[] = [];
          crew.structure.forEach((entry: any, index: number) => {
            const agent = agentById.get(entry.agent_id);
            const taskId = (entry.tasks || [])[0];
            const task = typeof taskId === 'number' ? taskById.get(taskId) : null;

            const nodeId = `agent-${entry.agent_id}`;
            agentNodeIds.push(nodeId);

            materializedNodes.push({
              id: nodeId,
              type: "agent",
              x: baseX + spacingX * (index + 1),
              y: baseY,
              w: 288,
              h: 220,
              data: {
                role: agent?.role || agent?.name || `Agent ${entry.agent_id}`,
                goal: agent?.goal || "",
                backstory: agent?.backstory || "",
                allowDelegation: agent?.allow_delegation || false,
                verbose: agent?.verbose ?? true,
                loadout_data: agent?.loadout_data || undefined,
                taskName: task?.name,
                taskDescription: task?.description,
                expectedOutput: task?.expected_output,
              }
            });
          });

          materializedNodes.push({
            id: "end",
            type: "end",
            x: baseX + spacingX * (agentNodeIds.length + 1),
            y: baseY,
            w: 288,
            h: 100,
            data: {
              name: "End",
            }
          });

          if (agentNodeIds.length > 0) {
            materializedEdges.push({ from: "start", to: agentNodeIds[0], type: "control" });
            for (let i = 0; i < agentNodeIds.length - 1; i += 1) {
              materializedEdges.push({ from: agentNodeIds[i], to: agentNodeIds[i + 1], type: "control" });
            }
            materializedEdges.push({ from: agentNodeIds[agentNodeIds.length - 1], to: "end", type: "control" });
          } else {
            materializedEdges.push({ from: "start", to: "end", type: "control" });
          }

          setNodes(materializedNodes);
          setEdges(materializedEdges);
          setViewport({ x: 0, y: 0, k: 1 });
        } else {
          // No ui_state and no structure, use defaults
          setNodes(DEFAULT_NODES);
          setEdges(DEFAULT_EDGES);
        }
      } catch (err) {
        console.error("Failed to load crew:", err);
        toast("Failed to load crew configuration", "error");
      } finally {
        setIsLoadingCrew(false);
      }
    };

    loadCrew();
  }, [crewId]);

  // --- Helpers ---
  const screenToCanvas = useCallback((sx: number, sy: number) => {
    if (!canvasRef.current) return { x: 0, y: 0 };
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      x: (sx - rect.left - viewport.x) / viewport.k,
      y: (sy - rect.top - viewport.y) / viewport.k
    };
  }, [viewport]);

  const getAvailableVariables = () => {
    const startNode = nodes.find(n => n.type === 'start');
    return startNode?.data.variables?.map(v => v.name) || [];
  };

  const getConnectedKnowledge = (agentId: string) => {
    const knowledgeEdges = edges.filter(e => e.to === agentId && e.type === 'resource');
    return knowledgeEdges.map(e => nodes.find(n => n.id === e.from && n.type === 'knowledge')).filter(Boolean) as Node[];
  };

  // Helper: Extract all {{variable}} references from text
  const extractVariableRefs = (text: string | undefined): string[] => {
    if (!text) return [];
    const matches = text.match(/\{\{(\w+)\}\}/g) || [];
    return matches.map(m => m.slice(2, -2)); // Remove {{ and }}
  };

  // Helper: Find all Agent/Task fields that reference a specific variable
  const findVariableUsages = (varName: string): { nodeName: string; fields: string[] }[] => {
    const usages: { nodeName: string; fields: string[] }[] = [];

    nodes.filter(n => n.type === 'agent').forEach(node => {
      const fields: string[] = [];
      const nodeName = node.data.role || node.data.taskName || 'Unnamed Agent';

      if (extractVariableRefs(node.data.goal).includes(varName)) fields.push('Goal');
      if (extractVariableRefs(node.data.backstory).includes(varName)) fields.push('Backstory');
      if (extractVariableRefs(node.data.taskDescription).includes(varName)) fields.push('Task Description');
      if (extractVariableRefs(node.data.expectedOutput).includes(varName)) fields.push('Expected Output');

      if (fields.length > 0) {
        usages.push({ nodeName, fields });
      }
    });

    nodes.filter(n => n.type === 'router').forEach(node => {
      const fields: string[] = [];
      const nodeName = node.data.name || 'Unnamed Router';

      if (extractVariableRefs(node.data.instruction).includes(varName)) fields.push('Routing Instruction');

      if (fields.length > 0) {
        usages.push({ nodeName, fields });
      }
    });

    return usages;
  };

  const updateNodeData = (id: string, newData: Partial<NodeData>) => {
    // Check if this is a Start Node variable change
    const targetNode = nodes.find(n => n.id === id);
    if (targetNode?.type === 'start' && newData.variables !== undefined) {
      const oldVars = new Set((targetNode.data.variables || []).map(v => v.name));
      const newVars = new Set((newData.variables || []).map(v => v.name));

      // Find removed variables
      const removedVars = [...oldVars].filter(v => !newVars.has(v));

      // Check if any removed variable is still being used
      const affectedUsages: { varName: string; usages: { nodeName: string; fields: string[] }[] }[] = [];
      removedVars.forEach(varName => {
        const usages = findVariableUsages(varName);
        if (usages.length > 0) {
          affectedUsages.push({ varName, usages });
        }
      });

      // Show warning if there are affected usages
      if (affectedUsages.length > 0) {
        const warningLines = affectedUsages.map(({ varName, usages }) => {
          const usageDetails = usages.map(u => `  • ${u.nodeName}: ${u.fields.join(', ')}`).join('\n');
          return `Variable "{{${varName}}}" is used in:\n${usageDetails}`;
        }).join('\n\n');

        toast(
          `⚠️ Warning: Variable(s) still in use!\n\n${warningLines}\n\nPlease update these references to avoid runtime errors.`,
          "warning"
        );
      }
    }

    setNodes(prev => prev.map(n => n.id === id ? { ...n, data: { ...n.data, ...newData } } : n));
  };

  // --- Validation Logic ---
  const getOutgoers = (nodeId: string, currentEdges: Edge[]) => {
    return currentEdges.filter(e => e.from === nodeId).map(e => nodes.find(n => n.id === e.to)).filter(Boolean) as Node[];
  };

  const hasCycle = (sourceId: string, targetId: string, currentEdges: Edge[]) => {
    const visited = new Set();
    const stack = [targetId];
    
    while (stack.length > 0) {
      const current = stack.pop()!;
      if (current === sourceId) return true;
      if (!visited.has(current)) {
        visited.add(current);
        const neighbors = getOutgoers(current, currentEdges);
        neighbors.forEach(n => stack.push(n.id));
      }
    }
    return false;
  };

  const isValidConnection = (sourceId: string, targetId: string, handleId?: string) => {
    const sourceNode = nodes.find(n => n.id === sourceId);
    const targetNode = nodes.find(n => n.id === targetId);
    
    if (!sourceNode || !targetNode) return false;

    // Self-loop and cycles
    if (sourceId === targetId) { toast("Cannot connect a node to itself.", "error"); return false; }
    if (hasCycle(sourceId, targetId, edges)) { toast("Cycle detected!", "error"); return false; }

    // Connection matrix
    // Start: only to Agent or Router (control)
    if (sourceNode.type === 'start') {
      if (targetNode.type !== 'agent' && targetNode.type !== 'router') { toast("Start can only connect to Agent or Router.", "error"); return false; }
    }
    // Knowledge: only to Agent, as resource
    if (sourceNode.type === 'knowledge') {
      if (targetNode.type !== 'agent') { toast("Knowledge can only connect to Agent.", "error"); return false; }
    }
    // Router single input
    if (targetNode.type === 'router') {
      const existingInputs = edges.filter(e => e.to === targetId);
      if (existingInputs.length >= 1) { toast("Router can only accept one input stream.", "error"); return false; }
    }
    // Start cannot be target
    if (targetNode.type === 'start') { toast("Start node cannot accept inputs.", "error"); return false; }
    // End cannot be source
    if (sourceNode.type === 'end') { toast("End node cannot have outputs.", "error"); return false; }
    // Knowledge cannot be target
    if (targetNode.type === 'knowledge') { toast("Knowledge nodes cannot accept inputs.", "error"); return false; }
    // Knowledge cannot target Router/End (covered by knowledge target guard + start guard)
    // Start cannot link directly to End
    if (sourceNode.type === 'start' && targetNode.type === 'end') { toast("Start cannot connect directly to End.", "error"); return false; }

    return true;
  };

  // --- Event Handlers ---
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (e.ctrlKey || e.metaKey) {
      const zoomSensitivity = 0.001;
      const delta = -e.deltaY * zoomSensitivity;
      const newScale = Math.min(Math.max(viewport.k + delta, 0.1), 3);
      if (!canvasRef.current) return;
      const rect = canvasRef.current.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const newX = mouseX - (mouseX - viewport.x) * (newScale / viewport.k);
      const newY = mouseY - (mouseY - viewport.y) * (newScale / viewport.k);
      setViewport({ x: newX, y: newY, k: newScale });
    } else {
      setViewport(prev => ({ ...prev, x: prev.x - e.deltaX, y: prev.y - e.deltaY }));
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 1 || (e.button === 0 && (e.target as HTMLElement).closest('.canvas-bg'))) {
      setIsPanning(true);
      setDragStart({ x: e.clientX, y: e.clientY });
      e.preventDefault();
    } else {
      setSelectedNodeId(null);
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    setMousePos({ x: e.clientX, y: e.clientY });
    if (isPanning) {
      const dx = e.clientX - dragStart.x;
      const dy = e.clientY - dragStart.y;
      setViewport(prev => ({ ...prev, x: prev.x + dx, y: prev.y + dy }));
      setDragStart({ x: e.clientX, y: e.clientY });
    }
    if (isDraggingNode) {
      const dx = (e.clientX - dragStart.x) / viewport.k;
      const dy = (e.clientY - dragStart.y) / viewport.k;
      setNodes(prev => prev.map(n => n.id === isDraggingNode ? { ...n, x: n.x + dx, y: n.y + dy } : n));
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setIsDraggingNode(null);
    if (connecting) { setConnecting(null); }
  };

  const handleNodeMouseDown = (e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    if (e.button === 0) {
      setSelectedNodeId(nodeId);
      setIsDraggingNode(nodeId);
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleHandleMouseDown = (e: React.MouseEvent, nodeId: string, type: 'source' | 'target', handleId?: string) => {
    e.stopPropagation();
    e.preventDefault();
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    const startX = rect.left + rect.width / 2;
    const startY = rect.top + rect.height / 2;
    const cPos = screenToCanvas(startX, startY);
    setConnecting({ nodeId, type, handleId, startX: cPos.x, startY: cPos.y });
  };

  const handleNodeMouseUp = (e: React.MouseEvent, targetNodeId: string) => {
    if (connecting) {
      e.stopPropagation();
      if (connecting.nodeId !== targetNodeId) {
        if (isValidConnection(connecting.nodeId, targetNodeId, connecting.handleId)) {
          const sourceNode = nodes.find(n => n.id === connecting.nodeId);
          const newEdge: Edge = { 
            from: connecting.nodeId, 
            to: targetNodeId, 
            handleId: connecting.handleId,
            type: sourceNode?.type === 'knowledge' ? 'resource' : 'control'
          };
          setEdges(prev => [...prev, newEdge]);
          toast("Connected!", "success");
        }
      }
      setConnecting(null);
    }
  };

  // --- Drag and Drop from Sidebar ---
  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const type = e.dataTransfer.getData('application/reactflow') as NodeType;
    if (type) {
      if (type === 'start' && nodes.some(n => n.type === 'start')) {
        toast("Only one Start node is allowed.", "error");
        return;
      }
      const pos = screenToCanvas(e.clientX, e.clientY);
      const newNode: Node = {
        id: `${type}-${Date.now()}`,
        type,
        x: pos.x - 100,
        y: pos.y - 50,
        w: type === 'knowledge' ? 224 : (type === 'router' ? 160 : type === 'start' ? 288 : 256),
        h: type === 'knowledge' ? 120 : (type === 'router' ? 160 : type === 'start' ? 140 : 120),
        data: type === 'start' ? { inputMode: 'custom', variables: [] } : (type === 'knowledge' ? { sourceType: 'File' } : {})
      };
      setNodes(prev => [...prev, newNode]);
      setSelectedNodeId(newNode.id);
    }
  };
  const onSidebarDragStart = (e: React.DragEvent, type: NodeType) => { e.dataTransfer.setData('application/reactflow', type); e.dataTransfer.effectAllowed = 'copy'; };

  // --- Run Validation ---
  const handleRunClick = () => {
    if (!crewId) {
      toast("Please save this Crew before running.", "error");
      return;
    }
    const hasStart = nodes.some(n => n.type === 'start');
    const hasEnd = nodes.some(n => n.type === 'end');
    if (!hasStart || !hasEnd) { toast("Validation Failed: Must have at least one Start Node and one End Node.", "error"); return; }
    const orphans = nodes.filter(n => n.type === 'agent').filter(n => !edges.some(e => e.to === n.id));
    if (orphans.length > 0) { toast(`Validation Failed: Agent "${orphans[0].data.role || 'Unnamed'}" is not connected.`, "error"); return; }
    const danglingRouters = nodes.filter(n => n.type === 'router').filter(n => !edges.some(e => e.from === n.id));
    if (danglingRouters.length > 0) { toast(`Validation Failed: Router "${danglingRouters[0].data.name || 'Unnamed'}" has no output.`, "error"); return; }
    setIsRunModalOpen(true);
  };

  const handleStartExecution = async () => {
    if (!crewId) {
      toast("Please save this Crew before running.", "error");
      return;
    }

    setIsRunModalOpen(false);
    setIsExecutionPanelOpen(true);
    clearSteps();
    setActiveRunId(null);

    try {
      const response = await apiClient.startAnalysisV2({
        crew_id: crewId,
        variables: runInputs,
      });
      setActiveRunId(response.job_id);
      toast("Crew execution started!", "success");
    } catch (err) {
      console.error("Failed to start execution:", err);
      toast("Failed to start execution", "error");
      setIsExecutionPanelOpen(false);
      setActiveRunId(null);
    }
  };

  // --- Save Handler ---
  const handleSave = async () => {
    const startNode = nodes.find(n => n.type === 'start');
    const agentNodes = nodes.filter(n => n.type === 'agent');
    const endNode = nodes.find(n => n.type === 'end');

    if (!startNode) { toast("Missing Start Node", "error"); return; }
    if (agentNodes.length === 0) { toast("Please add at least one Agent", "error"); return; }
    if (!endNode) { toast("Missing End Node", "error"); return; }
    const danglingRouters = nodes.filter(n => n.type === 'router').filter(n => !edges.some(e => e.from === n.id));
    if (danglingRouters.length > 0) { toast(`Router "${danglingRouters[0].data.name || 'Unnamed'}" must have at least one output.`, "error"); return; }

    // === SAVE GUARD: Check for undefined variables ===
    const availableVars = getAvailableVariables();
    const validationErrors: { nodeName: string; nodeType: string; field: string; undefinedVars: string[] }[] = [];

    // Check Agent nodes - ALL fields that can contain variables
    agentNodes.forEach(node => {
      const nodeName = node.data.role || node.data.taskName || 'Unnamed Agent';

      // Check goal (Agent's objective - critical field!)
      if (node.data.goal) {
        const undefinedVars = getUndefinedVariables(
          node.data.goal,
          availableVars.map(v => ({ name: v, type: 'text' }))
        );
        if (undefinedVars.length > 0) {
          validationErrors.push({
            nodeName,
            nodeType: 'Agent',
            field: 'Goal',
            undefinedVars
          });
        }
      }

      // Check backstory
      if (node.data.backstory) {
        const undefinedVars = getUndefinedVariables(
          node.data.backstory,
          availableVars.map(v => ({ name: v, type: 'text' }))
        );
        if (undefinedVars.length > 0) {
          validationErrors.push({
            nodeName,
            nodeType: 'Agent',
            field: 'Backstory',
            undefinedVars
          });
        }
      }

      // Check taskDescription
      if (node.data.taskDescription) {
        const undefinedVars = getUndefinedVariables(
          node.data.taskDescription,
          availableVars.map(v => ({ name: v, type: 'text' }))
        );
        if (undefinedVars.length > 0) {
          validationErrors.push({
            nodeName,
            nodeType: 'Agent',
            field: 'Task Description',
            undefinedVars
          });
        }
      }

      // Check expectedOutput
      if (node.data.expectedOutput) {
        const undefinedVars = getUndefinedVariables(
          node.data.expectedOutput,
          availableVars.map(v => ({ name: v, type: 'text' }))
        );
        if (undefinedVars.length > 0) {
          validationErrors.push({
            nodeName,
            nodeType: 'Agent',
            field: 'Expected Output',
            undefinedVars
          });
        }
      }
    });

    // Check Router nodes
    const routerNodes = nodes.filter(n => n.type === 'router');
    routerNodes.forEach(node => {
      if (node.data.instruction) {
        const undefinedVars = getUndefinedVariables(
          node.data.instruction,
          availableVars.map(v => ({ name: v, type: 'text' }))
        );
        if (undefinedVars.length > 0) {
          validationErrors.push({
            nodeName: node.data.name || 'Unnamed Router',
            nodeType: 'Router',
            field: 'Routing Instruction',
            undefinedVars
          });
        }
      }
    });

    // If validation errors exist, block save and show detailed error
    if (validationErrors.length > 0) {
      const errorMessages = validationErrors.map(err => 
        `• ${err.nodeType} "${err.nodeName}" (${err.field}): ${err.undefinedVars.map(v => `{{${v}}}`).join(', ')}`
      ).join('\n');
      
      toast(
        `Cannot save: Undefined variables detected\n\n${errorMessages}\n\nPlease define these variables in the Start node or fix the references before saving.`,
        "error"
      );
      return;
    }

    const crewName = crewNameInput || startNode?.data.name || "Untitled Crew";
    setCrewNameInput(crewName);

    const agents = agentNodes.map(n => ({
      name: n.data.role || "Unnamed Agent",
      role: n.data.role || "Unnamed Agent",
      goal: n.data.goal || "",
      backstory: n.data.backstory || "",
      tools: n.data.tools || [],
      llm_config_id: n.data.llm_config_id,
      llm_type: n.data.model || DEFAULT_LLM_TIER,
      verbose: n.data.verbose ?? true,
      allow_delegation: n.data.allowDelegation || false,
      max_iter: n.data.maxIter || 3,
      temperature: n.data.temperature,
      top_p: n.data.top_p,
      max_tokens: n.data.max_tokens,
      knowledge_config: {
        source_ids: getConnectedKnowledge(n.id).filter(k => !k.data.is_user_source).map(k => k.data.source_id).filter(Boolean) as number[],
        user_source_ids: getConnectedKnowledge(n.id).filter(k => k.data.is_user_source).map(k => k.data.source_id).filter(Boolean) as number[],
        include_trading_lessons: false,
        max_lessons: 5
      }
    }));

    const tasks = agentNodes.map(n => {
      const incomingEdges = edges.filter(e => e.to === n.id);
      const dependencyAgentRoles = incomingEdges
        .map(e => nodes.find(node => node.id === e.from && node.type === 'agent')?.data.role)
        .filter(Boolean) as string[];
      
      return {
        name: `${n.data.role} Task`,
        description: n.data.goal || "",
        expected_output: `Result of ${n.data.role || "agent task"} analysis`,
        agent_id: n.data.role || "Unnamed Agent",
        context_task_ids: dependencyAgentRoles.map(role => `${role} Task`),
        async_execution: false
      };
    });

    const uiState = {
      viewport: { x: viewport.x, y: viewport.y, zoom: viewport.k },
      nodes: nodes.map(n => ({
        id: n.id,
        type: n.type,
        position: { x: n.x, y: n.y },
        data: n.data
      })),
      edges: edges.map(e => ({
        source: e.from,
        target: e.to,
        sourceHandle: e.handleId,
        type: e.type === 'resource' ? 'resource' : 'control'
      }))
    };

    const crewData = {
      name: crewName,
      description: startNode?.data.templateId
        ? `Based on ${SCENARIO_TEMPLATES[startNode.data.templateId]?.name || startNode.data.templateId} template`
        : "Custom Crew created via Visual Builder",
      agents,
      tasks,
      process: nodes.some(n => n.type === 'router') ? 'hierarchical' : 'sequential',
      memory: true,
      max_iter: 3,
      verbose: true,
      debate_rounds: 1,
      is_template: false,
      ui_state: uiState,
      input_schema: convertVariablesToJsonSchema(startNode.data.variables),
      router_config: nodes.filter(n => n.type === 'router').map(r => ({
        id: r.id,
        name: r.data.name,
        instruction: r.data.instruction,
        routes: r.data.routes,
        default_route_id: r.data.defaultRouteId,
        model: r.data.routerModel
      }))
    };

    setIsSaving(true);
    try {
      await onSave(crewData);
      setIsSaveModalOpen(false);
    } finally {
      setIsSaving(false);
    }
  };

  // --- Rendering Helpers ---
  const renderConnectionLine = () => {
    if (!connecting || !canvasRef.current) return null;
    const start = { x: connecting.startX, y: connecting.startY };
    const end = screenToCanvas(mousePos.x, mousePos.y);
    const sourceNode = nodes.find(n => n.id === connecting.nodeId);
    const isKnowledge = sourceNode && sourceNode.type === 'knowledge';
    const isResource = sourceNode?.type === 'knowledge';
    return (
      <path 
        d={`M ${start.x} ${start.y} C ${start.x + 100} ${start.y}, ${end.x - 100} ${end.y}, ${end.x} ${end.y}`} 
        stroke={isResource ? "#eab308" : "#3b82f6"} 
        strokeWidth="2" 
        fill="none" 
        strokeDasharray={isResource ? "6,6" : "0"} 
        className="pointer-events-none animate-pulse" 
      />
    );
  };

  const selectedNode = nodes.find(n => n.id === selectedNodeId);

  const renderRunModalContent = () => {
    const startNode = nodes.find(n => n.type === 'start');
    if (!startNode) return null;
    const isTemplate = startNode.data.inputMode === 'template' && startNode.data.templateId;
    
    if (isTemplate) {
      const schema = startNode.data.inputSchema || [];
      return (
        <div className="space-y-4">
          <div className="p-3 bg-blue-900/20 border border-blue-900/50 rounded-lg text-sm text-blue-200 mb-4 flex items-start gap-3">
            <Info className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <div className="font-bold">Scenario: {SCENARIO_TEMPLATES[startNode.data.templateId!]?.name}</div>
              <div className="opacity-80 text-xs">Fill in the structured parameters below to start the crew.</div>
            </div>
          </div>
          {schema.map((field: any) => (
            <div key={field.key}>
              <label className="text-xs font-bold uppercase text-zinc-400 block mb-1.5">{field.label} {field.required && <span className="text-red-400">*</span>}</label>
              {renderSchemaField(field, runInputs[field.key], (e: any) => setRunInputs(prev => ({ ...prev, [field.key]: e.target.value })))}
            </div>
          ))}
        </div>
      );
    }
    const variables = startNode.data.variables || [];
    return (
      <div className="space-y-4">
        {variables.length > 0 ? variables.map(v => (
          <div key={v.name}>
            <label className="text-xs font-bold uppercase text-zinc-400 block mb-1.5">{v.name}</label>
            <input 
              type="text" 
              value={runInputs[v.name] || ''} 
              onChange={(e) => setRunInputs(prev => ({ ...prev, [v.name]: e.target.value }))} 
              className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-emerald-500 text-white" 
            />
          </div>
        )) : <div className="text-sm text-zinc-500 italic">No inputs required.</div>}
      </div>
    );
  };

  return (
    <div className="h-[calc(100vh-3.5rem)] flex overflow-hidden bg-[var(--bg-app)]">
      {/* Sidebar Tools */}
      <div className="w-16 bg-[var(--bg-panel)] border-r border-[var(--border-color)] flex flex-col items-center py-4 gap-4 z-20 shadow-xl">
        <button onClick={onBack} className="mb-4 p-2 text-[var(--text-secondary)] hover:text-white hover:bg-[var(--bg-card)] rounded-lg" title="Back to Crews">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="w-8 h-[1px] bg-[var(--border-color)] mb-2" />
        {(['start', 'agent', 'router', 'knowledge', 'end'] as NodeType[]).map(type => (
          <div key={type} className="group relative" draggable onDragStart={(e) => onSidebarDragStart(e, type)}>
            <div className={`p-3 bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] cursor-grab transition-all hover:scale-110 active:scale-95 ${
              type === 'start' ? 'hover:border-green-500 hover:text-green-500' : 
              type === 'agent' ? 'hover:border-blue-500 hover:text-blue-500' : 
              type === 'router' ? 'hover:border-purple-500 hover:text-purple-500' : 
              type === 'knowledge' ? 'hover:border-yellow-500 hover:text-yellow-500' : 
              'hover:border-red-500 hover:text-red-500'
            }`}>
              <NodeIcon type={type} className="w-5 h-5" />
            </div>
            <div className="absolute left-full ml-2 top-2 bg-black px-2 py-1 rounded text-xs whitespace-nowrap hidden group-hover:block z-50 pointer-events-none border border-zinc-800">
              {type.charAt(0).toUpperCase() + type.slice(1)} Node
            </div>
          </div>
        ))}
      </div>
      
      {/* Canvas Area */}
      <div 
        ref={canvasRef} 
        className="flex-1 relative bg-[var(--bg-app)] overflow-hidden cursor-default select-none canvas-bg" 
        onWheel={handleWheel} 
        onMouseDown={handleMouseDown} 
        onMouseMove={handleMouseMove} 
        onMouseUp={handleMouseUp} 
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {/* Loading Overlay */}
        {isLoadingCrew && (
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
              <span className="text-sm text-zinc-300">Loading crew configuration...</span>
            </div>
          </div>
        )}
        <div 
          className="absolute inset-0 pointer-events-none opacity-20" 
          style={{ 
            transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.k})`, 
            transformOrigin: '0 0', 
            backgroundImage: 'radial-gradient(#52525b 1px, transparent 1px)', 
            backgroundSize: '24px 24px' 
          }} 
        />
        <div style={{ transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.k})`, transformOrigin: '0 0', width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}>
          <svg className="overflow-visible absolute inset-0 pointer-events-none w-full h-full">
            {edges.map((edge, i) => {
              const fromNode = nodes.find(n => n.id === edge.from);
              const toNode = nodes.find(n => n.id === edge.to);
              if (!fromNode || !toNode) return null;
              let startX: number, startY: number;
              if (fromNode.type === 'router' && edge.handleId) {
                const routes = fromNode.data.routes || [];
                const routeIndex = routes.findIndex(r => r.id === edge.handleId);
                if (routeIndex !== -1) {
                  const topPercent = ((routeIndex + 1) / (routes.length + 1));
                  startX = fromNode.x + fromNode.w; 
                  startY = fromNode.y + (fromNode.h * topPercent); 
                } else { startX = fromNode.x + fromNode.w; startY = fromNode.y + fromNode.h / 2; }
              } else { startX = fromNode.x + fromNode.w; startY = fromNode.y + fromNode.h / 2; }
              const endX = toNode.x;
              const endY = toNode.y + toNode.h / 2;
              const isKnowledgeFlow = edge.type === 'resource' || fromNode.type === 'knowledge';
              const edgeColor = isKnowledgeFlow ? '#eab308' : '#3b82f6';
              return (
                <path 
                  key={i} 
                  d={`M ${startX} ${startY} C ${startX + 100} ${startY}, ${endX - 100} ${endY}, ${endX} ${endY}`} 
                  stroke={edgeColor} 
                  strokeWidth="2" 
                  fill="none" 
                  strokeDasharray={isKnowledgeFlow ? "6,6" : "0"} 
                  className="hover:stroke-blue-400 transition-colors cursor-pointer" 
                  onClick={(e) => { if (e.ctrlKey) { setEdges(prev => prev.filter((_, idx) => idx !== i)); } }} 
                />
              );
            })}
            {renderConnectionLine()}
          </svg>
          {nodes.map(node => (
            <div 
              key={node.id} 
              style={{ left: node.x, top: node.y }} 
              className="absolute" 
              onMouseDown={(e) => handleNodeMouseDown(e, node.id)} 
              onMouseUp={(e) => handleNodeMouseUp(e, node.id)}
            >
              {node.type === 'start' && <StartNode data={node.data} selected={selectedNodeId === node.id} onHandleMouseDown={(e: any, type: any, id: any) => handleHandleMouseDown(e, node.id, type, id)} />}
              {node.type === 'agent' && <AgentNode data={node.data} selected={selectedNodeId === node.id} connectedKnowledgeCount={getConnectedKnowledge(node.id).length} mcpTools={mcpTools} onHandleMouseDown={(e: any, type: any, id: any) => handleHandleMouseDown(e, node.id, type, id)} />}
              {node.type === 'router' && <RouterNode data={node.data} selected={selectedNodeId === node.id} onHandleMouseDown={(e: any, type: any, id: any) => handleHandleMouseDown(e, node.id, type, id)} />}
              {node.type === 'knowledge' && <KnowledgeNode data={node.data} selected={selectedNodeId === node.id} onHandleMouseDown={(e: any, type: any, id: any) => handleHandleMouseDown(e, node.id, type, id)} />}
              {node.type === 'end' && <EndNode data={node.data} selected={selectedNodeId === node.id} onHandleMouseDown={(e: any, type: any, id: any) => handleHandleMouseDown(e, node.id, type, id)} />}
              {selectedNodeId === node.id && node.type !== 'start' && (
                <div 
                  className="absolute -top-3 -right-3 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center cursor-pointer hover:scale-110 shadow-md z-50 text-white" 
                  onClick={(e) => { 
                    e.stopPropagation(); 
                    setNodes(prev => prev.filter(n => n.id !== node.id)); 
                    setEdges(prev => prev.filter(edge => edge.from !== node.id && edge.to !== node.id)); 
                    setSelectedNodeId(null); 
                  }}
                >
                  <X className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}
        </div>
        
        {/* Top Controls */}
        <div className="absolute top-4 right-4 flex gap-2 z-30">
          <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg flex items-center shadow-lg">
            <button onClick={() => setViewport(v => ({ ...v, k: Math.min(v.k + 0.1, 3) }))} className="p-2 hover:bg-[var(--bg-card)] text-[var(--text-secondary)]">
              <Plus className="w-4 h-4" />
            </button>
            <div className="w-[1px] h-4 bg-[var(--border-color)]" />
            <button onClick={() => setViewport(v => ({ ...v, k: Math.max(v.k - 0.1, 0.1) }))} className="p-2 hover:bg-[var(--bg-card)] text-[var(--text-secondary)]">
              <Minus className="w-4 h-4" />
            </button>
            <div className="w-[1px] h-4 bg-[var(--border-color)]" />
            <button onClick={() => setViewport({ x: 0, y: 0, k: 1 })} className="p-2 hover:bg-[var(--bg-card)] text-[var(--text-secondary)] text-xs font-mono">1:1</button>
          </div>
          <button
            onClick={handleRunClick}
            disabled={isLoading || isLoadingCrew || !crewId}
            className="bg-emerald-500 hover:bg-emerald-400 text-black font-bold px-6 py-2 rounded-lg shadow-lg shadow-green-900/20 flex items-center gap-2 transition-transform hover:scale-105 disabled:opacity-50"
          >
            <PlayCircle className="w-4 h-4" /> Run Crew
          </button>
          <button 
            onClick={() => setIsSaveModalOpen(true)} 
            disabled={isLoading}
            className="bg-emerald-500 hover:bg-emerald-400 text-black font-bold px-6 py-2 rounded-lg shadow-lg shadow-green-900/20 flex items-center gap-2 transition-transform hover:scale-105 disabled:opacity-50"
          >
            <Save className="w-4 h-4" /> {isLoading ? "Saving..." : "Save Crew"}
          </button>
          <button 
            onClick={async () => { 
              if (!onDelete) return; 
              if (confirm("Are you sure you want to delete this Crew configuration? This action cannot be undone.")) { 
                await onDelete(); 
              } 
            }} 
            className="bg-red-600 hover:bg-red-500 text-white font-bold px-6 py-2 rounded-lg shadow-lg flex items-center gap-2 transition-transform hover:scale-105"
          >
            <Trash2 className="w-4 h-4" /> Delete Crew
          </button>
        </div>

        {/* Execution Panel */}
        {isExecutionPanelOpen && (
          <div className="absolute bottom-4 right-4 w-[480px] h-[360px] z-40 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg shadow-xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-color)]">
              <div className="text-xs font-bold tracking-wider text-white">
                Execution{activeRunId ? ` (${activeRunId})` : ""}
              </div>
              <button
                onClick={() => {
                  setIsExecutionPanelOpen(false);
                  setActiveRunId(null);
                  clearSteps();
                }}
                className="text-[var(--text-secondary)] hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 min-h-0 p-2">
              <ExecutionStreamContainer steps={steps} />
            </div>
          </div>
        )}
        
        {/* Bottom Help */}
        <div className="absolute bottom-4 left-4 text-[10px] text-[var(--text-secondary)] bg-[var(--bg-panel)]/80 p-2 rounded border border-[var(--border-color)] pointer-events-none">
          Scroll to Zoom • Space + Drag to Pan • Drag from Sidebar to Add • Ctrl + Click Edge to Delete
        </div>
      </div>

      {/* Properties Panel */}
      <div className={`w-80 bg-[var(--bg-panel)] border-l border-[var(--border-color)] flex flex-col transition-all duration-300 transform z-20 shadow-xl ${selectedNodeId ? 'translate-x-0' : 'translate-x-full absolute right-0 h-full'}`}>
        {selectedNodeId && selectedNode && (
          <>
            <div className="p-4 border-b border-[var(--border-color)] flex justify-between items-center bg-[var(--bg-panel)]">
              <div className="flex items-center gap-2">
                <NodeIcon type={selectedNode.type} className="w-4 h-4 text-[var(--text-secondary)]" />
                <h3 className="font-bold uppercase text-sm tracking-wider text-white">Configuration</h3>
              </div>
              <button onClick={() => setSelectedNodeId(null)} className="text-[var(--text-secondary)] hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {selectedNode.type === 'start' && <StartNodePanel data={selectedNode.data} updateData={(d) => updateNodeData(selectedNodeId, d)} />}
              {selectedNode.type === 'agent' && <AgentNodePanel data={selectedNode.data} updateData={(d) => updateNodeData(selectedNodeId, d)} availableVars={getAvailableVariables()} connectedKnowledge={getConnectedKnowledge(selectedNodeId)} mcpTools={mcpTools} onOpenSkillPanel={() => openSkillPanel(selectedNodeId)} />}
              {selectedNode.type === 'knowledge' && <KnowledgeNodePanel data={selectedNode.data} updateData={(d) => updateNodeData(selectedNodeId, d)} />}
              {selectedNode.type === 'router' && <RouterNodePanel data={selectedNode.data} updateData={(d) => updateNodeData(selectedNodeId, d)} availableVars={getAvailableVariables()} />}
              {selectedNode.type === 'end' && <EndNodePanel data={selectedNode.data} updateData={(d) => updateNodeData(selectedNodeId, d)} />}
            </div>
          </>
        )}
      </div>
      
      {/* Run Modal */}
      {isRunModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 w-full max-w-md rounded-xl shadow-2xl overflow-hidden animate-in zoom-in-95">
            <div className="p-5 border-b border-zinc-800 flex justify-between items-center bg-zinc-800">
              <h3 className="font-bold flex items-center gap-2 text-white">
                <PlayCircle className="w-5 h-5 text-emerald-500" /> Start Execution
              </h3>
              <button onClick={() => setIsRunModalOpen(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6">{renderRunModalContent()}</div>
            <div className="p-5 border-t border-zinc-800 flex justify-end gap-3 bg-zinc-800">
              <button onClick={() => setIsRunModalOpen(false)} className="px-4 py-2 text-sm text-zinc-400 hover:text-white">Cancel</button>
              <button onClick={handleStartExecution} className="px-4 py-2 bg-emerald-500 text-black rounded-lg text-sm font-bold flex items-center gap-2">
                <PlayCircle className="w-4 h-4" /> Run
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Save Modal */}
      {isSaveModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 w-full max-w-md rounded-xl shadow-2xl overflow-hidden animate-in zoom-in-95">
            <div className="p-5 border-b border-zinc-800 flex justify-between items-center bg-zinc-800">
              <h3 className="font-bold flex items-center gap-2 text-white">
                <Save className="w-5 h-5 text-emerald-400" /> Save Crew
              </h3>
              <button onClick={() => setIsSaveModalOpen(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="text-xs font-bold uppercase text-zinc-400 block mb-2">Crew Name</label>
                <input
                  type="text"
                  value={crewNameInput}
                  onChange={(e) => setCrewNameInput(e.target.value)}
                  placeholder="Enter Crew name"
                  className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-emerald-500 text-white"
                />
              </div>
              <div className="text-xs text-zinc-500">Your configuration will be saved to your Crew list.</div>
            </div>
            <div className="p-5 border-t border-zinc-800 flex justify-end gap-3 bg-zinc-800">
              <button onClick={() => setIsSaveModalOpen(false)} className="px-4 py-2 text-sm text-zinc-400 hover:text-white">Cancel</button>
              <button
                onClick={handleSave}
                disabled={isSaving || isLoading || !(crewNameInput || nodes.find(n => n.type === 'start')?.data.name)}
                className="px-4 py-2 bg-emerald-500 text-black rounded-lg text-sm font-bold flex items-center gap-2 disabled:opacity-50"
              >
                {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Confirm Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sliding Skill Panel - Full Canvas Overlay */}
      {isSkillPanelOpen && skillPanelNodeId && (
        <div className="fixed inset-0 z-[100] animate-in fade-in duration-200">
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setIsSkillPanelOpen(false)} />

          {/* Sliding Panel from Right */}
          <div className="absolute right-0 top-0 bottom-0 w-[1080px] bg-[var(--bg-panel)] border-l border-[var(--border-color)] shadow-2xl animate-in slide-in-from-right duration-300 flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-[var(--border-color)] bg-[var(--bg-card)]">
              <div className="flex items-center gap-4">
                <div className="p-2 bg-orange-900/30 rounded-lg">
                  <Sparkles className="w-5 h-5 text-orange-400" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white">
                    Skill Equipment
                  </h2>
                  <p className="text-xs text-[var(--text-secondary)]">
                    Agent: <span className="text-blue-400 font-medium">{nodes.find(n => n.id === skillPanelNodeId)?.data.role || 'Unnamed'}</span>
                    <span className="mx-2">·</span>
                    <span className="text-orange-400">{getNodeSkillKeys(skillPanelNodeId).length} selected</span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsSkillPanelOpen(false)}
                className="p-2 text-[var(--text-secondary)] hover:text-white hover:bg-zinc-800 rounded-lg transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Skill Selector - Full Height */}
            <div className="flex-1 overflow-hidden bg-[var(--bg-app)]">
              <SkillSelector
                selectedSkillKeys={getNodeSkillKeys(skillPanelNodeId)}
                onChange={(keys: string[]) => {
                  if (skillPanelNodeId) {
                    updateNodeSkillKeys(skillPanelNodeId, keys);
                  }
                }}
              />
            </div>

            {/* Footer with Legend */}
            <div className="flex items-center justify-between p-4 border-t border-[var(--border-color)] bg-[var(--bg-card)]">
              <div className="flex items-center gap-4 text-xs text-[var(--text-secondary)]">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
                  Capabilities
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-500"></span>
                  Presets
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-green-500"></span>
                  Strategies
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-orange-500"></span>
                  Skillsets
                </span>
              </div>
              <button
                onClick={() => setIsSkillPanelOpen(false)}
                className="px-6 py-2 bg-[var(--accent-blue)] hover:bg-blue-500 text-white font-medium rounded-lg transition-all"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
