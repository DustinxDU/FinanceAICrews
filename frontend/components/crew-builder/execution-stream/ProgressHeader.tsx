'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface ProgressHeaderProps {
  stage: string;
  isRunning?: boolean;
  jobStatus?: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  viewMode: 'clean' | 'full';
  onToggleView: () => void;
  agentCount?: number;
}

export const ProgressHeader = ({
  stage,
  isRunning = false,
  jobStatus,
  viewMode,
  onToggleView,
  agentCount = 0
}: ProgressHeaderProps) => {
  // Derive display status from jobStatus or isRunning (backward compat)
  const isPending = jobStatus === 'pending';
  const isFailed = jobStatus === 'failed';
  const isCancelled = jobStatus === 'cancelled';
  const isActive = jobStatus === 'running' || isRunning;
  // Only show completed if explicitly completed or not running and not in other states
  const isComplete = jobStatus === 'completed' || (!isRunning && !isFailed && !isCancelled && !isPending);

  // Status indicator color
  const indicatorColor = isFailed
    ? 'bg-red-500'
    : isCancelled
      ? 'bg-yellow-500'
      : isPending
        ? 'bg-blue-500'
        : isActive
          ? 'bg-green-500 animate-pulse'
          : 'bg-gray-500';

  // Status label
  const statusLabel = isFailed
    ? 'Failed'
    : isCancelled
      ? 'Cancelled'
      : isPending
        ? 'Queued'
        : isActive
          ? 'Running'
          : 'Completed';

  // Status label color
  const statusLabelColor = isFailed
    ? 'text-red-400'
    : isCancelled
      ? 'text-yellow-400'
      : isPending
        ? 'text-blue-400'
        : 'text-gray-500';

  // Title color
  const titleColor = isFailed
    ? 'text-red-400'
    : isCancelled
      ? 'text-yellow-400'
      : 'text-cyan-400';

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-gray-900/60 border-b border-cyan-500/20">
      {/* Left: Stage Info */}
      <div className="flex items-center gap-3">
        <div className={cn('w-2 h-2 rounded-full', indicatorColor)} />
        <div>
          <span className={cn('text-xs uppercase tracking-wider', statusLabelColor)}>
            {statusLabel}
          </span>
          <h2 className={cn('font-semibold text-lg', titleColor)}>
            {stage}
          </h2>
        </div>
        {agentCount > 0 && (
          <span className="text-xs text-gray-600 bg-gray-800 px-2 py-1 rounded">
            {agentCount} agents
          </span>
        )}
      </div>

      {/* Right: Toggle */}
      <button
        onClick={onToggleView}
        className={cn(
          'text-xs px-3 py-1.5 rounded transition-colors border',
          viewMode === 'clean'
            ? 'bg-cyan-500/20 border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/30'
            : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'
        )}
      >
        {viewMode === 'clean' ? '✨ Clean' : '📋 Full'}
      </button>
    </div>
  );
};