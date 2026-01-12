import React from 'react';
import { ExecutionStep } from './types';
import { ThoughtCard, ToolCallCard, ObservationCard, FinalResultCard } from './index';

interface ExecutionStreamContainerProps {
  steps: ExecutionStep[];
}

export const ExecutionStreamContainer = ({ steps }: ExecutionStreamContainerProps) => {
  if (steps.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 italic">
        Waiting for execution to start...
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 h-full overflow-y-auto p-4 bg-gray-950 rounded-md border border-gray-800">
      {steps.map((step) => {
        switch (step.type) {
          case 'thought':
            return (
              <ThoughtCard 
                key={step.id} 
                content={step.content || ''} 
                agentName={step.agentName} 
              />
            );
          case 'tool_call':
            return (
              <ToolCallCard 
                key={step.id} 
                toolName={step.toolName || 'Unknown Tool'} 
                input={step.input || ''} 
              />
            );
          case 'observation':
            return (
              <ObservationCard 
                key={step.id} 
                content={step.content || ''} 
              />
            );
          case 'final_answer':
            return (
              <FinalResultCard 
                key={step.id} 
                content={step.content || ''} 
              />
            );
          default:
            return null;
        }
      })}
    </div>
  );
};