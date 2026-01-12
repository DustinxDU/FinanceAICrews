'use client';

import React from 'react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';

interface MiniLineChartProps {
  data: Array<{ value: number; timestamp?: string }>;
  title?: string;
  height?: number;
  color?: string;
}

export const MiniLineChart = ({ 
  data, 
  title, 
  height = 60,
  color = '#22d3ee' 
}: MiniLineChartProps) => {
  return (
    <div className="w-full">
      {title && <div className="text-[10px] text-gray-500 mb-1">{title}</div>}
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <YAxis hide domain={['auto', 'auto']} />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke={color} 
              strokeWidth={2} 
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
