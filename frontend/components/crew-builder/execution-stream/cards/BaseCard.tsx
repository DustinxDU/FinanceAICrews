'use client';

import React from 'react';
import { LucideIcon } from 'lucide-react';

export interface BaseCardProps {
  id?: string;
  children: React.ReactNode;
  borderColor: string;
  bgColor: string;
  icon: LucideIcon;
  title: string;
  titleColor: string;
  agentName?: string;
  timestamp?: string;
  isProminent?: boolean;
}

export const BaseCard = ({
  id,
  children,
  borderColor,
  bgColor,
  icon: Icon,
  title,
  titleColor,
  agentName,
  timestamp,
  isProminent = false,
}: BaseCardProps) => {
  const prominentClasses = isProminent
    ? 'border-2 shadow-lg ring-1 ring-white/10'
    : 'border-l-4 shadow-md';

  return (
    <div
      id={id}
      className={`${prominentClasses} ${borderColor} ${bgColor} p-4 rounded-md text-sm text-gray-200 transition-all duration-200 hover:brightness-110`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className={`flex items-center gap-2 font-bold ${titleColor} uppercase text-xs tracking-wider`}>
          <Icon size={14} />
          <span>{title}</span>
          {agentName && (
            <span className="text-gray-400 font-normal lowercase">
              · {agentName}
            </span>
          )}
        </div>
        {timestamp && (
          <span className="text-[10px] text-gray-500 font-mono">
            {formatTimestamp(timestamp)}
          </span>
        )}
      </div>
      <div className="whitespace-pre-wrap font-mono text-xs leading-relaxed">
        {children}
      </div>
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
