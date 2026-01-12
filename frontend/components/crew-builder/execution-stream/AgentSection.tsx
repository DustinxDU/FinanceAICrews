'use client';

import React from 'react';
import { ChevronDown, ChevronRight, CheckCircle, Clock, AlertCircle, Circle } from 'lucide-react';
import { MappedEvent } from './eventMapper';

interface AgentSectionProps {
  agentName: string;
  events: MappedEvent[];
  isExpanded: boolean;
  onToggle: () => void;
  status: 'idle' | 'active' | 'completed' | 'failed';
  children: React.ReactNode;
}

export const AgentSection = ({
  agentName,
  events,
  isExpanded,
  onToggle,
  status,
  children
}: AgentSectionProps) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'completed': return <CheckCircle size={16} className="text-green-400" />;
      case 'failed': return <AlertCircle size={16} className="text-red-400" />;
      case 'active': return <Clock size={16} className="text-blue-400 animate-pulse" />;
      default: return <Circle size={16} className="text-gray-600" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'completed': return 'border-l-green-500/50 bg-green-900/5';
      case 'failed': return 'border-l-red-500/50 bg-red-900/5';
      case 'active': return 'border-l-blue-500/50 bg-blue-900/5';
      default: return 'border-l-gray-700 bg-gray-900/20';
    }
  };

  return (
    <div className={`mb-4 rounded-lg border border-gray-800 overflow-hidden transition-all duration-300 ${getStatusColor()} border-l-4`}>
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown size={16} className="text-gray-400" />
          ) : (
            <ChevronRight size={16} className="text-gray-400" />
          )}
          
          <div className="flex items-center gap-2">
            {getStatusIcon()}
            <span className={`font-medium ${status === 'active' ? 'text-blue-100' : 'text-gray-200'}`}>
              {agentName}
            </span>
          </div>
          
          <span className="text-xs text-gray-500 px-2 py-0.5 rounded-full bg-gray-900/50 border border-gray-800">
            {events.length} events
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs text-gray-500">
          {status === 'active' && <span className="text-blue-400">Running...</span>}
          {status === 'completed' && <span className="text-green-400">Done</span>}
        </div>
      </button>

      {isExpanded && (
        <div className="p-4 pt-0 border-t border-gray-800/50 space-y-3 bg-black/10">
          <div className="h-2" /> {/* Spacer */}
          {children}
        </div>
      )}
    </div>
  );
};
