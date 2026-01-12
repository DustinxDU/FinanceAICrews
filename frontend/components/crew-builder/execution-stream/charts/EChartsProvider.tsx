'use client';

import React, { createContext, useContext, useMemo } from 'react';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import {
  LineChart,
  BarChart,
  CandlestickChart,
  PieChart,
  RadarChart,
  SankeyChart,
  GaugeChart,
} from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent,
  VisualMapComponent,
} from 'echarts/components';

// Register required components
echarts.use([
  CanvasRenderer,
  LineChart,
  BarChart,
  CandlestickChart,
  PieChart,
  RadarChart,
  SankeyChart,
  GaugeChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent,
  VisualMapComponent,
]);

// Finance AI Dark Theme
const financeAIDarkTheme = {
  name: 'financeAIDark',
  theme: {
    color: [
      '#10b981', // green - primary
      '#3b82f6', // blue
      '#f59e0b', // amber
      '#ef4444', // red
      '#8b5cf6', // purple
      '#ec4899', // pink
      '#06b6d4', // cyan
      '#84cc16', // lime
    ],
    backgroundColor: 'transparent',
    textStyle: {
      color: '#d1d5db', // gray-300
    },
    title: {
      textStyle: {
        color: '#f3f4f6', // gray-100
        fontSize: 14,
        fontWeight: 600,
      },
    },
    legend: {
      textStyle: {
        color: '#9ca3af', // gray-400
      },
    },
    tooltip: {
      backgroundColor: 'rgba(17, 24, 39, 0.95)', // gray-900
      borderColor: '#374151', // gray-700
      textStyle: {
        color: '#f3f4f6',
      },
    },
    xAxis: {
      axisLine: { lineStyle: { color: '#374151' } },
      axisTick: { lineStyle: { color: '#374151' } },
      axisLabel: { color: '#9ca3af' },
      splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } },
    },
    yAxis: {
      axisLine: { lineStyle: { color: '#374151' } },
      axisTick: { lineStyle: { color: '#374151' } },
      axisLabel: { color: '#9ca3af' },
      splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } },
    },
    candlestick: {
      itemStyle: {
        color: '#10b981',      // green for up
        color0: '#ef4444',     // red for down
        borderColor: '#10b981',
        borderColor0: '#ef4444',
      },
    },
    graph: {
      color: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'],
    },
  },
};

// Register theme
echarts.registerTheme(financeAIDarkTheme.name, financeAIDarkTheme.theme);

interface EChartsThemeContext {
  name: string;
  echarts: typeof echarts;
}

const ThemeContext = createContext<EChartsThemeContext>({
  name: financeAIDarkTheme.name,
  echarts,
});

export function useEChartsTheme() {
  return useContext(ThemeContext);
}

export function useECharts() {
  return echarts;
}

interface EChartsProviderProps {
  children: React.ReactNode;
}

export function EChartsProvider({ children }: EChartsProviderProps) {
  const value = useMemo(() => ({
    name: financeAIDarkTheme.name,
    echarts,
  }), []);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

// Export echarts instance for direct use
export { echarts };
export default EChartsProvider;
