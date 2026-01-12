'use client';

import React from 'react';
import { BarChart, Bar, ResponsiveContainer, Cell, XAxis, YAxis } from 'recharts';

interface MiniBarChartProps {
  data: Array<{ name: string; value: number }>;
  title?: string;
  height?: number;
}

export const MiniBarChart = ({ 
  data, 
  title, 
  height = 100 
}: MiniBarChartProps) => {
  return (
    <div className="w-full">
      {title && <div className="text-[10px] text-gray-500 mb-1">{title}</div>}
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 40, right: 10 }}>
            <XAxis type="number" hide />
            <YAxis 
              type="category" 
              dataKey="name" 
              width={40}
              tick={{ fontSize: 9, fill: '#9ca3af' }}
              interval={0}
            />
            <Bar dataKey="value" barSize={12} radius={[0, 4, 4, 0]}>
              {data.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.value >= 0 ? '#34d399' : '#f87171'} 
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
