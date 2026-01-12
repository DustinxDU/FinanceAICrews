'use client';

import React, { useState, useMemo, useEffect, useRef } from 'react';
import { RunEvent, JobStatus } from '@/lib/types';
import { BaseCard } from './cards/BaseCard';
import {
  getCurrentStage,
  filterEventsForDisplay,
  mapEventToCard
} from './eventMapper';
import { deriveAgentStates } from './agentState';
import { AgentsRail } from './AgentsRail';
import { ProgressHeader } from './ProgressHeader';
import { FinalReportCard } from './cards/FinalReportCard';
import { EChartsProvider } from './charts/EChartsProvider';
import { cn } from '@/lib/utils';
import { ChevronDown } from 'lucide-react';

// Initialize chart components - this triggers registerChartComponent() calls
import './core/initChartComponents';

interface ExecutionStreamPanelProps {
  job: JobStatus | null;
  className?: string;
  onRegenerate?: () => void;
}

export const ExecutionStreamPanel = ({
  job,
  className = '',
  onRegenerate
}: ExecutionStreamPanelProps) => {
  const events = job?.events || [];
  const isRunning = job?.status === 'running';
  const isCompleted = job?.status === 'completed';

  // === View State ===
  const [viewMode, setViewMode] = useState<'clean' | 'full'>('clean');
  const [selectedAgentName, setSelectedAgentName] = useState<string | null>(null);
  const [followActive, setFollowActive] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // === Derived State ===
  const stage = useMemo(() => getCurrentStage(events), [events]);

  const agentStates = useMemo(
    () => deriveAgentStates(events),
    [events]
  );

  // === Follow Active Logic ===
  useEffect(() => {
    if (followActive && agentStates.activeAgentName) {
      setSelectedAgentName(agentStates.activeAgentName);
    }
  }, [agentStates.activeAgentName, followActive]);

  // === Filtered Events ===
  const displayedEvents = useMemo(() => {
    // DEBUG: Log filtering
    if (process.env.NODE_ENV === 'development') {
      console.log('[ExecutionStreamPanel] viewMode:', viewMode);
      console.log('[ExecutionStreamPanel] selectedAgentName:', selectedAgentName);
      console.log('[ExecutionStreamPanel] total events:', events.length);
      console.log('[ExecutionStreamPanel] events sample:', events.slice(0, 3));
    }

    if (viewMode === 'full') {
      return events; // 完整视图
    }

    // Clean 模式: 只显示工具相关事件 + 选中的 agent
    // 包含 task_state 以便显示失败/完成状态
    const eventTypes = ['tool_call', 'tool_result', 'task_output', 'task_state'];
    const filtered = filterEventsForDisplay(events, {
      hidePhaseEvents: true,
      selectedAgentName: selectedAgentName,
      eventTypes
    });

    // DEBUG: Log filtered results
    if (process.env.NODE_ENV === 'development') {
      console.log('[ExecutionStreamPanel] filtered events:', filtered.length);
    }

    return filtered;
  }, [events, viewMode, selectedAgentName]);

  // === Auto-scroll ===
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [displayedEvents.length, autoScroll, viewMode, selectedAgentName]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    if (!isAtBottom && autoScroll) {
      setAutoScroll(false);
    } else if (isAtBottom && !autoScroll) {
      setAutoScroll(true);
    }
  };

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      setAutoScroll(true);
    }
  };

  if (!job) {
    return (
      <div className={cn("h-full flex flex-col items-center justify-center text-gray-500 bg-gray-950 rounded-lg border border-gray-800", className)}>
        <p className="text-lg">Ready to execute</p>
      </div>
    );
  }

  // === Render ===
  return (
    <EChartsProvider>
      <div className={cn("h-full flex flex-col bg-gray-950 rounded-lg border border-gray-800 overflow-hidden", className)}>
        {/* Header with Stage + Toggle */}
        <ProgressHeader
          stage={stage}
          isRunning={isRunning}
          jobStatus={job?.status}
          viewMode={viewMode}
          onToggleView={() => setViewMode(m => m === 'clean' ? 'full' : 'clean')}
          agentCount={agentStates.agents.length}
        />

        {/* Body */}
        <div className="flex-1 flex overflow-hidden relative">
          {/* Left: Agents Rail (Clean mode only) */}
          {viewMode === 'clean' && agentStates.agents.length > 0 && (
            <AgentsRail
              agents={agentStates.agents}
              selectedAgentName={selectedAgentName}
              activeAgentName={agentStates.activeAgentName}
              followActive={followActive}
              onSelect={(name) => {
                setSelectedAgentName(name);
                setFollowActive(false); // 用户手动选择，停止跟随
              }}
              onToggleFollow={() => setFollowActive(!followActive)}
            />
          )}

          {/* Right: Event Feed */}
          <div 
            ref={scrollRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto p-4 space-y-3"
          >
            {displayedEvents.length === 0 ? (
              <div className="text-center text-gray-500 py-12">
                {viewMode === 'clean'
                  ? selectedAgentName
                    ? `No events for ${selectedAgentName}`
                    : 'Select an agent to view events'
                  : 'No events'
                }
              </div>
            ) : (
              displayedEvents.map((event, idx) => {
                const card = mapEventToCard(event, idx);
                if (!card) return null;

                const CardComponent = card.component;
                return (
                  <CardComponent
                    key={event.event_id || idx}
                    {...card.props}
                  />
                );
              })
            )}

            {/* Final Report */}
            {isCompleted && job.result && (
              <div id="final-report" className="mt-6">
                <FinalReportCard
                  content={job.result}
                  summary={job.summary}
                  ticker={job.ticker}
                  crewName={job.crew_name}
                />
              </div>
            )}

            {/* Error state */}
            {job.status === 'failed' && job.error && (
               <div className="border-2 border-red-500 bg-red-900/30 p-4 rounded-lg mt-4">
                 <h4 className="text-red-400 font-semibold mb-2">Execution Failed</h4>
                 <p className="text-red-300 text-sm whitespace-pre-wrap">{job.error}</p>
               </div>
             )}
          </div>

          {/* Scroll to bottom button */}
          {!autoScroll && (
            <button
              onClick={scrollToBottom}
              className="absolute bottom-4 right-4 p-2 bg-gray-800 hover:bg-gray-700 rounded-full shadow-lg transition-colors z-10"
            >
              <ChevronDown size={20} className="text-gray-300" />
            </button>
          )}
        </div>
      </div>
    </EChartsProvider>
  );
};
