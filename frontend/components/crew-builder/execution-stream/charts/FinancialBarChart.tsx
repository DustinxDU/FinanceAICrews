'use client';

import React, { useMemo, useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { motion } from 'framer-motion';
import { useEChartsTheme } from './EChartsProvider';
import { cardVariants, chartAnimation } from '../core/animations';
import { registerChartComponent, ChartComponentProps } from '../core/chartRegistry';

interface FinancialBarChartProps {
  data: {
    data: Array<Record<string, any>>;
    columns?: string[];
    statement_type?: string;
    symbol?: string;
  };
  title?: string;
  height?: number;
}

const METRIC_CONFIG: Record<string, { color: string; label: string }> = {
  'Total Revenue': { color: '#3b82f6', label: 'Revenue' },
  'Net Income': { color: '#10b981', label: 'Net Income' },
  'Gross Profit': { color: '#8b5cf6', label: 'Gross Profit' },
  'Operating Income': { color: '#f59e0b', label: 'Operating Income' },
  'Total Assets': { color: '#3b82f6', label: 'Total Assets' },
  'Total Liabilities': { color: '#ef4444', label: 'Total Liabilities' },
  'Total Equity': { color: '#10b981', label: 'Total Equity' },
  'Operating Cash Flow': { color: '#3b82f6', label: 'Operating CF' },
  'Free Cash Flow': { color: '#10b981', label: 'Free CF' },
};

function formatLargeNumber(num: number): string {
  if (Math.abs(num) >= 1e12) return (num / 1e12).toFixed(1) + 'T';
  if (Math.abs(num) >= 1e9) return (num / 1e9).toFixed(1) + 'B';
  if (Math.abs(num) >= 1e6) return (num / 1e6).toFixed(1) + 'M';
  return num.toLocaleString();
}

function FinancialBarChartComponent({ data, title, height = 300 }: FinancialBarChartProps) {
  const { name: themeName } = useEChartsTheme();
  const [chartHeight, setChartHeight] = useState(height);

  // Responsive height adjustment based on viewport width
  useEffect(() => {
    const handleResize = () => {
      // Reduce height on mobile (< 640px)
      if (window.innerWidth < 640) {
        setChartHeight(Math.min(height, 220));
      } else if (window.innerWidth < 1024) {
        setChartHeight(Math.min(height, 260));
      } else {
        setChartHeight(height);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [height]);

  const chartData = useMemo(() => {
    if (!data.data || !Array.isArray(data.data)) return { years: [], series: [] };

    // Sort by date (oldest to newest)
    const sorted = [...data.data].sort((a, b) =>
      new Date(a.Date).getTime() - new Date(b.Date).getTime()
    );

    // Extract years
    const years = sorted.map(row => new Date(row.Date).getFullYear().toString());

    // Find numeric columns (metrics)
    const metricCols = Object.keys(sorted[0] || {}).filter(key =>
      key !== 'Date' && typeof sorted[0][key] === 'number'
    );

    // Build series
    const series = metricCols.map(metric => {
      const config = METRIC_CONFIG[metric] || { color: '#6b7280', label: metric };
      return {
        name: config.label,
        type: 'bar' as const,
        data: sorted.map(row => (row[metric] || 0) / 1e9), // Convert to billions
        itemStyle: { color: config.color },
        emphasis: { focus: 'series' as const },
      };
    });

    return { years, series, metricCols };
  }, [data.data]);

  const option = useMemo(() => ({
    animation: true,
    animationDuration: chartAnimation.duration,
    animationEasing: chartAnimation.easing,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        let result = '<div class="font-semibold mb-1">' + params[0]?.axisValue + '</div>';
        params.forEach((p: any) => {
          const value = p.value * 1e9;
          result += '<div class="flex justify-between gap-4">' +
            '<span style="color:' + p.color + '">' + p.seriesName + '</span>' +
            '<span class="font-mono">' + formatLargeNumber(value) + '</span>' +
          '</div>';
        });
        return result;
      },
    },
    legend: {
      data: chartData.series.map(s => s.name),
      bottom: 0,
      textStyle: { color: '#9ca3af' },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: chartData.years,
      axisLine: { lineStyle: { color: '#374151' } },
      axisLabel: { color: '#9ca3af' },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (value: number) => value + 'B',
        color: '#9ca3af',
      },
      axisLine: { lineStyle: { color: '#374151' } },
      splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } },
    },
    series: chartData.series,
  }), [chartData]);

  const displayTitle = title || (data.symbol || '') + ' ' + (data.statement_type || 'Financial') + ' Statement';

  if (chartData.years.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-500">
        No financial data available
      </div>
    );
  }

  return (
    <motion.div
      data-testid="financial-bar-chart"
      className="w-full bg-slate-800/50 rounded-lg border border-slate-700/50 overflow-hidden"
      variants={cardVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <div className="p-3 border-b border-slate-700/50">
        <h3 className="font-semibold text-white text-sm">{displayTitle}</h3>
        <p className="text-xs text-slate-500">Values in Billions USD</p>
      </div>

      {/* Chart */}
      <div className="p-2">
        <ReactECharts
          option={option}
          theme={themeName}
          style={{ height: chartHeight }}
          opts={{ renderer: 'canvas' }}
          notMerge={true}
          lazyUpdate={true}
        />
      </div>
    </motion.div>
  );
}

// Wrap with React.memo to prevent unnecessary re-renders
export const FinancialBarChart = React.memo(FinancialBarChartComponent);
FinancialBarChart.displayName = 'FinancialBarChart';

// ============ Chart Router Registration ============

/**
 * Adapter to match ChartComponentProps interface
 */
function FinancialBarChartAdapter({ data, metadata }: ChartComponentProps) {
  return (
    <FinancialBarChart
      data={data}
      title={metadata?.title}
    />
  );
}

// Register with ChartRouter for 'financial' data type
registerChartComponent('financial', FinancialBarChartAdapter);

export default FinancialBarChart;
