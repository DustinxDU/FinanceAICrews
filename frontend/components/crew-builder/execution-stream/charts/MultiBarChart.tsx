'use client';

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface MultiBarChartProps {
  data: Array<Record<string, any>>;
  series: string[];
  title?: string;
  height?: number;
}

// Color palette for multiple series
const COLORS = [
  '#22d3ee', // cyan
  '#34d399', // green
  '#fbbf24', // yellow
  '#f472b6', // pink
  '#a78bfa', // purple
  '#60a5fa', // blue
];

export const MultiBarChart = ({
  data,
  series,
  title,
  height = 180
}: MultiBarChartProps) => {
  return (
    <div className="w-full">
      {title && <div className="text-xs text-gray-400 mb-2 font-medium">{title}</div>}
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
            <XAxis
              dataKey="name"
              tick={{ fill: '#9ca3af', fontSize: 10 }}
              axisLine={{ stroke: '#374151' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: '#9ca3af', fontSize: 10 }}
              axisLine={{ stroke: '#374151' }}
              tickLine={false}
              tickFormatter={(value) => `${value.toFixed(0)}B`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: '1px solid #374151',
                borderRadius: '6px',
                fontSize: '11px',
              }}
              labelStyle={{ color: '#e5e7eb', fontWeight: 'bold', marginBottom: '4px' }}
              formatter={(value, name, props) => {
                // Try to get the formatted value if available
                const formattedKey = `${name}_formatted`;
                const formattedValue = props?.payload?.[formattedKey];
                const numValue = typeof value === 'number' ? value : 0;
                return [formattedValue || `$${numValue.toFixed(1)}B`, name];
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: '10px', paddingTop: '8px' }}
              iconSize={8}
            />
            {series.map((key, index) => (
              <Bar
                key={key}
                dataKey={key}
                fill={COLORS[index % COLORS.length]}
                radius={[2, 2, 0, 0]}
                maxBarSize={40}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
