'use client';

import React from 'react';
import { Flag, CheckCircle, XCircle, Clock } from 'lucide-react';
import { StatusContent } from '../eventMapper';

interface StatusCardProps {
  id?: string;
  content: StatusContent;
  timestamp?: string;
}

export const StatusCard = ({ id, content, timestamp }: StatusCardProps) => {
  const isCompleted = content.status === 'completed';
  const StatusIcon = isCompleted ? CheckCircle : XCircle;

  return (
    <div id={id} className={`border-l-4 ${isCompleted ? 'border-green-500 bg-green-900/30' : 'border-red-500 bg-red-900/30'} p-3 rounded-r-md`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <StatusIcon size={16} className={isCompleted ? 'text-green-400' : 'text-red-400'} />
          <span className={`font-bold text-sm ${isCompleted ? 'text-green-300' : 'text-red-300'}`}>
            Job {isCompleted ? 'Completed' : 'Failed'}
          </span>
        </div>

        <div className="flex items-center gap-3 text-xs text-gray-400">
          {content.durationMs && (
            <span className="flex items-center gap-1">
              <Clock size={12} />
              {formatDuration(content.durationMs)}
            </span>
          )}
          {timestamp && (
            <span className="font-mono text-[10px]">
              {formatTimestamp(timestamp)}
            </span>
          )}
        </div>
      </div>

      {content.error && (
        <div className="mt-2 text-red-400 bg-red-900/30 p-2 rounded text-xs">
          {content.error}
        </div>
      )}
    </div>
  );
};

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  } catch {
    return '';
  }
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = ((ms % 60000) / 1000).toFixed(0);
  return `${minutes}m ${seconds}s`;
}