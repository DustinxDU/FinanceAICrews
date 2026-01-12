'use client';

import React, { useMemo, useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { motion } from 'framer-motion';
import { useEChartsTheme } from './EChartsProvider';
import { cardVariants, chartAnimation } from '../core/animations';
import { registerChartComponent, ChartComponentProps } from '../core/chartRegistry';

/** OHLCV row interface for K-line data */
export interface OHLCVRow {
  Date: string;
  Open: number;
  High: number;
  Low: number;
  Close: number;
  Volume: number;
}

export interface KLineChartProps {
  data: OHLCVRow[];
  columns?: string[];
  symbol?: string;
  period?: string;
  height?: number;
  onPeriodChange?: (period: string) => void;
}

/** Period selector options */
const PERIOD_OPTIONS = ['1D', '1W', '1M', '3M', '1Y'];

/** Calculate simple moving average */
function calculateMA(data: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else {
      let sum = 0;
      for (let j = 0; j < period; j++) {
        sum += data[i - j];
      }
      result.push(sum / period);
    }
  }
  return result;
}

function KLineChartComponent({
  data,
  columns,
  symbol = '',
  period = '1M',
  height = 400,
  onPeriodChange,
}: KLineChartProps) {
  const { name: themeName } = useEChartsTheme();
  const [selectedPeriod, setSelectedPeriod] = useState(period);
  const [chartHeight, setChartHeight] = useState(height);

  // Responsive height adjustment based on viewport width
  useEffect(() => {
    const handleResize = () => {
      // Reduce height on mobile (< 640px)
      if (window.innerWidth < 640) {
        setChartHeight(Math.min(height, 280));
      } else if (window.innerWidth < 1024) {
        setChartHeight(Math.min(height, 340));
      } else {
        setChartHeight(height);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [height]);

  // Process data with useMemo: sort by date, format OHLC for ECharts
  const processedData = useMemo(() => {
    if (!data || data.length === 0) {
      return { dates: [], ohlc: [], volume: [], closes: [] };
    }

    // Sort by date
    const sortedData = [...data].sort((a, b) =>
      new Date(a.Date).getTime() - new Date(b.Date).getTime()
    );

    const dates: string[] = [];
    const ohlc: [number, number, number, number][] = []; // [open, close, low, high]
    const volume: number[] = [];
    const closes: number[] = [];

    sortedData.forEach((row) => {
      dates.push(row.Date);
      // ECharts candlestick format: [open, close, low, high]
      ohlc.push([row.Open, row.Close, row.Low, row.High]);
      volume.push(row.Volume);
      closes.push(row.Close);
    });

    return { dates, ohlc, volume, closes };
  }, [data]);

  // Calculate MA5 and MA20 moving averages
  const ma5 = useMemo(() => calculateMA(processedData.closes, 5), [processedData.closes]);
  const ma20 = useMemo(() => calculateMA(processedData.closes, 20), [processedData.closes]);

  // Determine volume bar colors based on price direction
  const volumeColors = useMemo(() => {
    return processedData.ohlc.map((item) => {
      // item[0] = open, item[1] = close
      return item[1] >= item[0] ? '#10b981' : '#ef4444'; // green up, red down
    });
  }, [processedData.ohlc]);

  // ECharts option configuration
  const option = useMemo(() => ({
    animation: true,
    animationDuration: chartAnimation.duration,
    animationEasing: chartAnimation.easing,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
      },
    },
    legend: {
      data: ['K-Line', 'MA5', 'MA20'],
      top: 10,
      textStyle: { color: '#9ca3af' },
    },
    grid: [
      {
        left: '10%',
        right: '10%',
        top: '15%',
        height: '55%', // Main chart 55%
      },
      {
        left: '10%',
        right: '10%',
        top: '75%',
        height: '18%', // Volume chart 18%
      },
    ],
    xAxis: [
      {
        type: 'category',
        data: processedData.dates,
        gridIndex: 0,
        axisLine: { lineStyle: { color: '#374151' } },
        axisLabel: { color: '#9ca3af', fontSize: 10 },
        axisTick: { show: false },
      },
      {
        type: 'category',
        data: processedData.dates,
        gridIndex: 1,
        axisLine: { lineStyle: { color: '#374151' } },
        axisLabel: { show: false },
        axisTick: { show: false },
      },
    ],
    yAxis: [
      {
        type: 'value',
        position: 'right',
        gridIndex: 0,
        axisLine: { lineStyle: { color: '#374151' } },
        axisLabel: { color: '#9ca3af', fontSize: 10 },
        splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } },
      },
      {
        type: 'value',
        position: 'right',
        gridIndex: 1,
        axisLine: { lineStyle: { color: '#374151' } },
        axisLabel: { color: '#9ca3af', fontSize: 10 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: 'K-Line',
        type: 'candlestick',
        data: processedData.ohlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#10b981',        // green for up (close > open)
          color0: '#ef4444',       // red for down (close < open)
          borderColor: '#10b981',
          borderColor0: '#ef4444',
        },
      },
      {
        name: 'MA5',
        type: 'line',
        data: ma5,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        lineStyle: {
          width: 1,
          color: '#3b82f6', // blue
        },
        symbol: 'none',
      },
      {
        name: 'MA20',
        type: 'line',
        data: ma20,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: false,
        lineStyle: {
          width: 1,
          type: 'dashed',
          color: '#f59e0b', // amber
        },
        symbol: 'none',
      },
      {
        name: 'Volume',
        type: 'bar',
        data: processedData.volume.map((vol, idx) => ({
          value: vol,
          itemStyle: { color: volumeColors[idx] },
        })),
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: 50,
        end: 100,
      },
    ],
  }), [processedData, ma5, ma20, volumeColors]);

  const handlePeriodChange = (newPeriod: string) => {
    setSelectedPeriod(newPeriod);
    onPeriodChange?.(newPeriod);
  };

  return (
    <motion.div
      data-testid="kline-chart"
      className="w-full bg-slate-800/50 rounded-lg border border-slate-700/50 p-4"
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
    >
      {/* Header with symbol and period selector */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold text-white">{symbol}</span>
          <span className="text-sm text-slate-400">K-Line</span>
        </div>
        <div className="flex items-center gap-1">
          {PERIOD_OPTIONS.map((p) => (
            <button
              key={p}
              onClick={() => handlePeriodChange(p)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                selectedPeriod === p
                  ? 'bg-blue-500 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* ECharts component */}
      <ReactECharts
        option={option}
        theme={themeName}
        style={{ height: chartHeight - 60, width: '100%' }}
        notMerge={true}
        lazyUpdate={true}
      />
    </motion.div>
  );
}

// Wrap with React.memo to prevent unnecessary re-renders
export const KLineChart = React.memo(KLineChartComponent);
KLineChart.displayName = 'KLineChart';

// ============ Chart Router Registration ============

/**
 * Adapter to match ChartComponentProps interface
 * Extracts kline data from the standard { data, columns, symbol } format
 */
function KLineChartAdapter({ data, metadata }: ChartComponentProps) {
  const ohlcvData = data.data || [];
  const columns = data.columns || metadata?.columns || [];
  const symbol = data.symbol || metadata?.symbol || '';
  const period = data.period || '1M';

  return (
    <KLineChart
      data={ohlcvData}
      columns={columns}
      symbol={symbol}
      period={period}
    />
  );
}

// Register with ChartRouter for 'kline' data type
registerChartComponent('kline', KLineChartAdapter);

export default KLineChart;
