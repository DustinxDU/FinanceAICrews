'use client';

import React from 'react';
import { Sparkles, Zap } from 'lucide-react';
import { BaseCard } from './BaseCard';
import { LLMCallContent } from '../eventMapper';

interface LLMCallCardProps {
  id?: string;
  content: LLMCallContent;
  agentName?: string;
  timestamp?: string;
}

export const LLMCallCard = ({ id, content, agentName, timestamp }: LLMCallCardProps) => {
  const isSuccess = content.status === 'success';
  const isRunning = content.status === 'running';

  return (
    <BaseCard
      id={id}
      borderColor="border-purple-500"
      bgColor="bg-purple-900/20"
      icon={Sparkles}
      title="LLM Call"
      titleColor="text-purple-400"
      agentName={agentName}
      timestamp={timestamp}
    >
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-1.5">
          <Zap size={12} className="text-purple-300" />
          <span className="text-purple-200 font-medium">{content.model}</span>
        </div>
        <span className="text-[10px] text-gray-500">{content.provider}</span>

        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
          isRunning ? 'bg-purple-500/30 text-purple-300 animate-pulse' :
          isSuccess ? 'bg-green-500/30 text-green-300' :
          'bg-red-500/30 text-red-300'
        }`}>
          {content.status}
        </span>
      </div>

      {content.tokens && (
        <div className="mt-2 flex gap-4 text-[10px] text-gray-400">
          <span>Prompt: <span className="text-purple-300">{content.tokens.prompt}</span></span>
          <span>Completion: <span className="text-purple-300">{content.tokens.completion}</span></span>
          <span>Total: <span className="text-purple-200 font-medium">{content.tokens.total}</span></span>
        </div>
      )}

      {content.durationMs && (
        <span className="text-[10px] text-gray-500 block mt-1">
          Duration: {content.durationMs}ms
        </span>
      )}

      {content.error && (
        <div className="mt-2 text-red-400 bg-red-900/30 p-2 rounded text-[11px]">
          {content.error}
        </div>
      )}

      {(content.promptPreview || content.responsePreview) && (
        <details className="mt-2">
          <summary className="cursor-pointer text-purple-400 hover:text-purple-300 text-[10px]">
            View conversation preview
          </summary>
          <div className="mt-2 space-y-2">
            {content.promptPreview && (
              <div className="bg-gray-800/50 p-2 rounded">
                <span className="text-[10px] text-gray-500 block mb-1">Prompt:</span>
                <span className="text-[11px] text-gray-300 line-clamp-3">{content.promptPreview}</span>
              </div>
            )}
            {content.responsePreview && (
              <div className="bg-purple-800/30 p-2 rounded">
                <span className="text-[10px] text-gray-500 block mb-1">Response:</span>
                <span className="text-[11px] text-gray-200 line-clamp-3">{content.responsePreview}</span>
              </div>
            )}
          </div>
        </details>
      )}
    </BaseCard>
  );
};
