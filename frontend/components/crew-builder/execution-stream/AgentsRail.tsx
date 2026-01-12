'use client';

import React from 'react';
import { AgentState } from './agentState';
import { cn } from '@/lib/utils';
import { useTranslations } from 'next-intl';

interface AgentsRailProps {
  agents: AgentState[];
  selectedAgentName: string | null;
  activeAgentName: string | null;
  followActive: boolean;
  onSelect: (agentName: string) => void;
  onToggleFollow: () => void;
}

const statusColors: Record<string, string> = {
  idle: 'bg-gray-500',
  running: 'bg-green-500 animate-pulse',
  done: 'bg-blue-500',
  failed: 'bg-red-500'
};

const statusLabels: Record<string, string> = {
  idle: 'Waiting',
  running: 'Running',
  done: 'Completed',
  failed: 'Failed'
};

export const AgentsRail = ({
  agents,
  selectedAgentName,
  activeAgentName,
  followActive,
  onSelect,
  onToggleFollow
}: AgentsRailProps) => {
  const t = useTranslations('library');
  return (
    <div className="w-64 bg-gray-900/80 border-r border-cyan-500/20 flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-cyan-500/20">
        <div className="flex items-center justify-between">
          <h3 className="text-cyan-400 text-sm font-semibold uppercase tracking-wider">
            {t('agents')}
          </h3>
          <button
            onClick={onToggleFollow}
            className={cn(
              'text-xs px-2 py-1 rounded transition-colors',
              followActive
                ? 'bg-cyan-500/20 text-cyan-400'
                : 'bg-gray-800 text-gray-500'
            )}
          >
            {followActive ? `👁 ${t('follow')}` : `📌 ${t('pin')}`}
          </button>
        </div>
      </div>

      {/* Agent List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {agents.map((agent) => (
          <button
            key={agent.agentName}
            onClick={() => onSelect(agent.agentName)}
            className={cn(
              'w-full text-left p-3 rounded-lg transition-all border',
              selectedAgentName === agent.agentName
                ? 'bg-cyan-500/20 border-cyan-500/40'
                : agent.agentName === activeAgentName && followActive
                  ? 'bg-green-500/10 border-green-500/30'
                  : 'bg-gray-800/50 border-transparent hover:bg-gray-800 hover:border-gray-700'
            )}
          >
            {/* Status Indicator + Name */}
            <div className="flex items-center gap-2 mb-1">
              <div className={cn(
                'w-2 h-2 rounded-full',
                statusColors[agent.status]
              )} role="status" />
              <span className={cn(
                'text-sm font-medium',
                selectedAgentName === agent.agentName
                  ? 'text-cyan-300'
                  : 'text-gray-300'
              )}>
                {agent.agentName}
              </span>
              {agent.agentName === activeAgentName && followActive && (
                <span className="text-[10px] text-green-400">●</span>
              )}
            </div>

            {/* Status Label */}
            <div className="text-xs text-gray-500 mb-1">
              {statusLabels[agent.status]}
            </div>

            {/* Current Action */}
            {agent.currentActionLabel && (
              <div className="text-xs text-gray-400 truncate">
                {agent.currentActionLabel}
              </div>
            )}

            {/* Last Tool (if available) */}
            {agent.lastToolName && (
              <div className="text-[10px] text-gray-600 mt-1 flex items-center gap-1">
                <span>🔧</span>
                <span className="truncate">{agent.lastToolName}</span>
                {agent.lastToolDurationMs && (
                  <span className="ml-auto">{(agent.lastToolDurationMs / 1000).toFixed(1)}s</span>
                )}
              </div>
            )}
          </button>
        ))}

        {agents.length === 0 && (
          <div className="text-center py-8 text-gray-500 text-sm">
            {t('noAgentsActive')}
          </div>
        )}
      </div>
    </div>
  );
};
