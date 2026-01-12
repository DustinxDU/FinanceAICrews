import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { KLineChart } from '../charts/KLineChart';
import { EChartsProvider } from '../charts/EChartsProvider';

// Mock echarts-for-react
vi.mock('echarts-for-react', () => ({
  default: ({ option, theme, style }: any) => (
    <div data-testid="echarts-mock" data-theme={theme} style={style}>
      {JSON.stringify(option)}
    </div>
  ),
}));

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

// Mock data with OHLCV data (3 rows)
const mockData = {
  data: [
    { Date: '2024-01-15', Open: 180.5, High: 182.3, Low: 179.8, Close: 181.2, Volume: 52000000 },
    { Date: '2024-01-16', Open: 181.2, High: 183.5, Low: 180.1, Close: 182.8, Volume: 48000000 },
    { Date: '2024-01-17', Open: 182.8, High: 184.0, Low: 181.5, Close: 183.5, Volume: 55000000 },
  ],
  columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'],
  symbol: 'AAPL',
  period: '1mo',
};

describe('KLineChart', () => {
  it('renders chart container', () => {
    render(
      <EChartsProvider>
        <KLineChart data={mockData.data} columns={mockData.columns} symbol={mockData.symbol} />
      </EChartsProvider>
    );
    expect(screen.getByTestId('kline-chart')).toBeInTheDocument();
  });

  it('renders symbol in title', () => {
    render(
      <EChartsProvider>
        <KLineChart data={mockData.data} columns={mockData.columns} symbol={mockData.symbol} />
      </EChartsProvider>
    );
    expect(screen.getByText('AAPL')).toBeInTheDocument();
  });

  it('renders period selector buttons', () => {
    render(
      <EChartsProvider>
        <KLineChart data={mockData.data} columns={mockData.columns} symbol={mockData.symbol} />
      </EChartsProvider>
    );
    expect(screen.getByText('1D')).toBeInTheDocument();
    expect(screen.getByText('1W')).toBeInTheDocument();
    expect(screen.getByText('1M')).toBeInTheDocument();
  });
});
