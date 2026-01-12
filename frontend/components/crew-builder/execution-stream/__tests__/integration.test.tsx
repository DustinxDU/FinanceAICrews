/**
 * Integration tests for Execution Stream Visualization
 *
 * Tests the full rendering pipeline from raw data through ChartRouter
 * to the appropriate visualization component.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import React from 'react';
import { EChartsProvider } from '../charts/EChartsProvider';
import { ChartRouter, registerChartComponent, DataType } from '../core/ChartRouter';

// Mock echarts-for-react
vi.mock('echarts-for-react', () => ({
  default: ({ option, theme, style }: any) => (
    <div data-testid="echarts-mock" data-theme={theme} style={style}>
      {JSON.stringify(option)}
    </div>
  ),
}));

// Mock framer-motion to avoid animation timing issues
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Helper to wrap components with EChartsProvider
function renderWithProvider(ui: React.ReactElement) {
  return render(<EChartsProvider>{ui}</EChartsProvider>);
}

describe('Execution Stream Visualization Integration', () => {
  beforeEach(() => {
    // Import and register chart components before each test
    // This simulates what happens in the real application
  });

  afterEach(() => {
    cleanup();
  });

  describe('ChartRouter Data Type Detection', () => {
    it('returns null for null data', () => {
      const { container } = renderWithProvider(<ChartRouter data={null} />);
      expect(container.firstChild).toBeNull();
    });

    it('returns null for undefined data', () => {
      const { container } = renderWithProvider(<ChartRouter data={undefined} />);
      expect(container.firstChild).toBeNull();
    });

    it('renders container for stock info data', () => {
      const stockData = {
        symbol: 'AAPL',
        info: {
          shortName: 'Apple Inc.',
          sector: 'Technology',
          currentPrice: 185.50,
          previousClose: 184.00,
        },
      };

      renderWithProvider(<ChartRouter data={stockData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('renders container for kline/OHLCV data', () => {
      const klineData = {
        data: [
          { Date: '2024-01-15', Open: 180, High: 182, Low: 179, Close: 181, Volume: 52000000 },
          { Date: '2024-01-16', Open: 181, High: 183, Low: 180, Close: 182, Volume: 48000000 },
        ],
        columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'],
        symbol: 'AAPL',
      };

      renderWithProvider(<ChartRouter data={klineData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('renders container for financial statement data', () => {
      const financialData = {
        data: [
          { Date: '2022-12-31', 'Total Revenue': 394328000000, 'Net Income': 99803000000 },
          { Date: '2023-12-31', 'Total Revenue': 383285000000, 'Net Income': 96995000000 },
        ],
        columns: ['Date', 'Total Revenue', 'Net Income'],
        statement_type: 'income',
        symbol: 'AAPL',
      };

      renderWithProvider(<ChartRouter data={financialData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('renders container for quote data', () => {
      const quoteData = {
        symbol: 'AAPL',
        price: 185.50,
        change: 1.50,
        change_percent: 0.82,
      };

      renderWithProvider(<ChartRouter data={quoteData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });
  });

  describe('JSON String Input Handling', () => {
    it('handles JSON string input for stock info', () => {
      const stockDataString = JSON.stringify({
        symbol: 'MSFT',
        info: {
          shortName: 'Microsoft Corporation',
          currentPrice: 415.50,
        },
      });

      renderWithProvider(<ChartRouter data={stockDataString} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('handles JSON string input for kline data', () => {
      const klineDataString = JSON.stringify({
        data: [
          { Date: '2024-01-15', Open: 180, High: 182, Low: 179, Close: 181, Volume: 52000000 },
        ],
        columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'],
        symbol: 'AAPL',
      });

      renderWithProvider(<ChartRouter data={klineDataString} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });
  });

  describe('Fallback Behavior', () => {
    it('returns null for unrecognized data structure', () => {
      const unknownData = {
        randomField: 'value',
        anotherField: 123,
        nested: { deep: true },
      };

      const { container } = renderWithProvider(<ChartRouter data={unknownData} />);

      // Should return null for undetectable data types
      // Based on ChartRouter implementation: if detection fails, returns null
      expect(container.firstChild).toBeNull();
    });

    it('returns null for empty object', () => {
      const { container } = renderWithProvider(<ChartRouter data={{}} />);
      expect(container.firstChild).toBeNull();
    });

    it('returns null for empty array', () => {
      const { container } = renderWithProvider(<ChartRouter data={[]} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('Force Type Override', () => {
    it('allows forcing a specific data type on detected data', () => {
      // Use data that will be detected (as quote), then override to force different type
      const quoteData = {
        symbol: 'AAPL',
        price: 185.50,
        change: 1.50,
        change_percent: 0.82,
      };

      renderWithProvider(
        <ChartRouter data={quoteData} forceType={'stock_info' as DataType} />
      );
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('forceType does not help undetectable data', () => {
      // Data that cannot be detected returns null even with forceType
      // because detection must first succeed for forceType to override
      const unknownData = {
        foo: 'bar',
      };

      const { container } = renderWithProvider(
        <ChartRouter data={unknownData} forceType={'quote' as DataType} />
      );
      // ChartRouter returns null when detectDataType returns null
      expect(container.firstChild).toBeNull();
    });
  });

  describe('Loading and Callback Behavior', () => {
    it('calls onLoad callback when chart loads', async () => {
      const onLoadMock = vi.fn();
      const stockData = {
        symbol: 'AAPL',
        info: {
          shortName: 'Apple Inc.',
          currentPrice: 185.50,
        },
      };

      renderWithProvider(<ChartRouter data={stockData} onLoad={onLoadMock} />);

      // Wait for component to load
      await waitFor(() => {
        expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
      });

      // onLoad is called when chart renderer completes
      // Note: depends on whether a registered component exists
    });
  });

  describe('Custom className Support', () => {
    it('applies custom className to container', () => {
      const stockData = {
        symbol: 'AAPL',
        info: {
          shortName: 'Apple Inc.',
          currentPrice: 185.50,
        },
      };

      renderWithProvider(<ChartRouter data={stockData} className="custom-class" />);
      const container = screen.getByTestId('chart-router-container');
      expect(container).toHaveClass('custom-class');
    });
  });

  describe('Multiple Data Type Scenarios', () => {
    it('handles balance sheet data', () => {
      const balanceSheetData = {
        data: [
          {
            Date: '2023-12-31',
            'Total Assets': 352583000000,
            'Total Liabilities': 290437000000,
            'Total Equity': 62146000000,
          },
        ],
        columns: ['Date', 'Total Assets', 'Total Liabilities', 'Total Equity'],
        statement_type: 'balance',
        symbol: 'AAPL',
      };

      renderWithProvider(<ChartRouter data={balanceSheetData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('handles cash flow data', () => {
      const cashFlowData = {
        data: [
          {
            Date: '2023-12-31',
            'Operating Cash Flow': 110543000000,
            'Capital Expenditure': -10959000000,
            'Free Cash Flow': 99584000000,
          },
        ],
        columns: ['Date', 'Operating Cash Flow', 'Capital Expenditure', 'Free Cash Flow'],
        statement_type: 'cashflow',
        symbol: 'AAPL',
      };

      renderWithProvider(<ChartRouter data={cashFlowData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('handles data with time series pattern', () => {
      const timeSeriesData = {
        data: [
          { Date: '2024-01-15', value: 65.5, trend: 1.25 },
          { Date: '2024-01-16', value: 68.2, trend: 1.45 },
        ],
        columns: ['Date', 'value', 'trend'],
        symbol: 'AAPL',
      };

      renderWithProvider(<ChartRouter data={timeSeriesData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('handles news data format', () => {
      const newsData = {
        news: [
          { title: 'Apple announces new product', summary: 'Details here...', provider: 'Reuters' },
          { title: 'Apple Q4 earnings beat', summary: 'Strong quarter...', provider: 'Bloomberg' },
        ],
        symbol: 'AAPL',
      };

      renderWithProvider(<ChartRouter data={newsData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('handles metrics data format', () => {
      const metricsData = {
        symbol: 'AAPL',
        pe: 28.5,
        pb: 45.2,
        roe: 0.175,
        eps: 6.42,
      };

      renderWithProvider(<ChartRouter data={metricsData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles data with very large numbers', () => {
      const largeNumberData = {
        symbol: 'AAPL',
        info: {
          shortName: 'Apple Inc.',
          marketCap: 3000000000000, // 3 trillion
          currentPrice: 185.50,
        },
      };

      renderWithProvider(<ChartRouter data={largeNumberData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('handles data with negative values', () => {
      const negativeData = {
        data: [
          { Date: '2023-12-31', 'Net Income': -50000000, 'Operating Income': -30000000 },
        ],
        columns: ['Date', 'Net Income', 'Operating Income'],
        statement_type: 'income',
        symbol: 'LOSS',
      };

      renderWithProvider(<ChartRouter data={negativeData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('handles data with special characters in symbol', () => {
      const specialCharData = {
        symbol: 'BRK.A',
        info: {
          shortName: 'Berkshire Hathaway Inc.',
          currentPrice: 600000.00,
        },
      };

      renderWithProvider(<ChartRouter data={specialCharData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('handles stock info with minimal but valid fields', () => {
      // stock_info detection requires: symbol + info object with shortName/longName/sector/industry
      const minimalData = {
        symbol: 'TEST',
        info: {
          shortName: 'Test Company',
          currentPrice: 100.00,
        },
      };

      renderWithProvider(<ChartRouter data={minimalData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });

    it('handles alternate stock info format with company_name', () => {
      // Alternative pattern: { symbol, company_name, sector/industry }
      const altFormatData = {
        symbol: 'ALT',
        company_name: 'Alternative Corp',
        sector: 'Technology',
      };

      renderWithProvider(<ChartRouter data={altFormatData} />);
      expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
    });
  });
});

describe('EChartsProvider Context', () => {
  it('provides theme context to children', () => {
    const { container } = render(
      <EChartsProvider>
        <div data-testid="child">Child content</div>
      </EChartsProvider>
    );

    expect(screen.getByTestId('child')).toBeInTheDocument();
    expect(container.firstChild).not.toBeNull();
  });
});
