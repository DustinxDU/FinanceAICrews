'use client';

import React from 'react';
import { Info } from 'lucide-react';
import { BaseCard } from './BaseCard';
import { SystemContent } from '../eventMapper';

interface SystemCardProps {
  id?: string;
  content: SystemContent;
  timestamp?: string;
}

export const SystemCard = ({ id, content, timestamp }: SystemCardProps) => {
  return (
    <BaseCard
      id={id}
      borderColor="border-gray-500"
      bgColor="bg-gray-800/30"
      icon={Info}
      title="System"
      titleColor="text-gray-400"
      timestamp={timestamp}
    >
      <div className="text-gray-400 italic">
        {content.message}
      </div>
    </BaseCard>
  );
};
