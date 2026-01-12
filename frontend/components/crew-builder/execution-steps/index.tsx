import React from 'react';
import { Brain, Wrench, Eye, Flag } from 'lucide-react';

interface BaseCardProps {
  children: React.ReactNode;
  borderColor: string;
  bgColor: string;
  icon: React.ElementType;
  title: string;
  titleColor: string;
}

const BaseCard = ({ children, borderColor, bgColor, icon: Icon, title, titleColor }: BaseCardProps) => (
  <div className={`border-l-4 ${borderColor} ${bgColor} p-4 mb-4 rounded-r-md text-sm text-gray-200 shadow-md`}>
    <div className={`flex items-center gap-2 mb-2 font-bold ${titleColor} uppercase text-xs tracking-wider`}>
      <Icon size={14} />
      <span>{title}</span>
    </div>
    <div className="whitespace-pre-wrap font-mono">
      {children}
    </div>
  </div>
);

export const ThoughtCard = ({ content, agentName }: { content: string, agentName?: string }) => (
  <BaseCard
    borderColor="border-blue-500"
    bgColor="bg-blue-900/20"
    icon={Brain}
    title="THOUGHT"
    titleColor="text-blue-400"
  >
    {agentName && <div className="text-xs text-blue-300 mb-1">Agent: {agentName}</div>}
    {content}
  </BaseCard>
);

export const ToolCallCard = ({ toolName, input }: { toolName: string, input: string }) => (
  <BaseCard
    borderColor="border-yellow-500"
    bgColor="bg-yellow-900/20"
    icon={Wrench}
    title="TOOL CALL"
    titleColor="text-yellow-400"
  >
    <div className="font-semibold text-yellow-100">{toolName}</div>
    <div className="text-xs text-gray-400 mt-1">{input}</div>
  </BaseCard>
);

export const ObservationCard = ({ content }: { content: string }) => (
  <BaseCard
    borderColor="border-green-600"
    bgColor="bg-green-900/20"
    icon={Eye}
    title="OBSERVATION"
    titleColor="text-green-500"
  >
    {content}
  </BaseCard>
);

export const FinalResultCard = ({ content }: { content: string }) => (
  <BaseCard
    borderColor="border-green-400"
    bgColor="bg-green-900/30"
    icon={Flag}
    title="FINAL ANSWER"
    titleColor="text-green-300"
  >
    {content}
  </BaseCard>
);