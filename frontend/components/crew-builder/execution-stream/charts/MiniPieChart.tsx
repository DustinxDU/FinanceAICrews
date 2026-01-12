'use client';

import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface MiniPieChartProps {
  data: Array<{ name: string; value: number }>;
  title?: string;
  size?: number;
}

const COLORS = ['#60A5FA', '#34D399', '#FBBF24', '#F87171', '#A78BFA', '#22D3EE'];

export const MiniPieChart = ({ 
  data, 
  title, 
  size = 120 
}: MiniPieChartProps) => {
  return (
    <div className="flex flex-col items-center">
      {title && <div className="text-[10px] text-gray-500 mb-2 w-full text-left">{title}</div>}
      <div style={{ width: '100%', height: size }} className="relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              innerRadius={size / 4}
              outerRadius={size / 2.5}
              paddingAngle={2}
              dataKey="value"
              stroke="none"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip 
              contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', fontSize: '10px' }}
              itemStyle={{ color: '#e5e7eb' }}
            />
            <Legend 
              verticalAlign="middle" 
              align="right"
              layout="vertical"
              iconSize={8}
              wrapperStyle={{ fontSize: '10px' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
