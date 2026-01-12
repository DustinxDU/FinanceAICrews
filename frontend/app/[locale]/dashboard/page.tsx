"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { Link } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import { AppLayout } from "@/components/layout";
import { withAuth } from "@/contexts/AuthContext";
import apiClient from "@/lib/api";
import type { JobStatus, ChatMessage, CrewDefinition, RunEvent, RunSummary } from "@/lib/types";
import { ToastProvider, useToast } from "@/components/crew-builder/Toast";
import { SchemaForm, InputSchema } from "@/components/SchemaForm";
import {
  TrendingUp, Globe, Bitcoin, PlayCircle, Loader2, Check, History,
  Terminal, ChevronDown, Sparkles, User, Bot, SendHorizontal, AlertTriangle, XCircle,
} from "lucide-react";
import { ExecutionStreamPanel } from "@/components/crew-builder/execution-stream";
import { AssetPicker } from "@/components/AssetPicker";
import { TimeframePicker, TimeframeValue } from "@/components/TimeframePicker";

// Fallback crews when DB is empty
const CREW_TYPES_FALLBACK: CrewOption[] = [];

export interface LogItem {
  id: string | number;
  agent: string;
  status: string;
  message: string;
  timestamp: string;
  type?: string;
  detail?: string;
  payload?: any;
  severity?: string;
}

interface CrewOption {
  id: number;
  name: string;
  description: string;
  agents: number;
  icon: React.ElementType;
}

function Launcher({ onRun, isRunning }: { onRun: (payload: { ticker: string; crew_id: number; crew_name: string; date?: string; variables?: Record<string, any> }) => void; isRunning: boolean }) {
  const t = useTranslations('dashboard');
  const [crewOptions, setCrewOptions] = useState<CrewOption[]>(CREW_TYPES_FALLBACK);
  const [selectedCrew, setSelectedCrew] = useState<CrewOption | null>(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [ticker, setTicker] = useState("NVDA");
  const [crewDetail, setCrewDetail] = useState<CrewDefinition | null>(null);
  const [timeframe, setTimeframe] = useState<TimeframeValue>({ type: 'preset', value: '1mo' });
  const [isLoadingCrews, setIsLoadingCrews] = useState(true);
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  // Load crews from v2 crew-builder API (database)
  useEffect(() => {
    const loadCrews = async () => {
      setIsLoadingCrews(true);
      try {
        const crews = await apiClient.listCrewDefinitions(true); // include templates
        if (crews?.length) {
          const mapped: CrewOption[] = crews.map((c: CrewDefinition) => ({
            id: c.id,
            name: c.name,
            description: c.description || "",
            agents: c.structure?.length || 0,
            icon: c.name.toLowerCase().includes("buffett") ? Globe 
                : c.name.toLowerCase().includes("soros") ? Bitcoin 
                : c.name.toLowerCase().includes("macro") ? Globe
                : TrendingUp,
          }));
          setCrewOptions(mapped);
          setSelectedCrew(mapped[0]);
        }
      } catch (err) {
        console.error("Failed to load crews:", err);
      } finally {
        setIsLoadingCrews(false);
      }
    };
    loadCrews();
  }, []);

  // Load crew detail from v2 API
  useEffect(() => {
    if (!selectedCrew) return;
    const loadDetail = async () => {
      setIsLoadingDetail(true);
      try {
        const detail = await apiClient.getCrewDefinition(selectedCrew.id);
        setCrewDetail(detail);
        // Reset form values when crew changes, initialize with defaults from schema
        if (detail?.input_schema?.properties) {
          const defaults: Record<string, any> = {};
          Object.entries(detail.input_schema.properties).forEach(([key, prop]: [string, any]) => {
            if (prop.default !== undefined) {
              defaults[key] = prop.default;
            }
          });
          setFormValues(defaults);
        } else {
          setFormValues({});
        }
      } catch {
        setCrewDetail(null);
        setFormValues({});
      } finally {
        setIsLoadingDetail(false);
      }
    };
    loadDetail();
  }, [selectedCrew]);


  // Show loading state
  if (isLoadingCrews) {
    return (
      <div className="p-6 border-b border-[var(--border-color)] bg-[var(--bg-panel)] shrink-0 z-20 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-[var(--accent-blue)]" />
        <span className="ml-2 text-sm text-[var(--text-secondary)]">{t('loadingCrews')}</span>
      </div>
    );
  }

  // Show empty state if no crews
  if (!selectedCrew) {
    return (
      <div className="p-6 border-b border-[var(--border-color)] bg-[var(--bg-panel)] shrink-0 z-20">
        <p className="text-sm text-[var(--text-secondary)]">No crews available. Please create one in Crew Builder.</p>
      </div>
    );
  }

  const CrewIcon = selectedCrew.icon;

  return (
    <div className="p-6 border-b border-[var(--border-color)] bg-[var(--bg-panel)] shrink-0 z-20">
      <h2 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-4">Mission Configuration</h2>
      <div className="mb-4 space-y-2 relative">
        <label className="text-sm font-medium">{t('selectCrew')}</label>
        <div className="relative">
          <button onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="w-full flex items-center justify-between bg-[var(--bg-card)] border border-[var(--border-color)] p-3 rounded-lg hover:border-[var(--accent-blue)] transition-colors">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded bg-blue-500/10 text-blue-400"><CrewIcon className="w-4 h-4" /></div>
              <div className="text-left">
                <div className="font-bold text-sm">{selectedCrew.name}</div>
                <div className="text-xs text-[var(--text-secondary)]">{selectedCrew.agents} Agents</div>
              </div>
            </div>
            <ChevronDown className="w-4 h-4 text-[var(--text-secondary)]" />
          </button>
          {isDropdownOpen && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-xl z-50 overflow-hidden max-h-64 overflow-y-auto">
              {crewOptions.map(crew => {
                const ItemIcon = crew.icon;
                return (
                  <button key={crew.id} onClick={() => { setSelectedCrew(crew); setIsDropdownOpen(false); }}
                    className={`w-full text-left p-3 hover:bg-[var(--bg-panel)] flex items-center gap-3 transition-colors ${selectedCrew.id === crew.id ? "bg-[var(--bg-panel)]" : ""}`}>
                    <div className={`p-2 rounded ${selectedCrew.id === crew.id ? "bg-blue-500/20 text-blue-400" : "bg-zinc-800 text-[var(--text-secondary)]"}`}><ItemIcon className="w-4 h-4" /></div>
                    <div className="flex-1">
                      <div className="text-sm font-bold">{crew.name}</div>
                      <div className="text-xs text-[var(--text-secondary)]">{crew.agents} Agents</div>
                    </div>
                    {selectedCrew.id === crew.id && <Check className="w-4 h-4 text-[var(--accent-green)]" />}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Crew description */}
      {selectedCrew.description && (
        <p className="text-xs text-[var(--text-secondary)] mb-4 line-clamp-2">{selectedCrew.description}</p>
      )}

      {/* Dynamic Input Form based on crew's input_schema */}
      <div className="mb-6">
        {isLoadingDetail ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-4 h-4 animate-spin text-[var(--text-secondary)]" />
            <span className="ml-2 text-xs text-[var(--text-secondary)]">{t('loadingInputSchema')}</span>
          </div>
        ) : crewDetail?.input_schema?.properties && Object.keys(crewDetail.input_schema.properties).length > 0 ? (
          <SchemaForm
            schema={crewDetail.input_schema as InputSchema}
            values={formValues}
            onChange={setFormValues}
            disabled={isRunning}
          />
        ) : (
          /* Fallback: Default ticker + timeframe inputs when no schema defined */
          <>
            <div className="mb-4">
              <label className="text-xs text-[var(--text-secondary)] mb-1 block">{t('targetAsset')}</label>
              <AssetPicker
                value={ticker}
                onSelect={(val) => setTicker(val)}
                placeholder="Search symbol (e.g. NVDA)"
              />
            </div>
            <div>
              <label className="text-xs text-[var(--text-secondary)] mb-2 block">{t('analysisTimeframe')}</label>
              <TimeframePicker
                value={timeframe}
                onChange={setTimeframe}
              />
            </div>
          </>
        )}
      </div>

      <button onClick={() => {
        if (!selectedCrew) return;

        // Determine variables based on whether we have a schema or using fallback
        const hasSchema = crewDetail?.input_schema?.properties && Object.keys(crewDetail.input_schema.properties).length > 0;

        let variables: Record<string, any>;
        let displayTicker: string;

        if (hasSchema) {
          // Use form values from SchemaForm
          variables = { ...formValues };
          // Find the primary ticker field for display purposes
          const schema = crewDetail!.input_schema!;
          const props = schema.properties as Record<string, any>;
          const required = (schema.required as string[]) || [];
          const primaryField = required.find(key => {
            const prop = props[key];
            return prop?.type === 'string' && !prop?.enum && !prop?.readOnly;
          }) || Object.keys(props).find(key => {
            const prop = props[key];
            return prop?.type === 'string' && !prop?.enum && !prop?.readOnly;
          });
          displayTicker = primaryField ? (formValues[primaryField] || 'Unknown') : 'Unknown';
        } else {
          // Fallback: use ticker and timeframe state
          if (!ticker.trim()) return;
          variables = {
            ticker: ticker.trim(),
            timeframe: timeframe.value,
            start_date: timeframe.start,
            end_date: timeframe.end,
            // Keep date for backward compatibility (defaults to today)
            date: new Date().toISOString().split('T')[0],
          };
          displayTicker = ticker.trim();
        }

        onRun({
          ticker: displayTicker,
          crew_id: selectedCrew.id,
          crew_name: selectedCrew.name,
          date: variables.date,
          variables: variables,
        });
      }} disabled={isRunning || !selectedCrew || (!(crewDetail?.input_schema?.properties && Object.keys(crewDetail.input_schema.properties).length > 0) && !ticker.trim())}
        className={`w-full py-4 rounded-xl font-bold flex items-center justify-center gap-2 transition-all ${isRunning ? "bg-[var(--bg-card)] text-[var(--text-secondary)] cursor-wait" : "bg-[var(--accent-green)] text-black hover:shadow-[0_0_20px_rgba(16,185,129,0.4)]"}`}>
        {isRunning ? <><Loader2 className="w-4 h-4 animate-spin" /><span>Mission in Progress...</span></> : <><PlayCircle className="w-5 h-5" /><span>Deploy Agents</span></>}
      </button>
    </div>
  );
}

function RunSummaryCard({ summary }: { summary: any }) {
  const t = useTranslations('dashboard');
  if (!summary) return null;
  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4 mb-6 shadow-sm">
      <div className="flex items-center gap-2 mb-3 text-[var(--accent-blue)] font-bold text-xs uppercase tracking-widest">
        <History className="w-3.5 h-3.5" />
        {t('executionSummary')}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <div className="text-[10px] text-[var(--text-secondary)] uppercase">{t('duration')}</div>
          <div className="text-sm font-mono">{(summary.total_duration_ms / 1000).toFixed(2)}s</div>
        </div>
        <div className="space-y-1">
          <div className="text-[10px] text-[var(--text-secondary)] uppercase">{t('totalTokens')}</div>
          <div className="text-sm font-mono">{summary.total_tokens.toLocaleString()}</div>
        </div>
        <div className="space-y-1">
          <div className="text-[10px] text-[var(--text-secondary)] uppercase">{t('toolsUsed')}</div>
          <div className="text-sm font-mono">{summary.tool_calls_count} calls</div>
        </div>
        <div className="space-y-1">
          <div className="text-[10px] text-[var(--text-secondary)] uppercase">{t('status')}</div>
          <div className={`text-sm font-bold capitalize ${summary.status === 'completed' ? 'text-[var(--accent-green)]' : 'text-red-400'}`}>
            {summary.status}
          </div>
        </div>
      </div>
    </div>
  );
}

export function LogItemComponent({ log }: { log: LogItem }) {
  const [expanded, setExpanded] = useState(false);
  const agentColors: Record<string, string> = { 
    Orchestrator: "text-purple-400", 
    Researcher: "text-blue-400", 
    Analyst: "text-yellow-400", 
    System: "text-zinc-400",
    Preflight: "text-cyan-400"
  };

  const isTool = log.type === "tool_call" || log.type === "tool_result";
  const isLLM = log.type === "llm_call";
  const isTask = log.type === "task_state";

  return (
    <div className="border-l-2 border-[var(--border-color)] ml-3 pl-4 pb-6 relative last:pb-0">
      <div className={`absolute -left-[9px] top-0 w-4 h-4 rounded-full border-2 border-[var(--bg-panel)] flex items-center justify-center ${
        log.status === "completed" || log.status === "success" ? "bg-green-500" : 
        log.status === "working" || log.status === "pending" ? "bg-yellow-500 animate-pulse" : 
        log.status === "failed" || log.severity === "error" ? "bg-red-500" : "bg-zinc-700"
      }`}>
        {(log.status === "completed" || log.status === "success") && <Check className="w-2 h-2 text-black" />}
        {(log.status === "failed" || log.severity === "error") && <XCircle className="w-2 h-2 text-white" />}
      </div>
      <div className="group cursor-pointer" onClick={() => (log.detail || log.payload) && setExpanded(!expanded)}>
        <div className="flex justify-between items-start mb-1">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-bold uppercase tracking-wider ${agentColors[log.agent] || "text-[var(--text-secondary)]"}`}>{log.agent}</span>
            {(log.detail || log.payload) && (
              <span className="text-[10px] bg-white/5 px-1.5 py-0.5 rounded text-zinc-500 group-hover:text-zinc-300 transition-colors">
                {expanded ? "Collapse" : "Details"}
              </span>
            )}
          </div>
          <span className="text-[10px] text-[var(--text-secondary)] font-mono">{log.timestamp}</span>
        </div>
        
        <div className="text-sm leading-snug">
          {isTool ? (
            <div className={`flex items-center gap-2 ${log.status === 'failed' ? 'text-red-400' : 'text-blue-300'}`}>
              <Terminal className="w-3 h-3" />
              <span>{log.message}</span>
            </div>
          ) : isLLM ? (
            <div className="flex items-center gap-2 text-purple-300">
              <Sparkles className="w-3 h-3" />
              <span>{log.message}</span>
            </div>
          ) : isTask ? (
            <div className="flex items-center gap-2 text-emerald-300 font-medium">
              <Bot className="w-3 h-3" />
              <span>{log.message}</span>
            </div>
          ) : (
            <p className={log.severity === 'error' ? 'text-red-400' : ''}>{log.message}</p>
          )}
        </div>

        {(log.detail || log.payload) && expanded && (
          <div className="mt-2 bg-black/40 rounded-lg p-3 text-[11px] font-mono text-zinc-400 border border-white/5 overflow-x-auto max-w-full">
            {log.detail && <pre className="whitespace-pre-wrap break-all mb-2">{log.detail}</pre>}

            {/* Structured Preflight Recovery UI */}
            {log.payload && log.payload.unauthorized_knowledge && Array.isArray(log.payload.unauthorized_knowledge) ? (
              <div className="space-y-3">
                <div className="text-red-400 font-bold mb-2">Missing Knowledge Packs:</div>
                {log.payload.unauthorized_knowledge.map((k: any, i: number) => (
                  <div key={i} className="flex items-center justify-between bg-zinc-900 p-2 rounded border border-zinc-700">
                    <div>
                      <span className="text-white font-bold">{k.display_name}</span>
                      <span className="text-zinc-500 ml-2 text-[10px] uppercase">{k.tier}</span>
                    </div>
                    <Link href={`/tools?category=knowledge&source_key=${k.source_key}`} target="_blank">
                      <button className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[10px] font-bold">
                        {k.tier === 'premium' ? `Buy $${k.price}` : 'Add Pack'}
                      </button>
                    </Link>
                  </div>
                ))}
                <div className="text-zinc-500 italic mt-2">
                  Click 'Add/Buy' above, complete the process, then try running again.
                </div>
              </div>
            ) : (
              log.payload && <pre className="whitespace-pre-wrap break-all text-blue-200/70">{JSON.stringify(log.payload, null, 2)}</pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function LiveStream({ logs, status, summary }: { logs: LogItem[]; status: string; summary: RunSummary | null | undefined }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => { if (status === "running") endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs, status]);

  // Group logs by agent
  const groupedLogs = logs.reduce((acc, log) => {
    const agent = log.agent || "System";
    if (!acc[agent]) acc[agent] = [];
    acc[agent].push(log);
    return acc;
  }, {} as Record<string, LogItem[]>);

  const agents = Object.keys(groupedLogs);

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-[var(--bg-panel)] custom-scrollbar">
      <h2 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-6 flex items-center justify-between">
        <span className="flex items-center gap-2">
          {status === "running" ? <><span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" /> Live Execution Log</> : <><History className="w-4 h-4" /> Mission Log</>}
        </span>
        {status === "running" && <Loader2 className="w-3 h-3 animate-spin" />}
      </h2>
      
      {summary && <RunSummaryCard summary={summary} />}

      <div className="relative space-y-8">
        {logs.length === 0 ? (
          <div className="text-center text-[var(--text-secondary)] py-10 opacity-50">
            <Terminal className="w-10 h-10 mb-2 mx-auto" />
            <p className="text-xs">Ready to deploy agents...</p>
          </div>
        ) : (
          agents.map((agent) => (
            <div key={agent} className="space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="h-[1px] flex-1 bg-[var(--border-color)]" />
                <span className="text-[10px] font-black uppercase tracking-tighter text-[var(--text-secondary)] px-2 bg-[var(--bg-panel)]">{agent}</span>
                <div className="h-[1px] flex-1 bg-[var(--border-color)]" />
              </div>
              <div className="space-y-1">
                {groupedLogs[agent].map((log) => (
                  <LogItemComponent key={log.id} log={log} />
                ))}
              </div>
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}

function CopilotChat({ active, jobId }: { active: boolean; jobId: string | null }) {
  const t = useTranslations('dashboard');
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || !jobId) return;
    setHistory((prev) => [...prev, { role: "user", content: input }]);
    setInput("");
    setIsLoading(true);
    try {
      const response = await apiClient.sendChatMessage(jobId, input);
      setHistory(response.chat_history);
    } catch { setHistory((prev) => [...prev, { role: "assistant", content: "Sorry, failed to send." }]); }
    finally { setIsLoading(false); }
  };

  return (
    <div className={`border-t border-[var(--border-color)] bg-[var(--bg-panel)] transition-all duration-300 flex flex-col ${active ? "h-64" : "h-14 overflow-hidden"}`}>
      <div className="px-4 py-3 border-b border-[var(--border-color)] flex justify-between items-center bg-[var(--bg-card)]">
        <div className="flex items-center gap-2 font-bold text-sm"><Sparkles className="w-4 h-4 text-[var(--accent-blue)]" />Copilot</div>
        {!active && <div className="text-xs text-[var(--text-secondary)]">{t('waitingForCompletion')}</div>}
        {active && <div className="text-xs bg-green-900/30 text-green-400 px-2 py-0.5 rounded">Context Aware</div>}
      </div>
      {active && (
        <>
          <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
            {history.length === 0 && <div className="text-xs text-[var(--text-secondary)] text-center mt-4">Ask follow-up questions about the report.</div>}
            {history.map((msg, i) => (
              <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${msg.role === "user" ? "bg-[var(--text-primary)] text-black" : "bg-[var(--accent-blue)] text-white"}`}>
                  {msg.role === "user" ? <User className="w-3 h-3" /> : <Bot className="w-3 h-3" />}
                </div>
                <div className={`p-2 rounded-lg text-xs max-w-[85%] ${msg.role === "user" ? "bg-[var(--bg-card)]" : "bg-blue-900/20 text-blue-100"}`}>{msg.content}</div>
              </div>
            ))}
            {isLoading && <div className="flex gap-3"><div className="w-6 h-6 rounded-full bg-[var(--accent-blue)] flex items-center justify-center"><Loader2 className="w-3 h-3 animate-spin text-white" /></div></div>}
          </div>
          <div className="p-3 border-t border-[var(--border-color)]">
            <div className="relative">
              <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSend()}
                type="text" placeholder="E.g., What are the risks?" className="w-full bg-[var(--bg-app)] border border-[var(--border-color)] rounded-lg pl-3 pr-8 py-2 text-sm focus:border-[var(--accent-blue)] outline-none" />
              <button onClick={handleSend} className="absolute right-2 top-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"><SendHorizontal className="w-4 h-4" /></button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function ErrorPanel({ error, hints }: { error: string; hints?: string[] }) {
  const t = useTranslations('dashboard');
  return (
    <div className="bg-red-900/20 border border-red-500/30 rounded-2xl p-8 max-w-2xl mx-auto mt-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center gap-4 mb-6">
        <div className="p-3 bg-red-500/20 rounded-full text-red-400">
          <XCircle className="w-8 h-8" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-red-200">{t('missionFailed')}</h2>
          <p className="text-red-400/80 text-sm">The execution was interrupted by an error.</p>
        </div>
      </div>
      
      <div className="bg-black/40 rounded-xl p-4 font-mono text-sm text-red-300 border border-red-500/10 mb-6">
        {error}
      </div>

      {hints && hints.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider flex items-center gap-2">
            <Sparkles className="w-3 h-3 text-yellow-400" />
            Suggested Actions
          </h3>
          <ul className="space-y-2">
            {hints.map((hint, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-zinc-300 bg-white/5 p-2 rounded-lg border border-white/5">
                <div className="mt-1 w-1 h-1 rounded-full bg-[var(--accent-blue)] shrink-0" />
                {hint}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Canvas({ status, job, rawEvents }: { status: string; job: JobStatus | null; rawEvents: RunEvent[] }) {
  // Merge rawEvents into job for ExecutionStreamPanel
  // This ensures real-time WebSocket events are displayed on the right panel
  const enrichedJob = job ? {
    ...job,
    events: rawEvents.length > 0 ? rawEvents : (job.events || [])
  } : null;

  return (
    <div className="flex-1 bg-[var(--bg-app)] overflow-hidden relative">
      <ExecutionStreamPanel job={enrichedJob} className="h-full" />
    </div>
  );
}

function WorkbenchInner() {
  const t = useTranslations('dashboard');
  const [status, setStatus] = useState<"idle" | "running" | "completed">("idle");
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [rawEvents, setRawEvents] = useState<RunEvent[]>([]); // Store original RunEvents for right panel
  const [currentJob, setCurrentJob] = useState<JobStatus | null>(null);
  const toast = useToast();
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const [lastEventId, setLastEventId] = useState<string | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // WebSocket connection for real-time logs
  const connectWebSocket = useCallback((jobId: string, resumeId: string | null = null) => {
    if (status !== "running") return;

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || `ws://${window.location.hostname}:8000`;
    const queryParams = resumeId ? `?last_event_id=${resumeId}` : "";
    const socket = new WebSocket(`${wsUrl}/api/v1/realtime/ws/analysis/${jobId}${queryParams}`);
    
    socket.onopen = () => {
      console.log("WebSocket connected for job logs", resumeId ? `(resuming from ${resumeId})` : "");
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.run_id && message.event_type) {
          const runEvent: RunEvent = message;
          setLastEventId(runEvent.event_id);
          
          // Store raw RunEvent for right panel (ExecutionStreamPanel)
          setRawEvents(prev => {
            if (prev.some(e => e.event_id === runEvent.event_id)) return prev;
            return [...prev, runEvent];
          });
          
          // Store formatted LogItem for left panel (LiveStream)
          setLogs(prev => {
            if (prev.some(l => l.id === runEvent.event_id)) return prev;
            
            const statusMap: Record<string, string> = {
              'activity': 'working',
              'tool_call': 'working',
              'tool_result': 'completed',
              'llm_call': 'working',
              'task_state': runEvent.payload?.status === 'failed' ? 'failed' : 'completed',
              'system': 'working'
            };

            return [...prev, {
              id: runEvent.event_id,
              agent: runEvent.agent_name || "System",
              status: statusMap[runEvent.event_type] || "working",
              message: runEvent.payload?.message || `${runEvent.event_type}: ${runEvent.payload?.tool_name || runEvent.payload?.model_name || ""}`,
              timestamp: new Date(runEvent.timestamp).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
              type: runEvent.event_type,
              detail: runEvent.payload?.thought || runEvent.payload?.error || undefined,
              payload: runEvent.payload,
              severity: runEvent.severity
            }];
          });
        }
      } catch (err) {
        console.error("Error parsing WS message:", err);
      }
    };

    socket.onclose = (e) => {
      console.log("WebSocket disconnected", e.reason);
      wsRef.current = null;
      // Auto-reconnect if mission still running
      if (status === "running") {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log("Attempting to reconnect WebSocket...");
          connectWebSocket(jobId, lastEventId);
        }, 3000);
      }
    };

    wsRef.current = socket;
  }, [status, lastEventId]);

  useEffect(() => {
    if (status === "running" && currentJob?.job_id && !wsRef.current) {
      connectWebSocket(currentJob.job_id);
    }
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, [status, currentJob?.job_id, connectWebSocket]);

  const pollJobStatus = useCallback(async (jobId: string) => {
    try {
      // Phase 3B: Use unified job status API
      const job = await apiClient.getJobStatus(jobId);
      setCurrentJob(job);
      
      // Phase 3C: Sync logs and rawEvents from structured events if available
      if (job.events && job.events.length > 0) {
        // Sync rawEvents for right panel
        setRawEvents(prev => {
          const newEvents = [...prev];
          let updated = false;
          job.events?.forEach(event => {
            if (!newEvents.some(e => e.event_id === event.event_id)) {
              newEvents.push(event);
              updated = true;
            }
          });
          return updated ? newEvents : prev;
        });

        // Sync logs for left panel
        setLogs(prev => {
          const newLogs = [...prev];
          let updated = false;
          
          job.events?.forEach(event => {
            if (!newLogs.some(l => l.id === event.event_id)) {
              const statusMap: Record<string, string> = {
                'activity': 'working',
                'tool_call': 'working',
                'tool_result': 'completed',
                'llm_call': 'working',
                'task_state': event.payload?.status === 'failed' ? 'failed' : 'completed',
                'system': 'working'
              };
              
              newLogs.push({
                id: event.event_id,
                agent: event.agent_name || "System",
                status: statusMap[event.event_type] || "working",
                message: event.payload?.message || `${event.event_type}: ${event.payload?.tool_name || event.payload?.model_name || ""}`,
                timestamp: new Date(event.timestamp).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
                type: event.event_type,
                detail: event.payload?.thought || event.payload?.error || undefined,
                payload: event.payload,
                severity: event.severity
              });
              updated = true;
            }
          });
          
          return updated ? newLogs : prev;
        });
      }
      
      // Fallback to legacy progress message if no structured events
      else if (job.progress_message) {
        setLogs((prev) => {
          if (prev.some((l) => l.message === job.progress_message)) return prev;
          return [...prev, { 
            id: Date.now(), 
            agent: "System", 
            status: job.status === "completed" ? "completed" : "working", 
            message: job.progress_message || "", 
            timestamp: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }) 
          }];
        });
      }

      // Stop polling and WS if job is finished
      if (job.status === "completed" || job.status === "failed") { 
        setStatus("completed"); 
        if (pollingRef.current) clearInterval(pollingRef.current);
        if (wsRef.current) wsRef.current.close();
      }
    } catch (error) { 
      console.error("Polling error:", error); 
      // If polling fails, add error log
      setLogs(prev => [...prev, {
        id: `err-${Date.now()}`,
        agent: "System", 
        status: "failed", 
        message: "Connection lost - retrying...",
        timestamp: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" })
      }]);
    }
  }, []);

  const handleRun = async (payload: { ticker: string; crew_id: number; crew_name: string; date?: string; variables?: Record<string, any> }) => {
    setStatus("running");
    setRawEvents([]); // Clear previous raw events for right panel
    setLogs([{ id: 1, agent: "Orchestrator", status: "completed", message: `Initializing mission: ${payload.ticker} Analysis`, timestamp: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }) }]);
    
    const variables = payload.variables || { ticker: payload.ticker, date: payload.date || new Date().toISOString().split('T')[0] };
    
    try {
      // Phase 3A: Run preflight check first
      setLogs(prev => [...prev, {
        id: prev.length + 1,
        agent: "Preflight",
        status: "working",
        message: "Running pre-execution validation...",
        timestamp: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" })
      }]);
      
      const preflightResult = await apiClient.runPreflightCheck(payload.crew_id, variables);
      
      if (!preflightResult.success) {
        setStatus("idle");
        const errorMessage = `Preflight failed: ${preflightResult.errors.join(', ')}`;
        toast(errorMessage, "error");

        setLogs(prev => [...prev, {
          id: prev.length + 1,
          agent: "Preflight",
          status: "failed",
          message: errorMessage,
          timestamp: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
          payload: preflightResult // Pass full result to render actions
        }]);
        return;
      }
      
      // Preflight passed
      setLogs(prev => [...prev, {
        id: prev.length + 1,
        agent: "Preflight",
        status: "completed",
        message: `Validation passed for crew '${preflightResult.crew_name}'`,
        timestamp: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" })
      }]);
      
      // Use v2 crew-builder run API with crew_id
      const response = await apiClient.startAnalysisV2({
        crew_id: payload.crew_id,
        variables: variables,
        skip_preflight: true // We already ran preflight
      });
      
      setCurrentJob({ job_id: response.job_id, status: "pending", progress: 0, ticker: payload.ticker, crew_name: payload.crew_name, created_at: new Date().toISOString(), progress_message: "" });
      pollingRef.current = setInterval(() => pollJobStatus(response.job_id), 1500);
      toast("Analysis started successfully", "success");
      
    } catch (error: any) { 
      console.error("Failed:", error); 
      setStatus("idle"); 
      
      // Enhanced error handling with toast notifications
      let errorMessage = "Failed to start analysis";
      if (error?.response?.status === 422) {
        errorMessage = "Validation failed: Please check your inputs";
      } else if (error?.response?.status === 403) {
        errorMessage = "Access denied: You don't have permission to run this crew";
      } else if (error?.response?.status === 404) {
        errorMessage = "Crew not found";
      } else if (error?.message) {
        errorMessage = `Error: ${error.message}`;
      }
      
      toast(errorMessage, "error");
      
      // Add error log entry
      setLogs(prev => [...prev, {
        id: prev.length + 1, 
        agent: "System", 
        status: "failed", 
        message: errorMessage,
        timestamp: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" })
      }]);
    }
  };

  useEffect(() => { return () => { if (pollingRef.current) clearInterval(pollingRef.current); }; }, []);

  return (
    <div className="h-[calc(100vh-3.5rem)] flex overflow-hidden">
      <div className="w-[400px] flex flex-col border-r border-[var(--border-color)] bg-[var(--bg-panel)] relative z-10 shadow-2xl">
        <Launcher onRun={handleRun} isRunning={status === "running"} />
        <LiveStream logs={logs} status={status} summary={currentJob?.summary} />
        <CopilotChat active={status === "completed"} jobId={currentJob?.job_id || null} />
      </div>
      <Canvas status={status} job={currentJob} rawEvents={rawEvents} />
    </div>
  );
}

function Workbench() {
  return (
    <ToastProvider>
      <WorkbenchInner />
    </ToastProvider>
  );
}

function WorkbenchPage() {
  return <AppLayout><Workbench /></AppLayout>;
}

export default withAuth(WorkbenchPage);
