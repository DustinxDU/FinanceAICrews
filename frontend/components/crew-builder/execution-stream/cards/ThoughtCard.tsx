'use client';

import React from 'react';
import { Brain } from 'lucide-react';
import { BaseCard } from './BaseCard';
import { ThoughtContent } from '../eventMapper';

interface ThoughtCardProps {
  id?: string;
  content: ThoughtContent;
  agentName?: string;
  timestamp?: string;
}

const activityLabels: Record<string, string> = {
  thinking: 'Thinking',
  tool_call: 'Preparing Tool',
  llm_call: 'LLM Processing',
  delegation: 'Delegating',
  output: 'Producing Output',
  task_completed: 'Task Completed',
};

export const ThoughtCard = ({ id, content, agentName, timestamp }: ThoughtCardProps) => {
  const label = activityLabels[content.activityType] || 'Thinking';

  return (
    <BaseCard
      id={id}
      borderColor="border-blue-500"
      bgColor="bg-blue-900/20"
      icon={Brain}
      title={label}
      titleColor="text-blue-400"
      agentName={agentName}
      timestamp={timestamp}
    >
      <div className="text-gray-200">
        {content.message}
      </div>
      {content.details && Object.keys(content.details).length > 0 && (
        <details className="mt-2">
          <summary className="text-blue-400 cursor-pointer text-[10px] hover:text-blue-300">
            Show details
          </summary>
          <pre className="mt-1 text-[10px] text-gray-400 overflow-x-auto">
            {JSON.stringify(content.details, null, 2)}
          </pre>
        </details>
      )}
    </BaseCard>
  );
};
