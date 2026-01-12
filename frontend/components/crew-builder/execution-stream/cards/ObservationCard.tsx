'use client';

import React from 'react';
import { Eye, CheckCircle, XCircle } from 'lucide-react';
import { BaseCard } from './BaseCard';
import { ToolResultContent } from '../eventMapper';
import { ChartRouter, detectDataType } from '../core';

interface ObservationCardProps {
  id?: string;
  content: ToolResultContent;
  agentName?: string;
  timestamp?: string;
}

export const ObservationCard = ({ id, content, agentName, timestamp }: ObservationCardProps) => {
  const isSuccess = content.status === 'success';
  const StatusIcon = isSuccess ? CheckCircle : XCircle;

  // DEBUG: Log what data we receive
  if (process.env.NODE_ENV === 'development') {
    console.log('[ObservationCard] Rendering with content:', content);
    console.log('[ObservationCard] output type:', typeof content.output, content.output);
  }

  return (
    <BaseCard
      id={id}
      borderColor={isSuccess ? 'border-green-600' : 'border-red-600'}
      bgColor={isSuccess ? 'bg-green-900/20' : 'bg-red-900/20'}
      icon={Eye}
      title="Observation"
      titleColor={isSuccess ? 'text-green-500' : 'text-red-500'}
      agentName={agentName}
      timestamp={timestamp}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="font-semibold text-gray-200">{content.toolName}</span>
        <StatusIcon size={14} className={isSuccess ? 'text-green-400' : 'text-red-400'} />
        {content.durationMs && (
          <span className="text-[10px] text-gray-500">
            {content.durationMs}ms
          </span>
        )}
      </div>

      {content.error ? (
        <div className="text-red-400 bg-red-900/30 p-2 rounded text-[11px]">
          {content.error}
        </div>
      ) : content.output ? (
        <div className="text-gray-300">
          <ChartRouter data={content.output} />

          {/* Raw JSON fallback only if ChartRouter doesn't detect a type */}
          {!detectDataType(content.output) && (
            <details>
              <summary className="cursor-pointer text-green-400 hover:text-green-300 text-[10px]">
                View raw output {(() => {
                  let parsed = content.output;
                  if (typeof parsed === 'string') {
                    try { parsed = JSON.parse(parsed); } catch { return ''; }
                  }
                  return typeof parsed === 'object' && parsed !== null
                    ? `(${Object.keys(parsed).length} fields)`
                    : '';
                })()}
              </summary>
              <pre className="mt-2 text-[10px] overflow-x-auto max-h-60 overflow-y-auto bg-gray-900 p-2 rounded">
                {typeof content.output === 'string'
                  ? (() => {
                      try {
                        return JSON.stringify(JSON.parse(content.output), null, 2);
                      } catch {
                        return content.output;
                      }
                    })()
                  : JSON.stringify(content.output, null, 2)}
              </pre>
            </details>
          )}
        </div>
      ) : (
        <span className="text-gray-500 italic">No output</span>
      )}
    </BaseCard>
  );
};
