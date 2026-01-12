import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { FinancialBarChart } from '../charts/FinancialBarChart';
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

const mockData = {
  data: [
    { Date: '2021-12-31', 'Total Revenue': 365817000000, 'Net Income': 94680000000 },
    { Date: '2022-12-31', 'Total Revenue': 394328000000, 'Net Income': 99803000000 },
    { Date: '2023-12-31', 'Total Revenue': 383285000000, 'Net Income': 96995000000 },
  ],
  columns: ['Date', 'Total Revenue', 'Net Income'],
  statement_type: 'income',
  symbol: 'AAPL',
};

describe('FinancialBarChart', () => {
  it('renders chart container', () => {
    render(
      <EChartsProvider>
        <FinancialBarChart data={mockData} />
      </EChartsProvider>
    );
    expect(screen.getByTestId('financial-bar-chart')).toBeInTheDocument();
  });

  it('renders title with statement type', () => {
    render(
      <EChartsProvider>
        <FinancialBarChart data={mockData} title="AAPL Income Statement" />
      </EChartsProvider>
    );
    expect(screen.getByText(/Income Statement/i)).toBeInTheDocument();
  });

  it('renders with legend items', () => {
    render(
      <EChartsProvider>
        <FinancialBarChart data={mockData} />
      </EChartsProvider>
    );
    // Check that the ECharts mock received the option with series
    const echartsMock = screen.getByTestId('echarts-mock');
    expect(echartsMock.textContent).toContain('Revenue');
  });
});
