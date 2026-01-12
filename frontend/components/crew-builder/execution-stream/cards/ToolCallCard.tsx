'use client';

import React from 'react';
import { Wrench } from 'lucide-react';
import { BaseCard } from './BaseCard';
import { ToolCallContent } from '../eventMapper';

interface ToolCallCardProps {
  id?: string;
  content: ToolCallContent;
  agentName?: string;
  timestamp?: string;
}

export const ToolCallCard = ({ id, content, agentName, timestamp }: ToolCallCardProps) => {
  return (
    <BaseCard
      id={id}
      borderColor="border-yellow-500"
      bgColor="bg-yellow-900/20"
      icon={Wrench}
      title="Tool Call"
      titleColor="text-yellow-400"
      agentName={agentName}
      timestamp={timestamp}
    >
      <div className="flex items-center gap-2">
        <span className="font-semibold text-yellow-100">{content.toolName}</span>
        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
          content.status === 'running' ? 'bg-yellow-500/30 text-yellow-300' :
          content.status === 'pending' ? 'bg-gray-500/30 text-gray-300' :
          'bg-gray-500/20 text-gray-400'
        }`}>
          {content.status}
        </span>
      </div>
      {content.input && Object.keys(content.input).length > 0 && (
        <div className="mt-2 text-gray-400">
          <pre className="text-[10px] overflow-x-auto max-h-24 overflow-y-auto">
            {JSON.stringify(content.input, null, 2)}
          </pre>
        </div>
      )}
    </BaseCard>
  );
};
