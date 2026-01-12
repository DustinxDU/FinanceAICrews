'use client';

import React from 'react';
import { FileText, CheckCircle, AlertTriangle, Quote } from 'lucide-react';
import { AgentOutputContent, detectChartableData } from '../eventMapper';
import { MiniLineChart, MiniBarChart, MiniPieChart } from '../charts';

interface AgentOutputCardProps {
  id?: string;
  content: AgentOutputContent;
  agentName?: string;
  timestamp?: string;
}

const outputModeLabels: Record<string, { label: string; color: string }> = {
  raw: { label: 'Raw', color: 'text-gray-400' },
  soft_pydantic: { label: 'Pydantic', color: 'text-cyan-400' },
  soft_json_dict: { label: 'JSON', color: 'text-blue-400' },
  native_pydantic: { label: 'Native', color: 'text-green-400' },
};

export const AgentOutputCard = ({ id, content, agentName, timestamp }: AgentOutputCardProps) => {
  const modeInfo = outputModeLabels[content.outputMode] || outputModeLabels.raw;
  
  // Detect chartable data in pydantic dump
  const chartData = content.pydanticDump ? detectChartableData(content.pydanticDump) : null;

  return (
    <div id={id} className="border-2 border-cyan-500 bg-gradient-to-br from-cyan-900/30 to-blue-900/20 p-4 rounded-lg shadow-lg ring-1 ring-cyan-400/20">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-cyan-500/20 rounded">
            <FileText size={16} className="text-cyan-400" />
          </div>
          <div>
            <span className="font-bold text-cyan-300 text-sm uppercase tracking-wider">
              Agent Output
            </span>
            {agentName && (
              <span className="text-gray-400 text-xs ml-2">
                {agentName}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Validation status */}
          {content.validationPassed ? (
            <span className="flex items-center gap-1 text-[10px] text-green-400 bg-green-500/20 px-2 py-0.5 rounded">
              <CheckCircle size={10} />
              Validated
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] text-yellow-400 bg-yellow-500/20 px-2 py-0.5 rounded">
              <AlertTriangle size={10} />
              Unvalidated
            </span>
          )}

          {/* Output mode badge */}
          <span className={`text-[10px] ${modeInfo.color} bg-gray-800/50 px-2 py-0.5 rounded`}>
            {modeInfo.label}
          </span>

          {/* Citation count */}
          {content.citationCount > 0 && (
            <span className="flex items-center gap-1 text-[10px] text-blue-400 bg-blue-500/20 px-2 py-0.5 rounded">
              <Quote size={10} />
              {content.citationCount}
            </span>
          )}

          {/* Timestamp */}
          {timestamp && (
            <span className="text-[10px] text-gray-500 font-mono">
              {formatTimestamp(timestamp)}
            </span>
          )}
        </div>
      </div>

      {/* Degraded warning */}
      {content.isDegraded && (
        <div className="mb-3 text-[11px] text-yellow-400 bg-yellow-500/10 border border-yellow-500/30 px-3 py-1.5 rounded flex items-center gap-2">
          <AlertTriangle size={12} />
          Output mode was degraded due to schema compatibility issues
        </div>
      )}

      {/* Warnings */}
      {content.warnings.length > 0 && (
        <div className="mb-3 space-y-1">
          {content.warnings.map((warning, i) => (
            <div key={i} className="text-[10px] text-yellow-400 bg-yellow-500/10 px-2 py-1 rounded">
              ⚠ {warning}
            </div>
          ))}
        </div>
      )}

      {/* Chart Rendering */}
      {chartData && (
        <div className="mb-3 p-3 bg-gray-900/50 rounded border border-cyan-500/20">
          {chartData.type === 'line' && (
            <MiniLineChart data={chartData.data} title={chartData.title} />
          )}
          {chartData.type === 'bar' && (
            <MiniBarChart data={chartData.data} title={chartData.title} />
          )}
          {chartData.type === 'pie' && (
            <MiniPieChart data={chartData.data} title={chartData.title} />
          )}
        </div>
      )}

      {/* Content Preview */}
      <div className="bg-gray-900/50 border border-cyan-500/20 rounded-lg p-4">
        <div className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap font-mono">
          {content.rawPreview || 'No output preview available'}
        </div>
      </div>

      {/* Pydantic dump (if available) */}
      {content.pydanticDump && Object.keys(content.pydanticDump).length > 0 && (
        <details className="mt-3">
          <summary className="cursor-pointer text-cyan-400 hover:text-cyan-300 text-xs">
            View structured data
          </summary>
          <pre className="mt-2 text-[10px] text-gray-400 bg-gray-800/50 p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
            {JSON.stringify(content.pydanticDump, null, 2)}
          </pre>
        </details>
      )}

      {/* Schema key info */}
      {content.schemaKey && (
        <div className="mt-3 text-[10px] text-gray-500">
          Schema: <span className="text-cyan-400">{content.schemaKey}</span>
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