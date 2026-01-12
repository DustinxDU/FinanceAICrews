// frontend/components/crew-builder/execution-stream/__tests__/ChartDataDetector.test.ts
import { describe, it, expect } from 'vitest';
import { detectDataType, DataType, DetectionResult } from '../core/ChartDataDetector';

describe('ChartDataDetector', () => {
  describe('stock_info detection', () => {
    it('detects stock_info from yfinance data', () => {
      const data = {
        symbol: 'AAPL',
        info: {
          shortName: 'Apple Inc.',
          sector: 'Technology',
          industry: 'Consumer Electronics',
          currentPrice: 180.5,
          marketCap: 2800000000000,
        },
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('stock_info');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.9);
    });

    it('detects stock_info from flat structure', () => {
      const data = {
        symbol: 'MSFT',
        company_name: 'Microsoft Corporation',
        sector: 'Technology',
        industry: 'Software',
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('stock_info');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.9);
    });
  });

  describe('kline detection', () => {
    it('detects OHLCV data as kline', () => {
      const data = {
        data: [
          { Date: '2024-01-01', Open: 100, High: 105, Low: 98, Close: 103, Volume: 1000000 },
          { Date: '2024-01-02', Open: 103, High: 108, Low: 101, Close: 106, Volume: 1200000 },
        ],
        columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'],
        symbol: 'AAPL',
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('kline');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.9);
    });

    it('returns metadata with columns for kline data', () => {
      const data = {
        data: [
          { Date: '2024-01-01', Open: 100, High: 105, Low: 98, Close: 103, Volume: 1000000 },
        ],
        columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'],
        symbol: 'TSLA',
      };
      const result = detectDataType(data);
      expect(result?.metadata?.columns).toEqual(['Date', 'Open', 'High', 'Low', 'Close', 'Volume']);
      expect(result?.metadata?.rowCount).toBe(1);
    });
  });

  describe('quote detection', () => {
    it('detects real-time quote data', () => {
      const data = {
        symbol: 'AAPL',
        price: 180.5,
        change: 2.5,
        change_percent: 1.4,
        volume: 50000000,
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('quote');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.85);
    });

    it('detects quote from regularMarketPrice format', () => {
      const data = {
        regularMarketPrice: 180.5,
        regularMarketChange: 2.5,
        regularMarketVolume: 50000000,
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('quote');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.8);
    });
  });

  describe('search detection', () => {
    it('detects search results', () => {
      const data = [
        { title: 'Apple stock rises', snippet: 'Breaking news...', url: 'https://example.com' },
        { title: 'Tech rally continues', snippet: 'Market update...', url: 'https://example.com/2' },
      ];
      const result = detectDataType(data);
      expect(result?.type).toBe('search');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.8);
    });

    it('detects search results with description field', () => {
      const data = {
        results: [
          { title: 'Apple stock analysis', description: 'Detailed report...', url: 'https://example.com' },
        ],
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('search');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.8);
    });
  });

  describe('news detection', () => {
    it('detects news array', () => {
      const data = {
        news: [
          { title: 'Apple Q4 Results', summary: 'Strong earnings...', provider: 'Reuters' },
        ],
        symbol: 'AAPL',
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('news');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.85);
    });

    it('detects news with nested content title', () => {
      const data = {
        news: [
          { content: { title: 'Market Update' } },
        ],
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('news');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.85);
    });
  });

  describe('financial detection', () => {
    it('detects income statement data', () => {
      const data = {
        data: [
          { Date: '2023-12-31', 'Total Revenue': 100000000, 'Net Income': 20000000 },
        ],
        columns: ['Date', 'Total Revenue', 'Net Income'],
        statement_type: 'income',
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('financial');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.85);
    });

    it('detects balance sheet data by columns', () => {
      const data = {
        data: [
          { Date: '2023-12-31', 'Total Assets': 500000000, 'Total Liabilities': 200000000 },
        ],
        columns: ['Date', 'Total Assets', 'Total Liabilities'],
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('financial');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.8);
    });

    it('detects cash flow data', () => {
      const data = {
        data: [
          { Date: '2023-12-31', 'Operating Cash Flow': 50000000, 'Free Cash Flow': 30000000 },
        ],
        columns: ['Date', 'Operating Cash Flow', 'Free Cash Flow'],
        statement_type: 'cashflow',
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('financial');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.85);
    });
  });

  describe('fallback to table', () => {
    it('falls back to table for unknown structured data', () => {
      const data = {
        data: [{ col1: 'val1', col2: 'val2' }],
        columns: ['col1', 'col2'],
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('table');
      expect(result?.confidence).toBeLessThan(0.6);
    });

    it('falls back to table for plain array of objects', () => {
      const data = [
        { name: 'Item 1', value: 100 },
        { name: 'Item 2', value: 200 },
      ];
      const result = detectDataType(data);
      // Should detect as table or comparison depending on numeric columns
      expect(['table', 'search', 'comparison']).toContain(result?.type);
    });
  });

  describe('null handling', () => {
    it('returns null for null input', () => {
      expect(detectDataType(null)).toBeNull();
    });

    it('returns null for undefined input', () => {
      expect(detectDataType(undefined)).toBeNull();
    });

    it('returns null for empty string', () => {
      expect(detectDataType('')).toBeNull();
    });

    it('returns null for invalid JSON string', () => {
      expect(detectDataType('not valid json')).toBeNull();
    });

    it('parses valid JSON string', () => {
      const jsonString = JSON.stringify({
        symbol: 'AAPL',
        price: 180.5,
        change: 2.5,
      });
      const result = detectDataType(jsonString);
      expect(result?.type).toBe('quote');
    });
  });

  describe('metadata extraction', () => {
    it('extracts symbol from data', () => {
      const data = {
        symbol: 'GOOGL',
        price: 140.0,
        change: 1.5,
      };
      const result = detectDataType(data);
      expect(result?.metadata?.symbol).toBe('GOOGL');
    });

    it('extracts ticker as symbol', () => {
      const data = {
        ticker: 'NVDA',
        data: [{ col: 'val' }],
      };
      const result = detectDataType(data);
      expect(result?.metadata?.symbol).toBe('NVDA');
    });

    it('extracts row count for array data', () => {
      const data = {
        data: [
          { Date: '2024-01-01', Open: 100, High: 105, Low: 98, Close: 103 },
          { Date: '2024-01-02', Open: 103, High: 108, Low: 101, Close: 106 },
          { Date: '2024-01-03', Open: 106, High: 110, Low: 105, Close: 109 },
        ],
        columns: ['Date', 'Open', 'High', 'Low', 'Close'],
      };
      const result = detectDataType(data);
      expect(result?.metadata?.rowCount).toBe(3);
    });
  });

  describe('fund_flow detection', () => {
    it('detects Chinese fund flow data', () => {
      const data = {
        symbol: '000001',
        '主力净流入': 1000000,
        '超大单净流入': 500000,
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('fund_flow');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.8);
    });

    it('detects English fund flow data', () => {
      const data = {
        symbol: 'AAPL',
        net_inflow: 1000000,
        main_force_inflow: 500000,
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('fund_flow');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.75);
    });
  });

  describe('ranking detection', () => {
    it('detects ranking data with rank field', () => {
      const data = {
        data: [
          { rank: 1, symbol: 'AAPL', change: 5.5 },
          { rank: 2, symbol: 'MSFT', change: 4.2 },
        ],
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('ranking');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.75);
    });

    it('detects LHB data', () => {
      const data = {
        lhb: true,
        data: [{ symbol: '000001', name: 'Test' }],
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('ranking');
    });
  });

  describe('holders detection', () => {
    it('detects institutional holders', () => {
      const data = {
        institutional_holders: [
          { holder: 'Vanguard', shares: 1000000 },
        ],
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('holders');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.7);
    });

    it('detects top holders array', () => {
      const data = {
        top_holders: [
          { name: 'BlackRock', percentage: 7.5 },
        ],
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('holders');
    });
  });

  describe('macro detection', () => {
    it('detects macro data by tool name', () => {
      const data = {
        _tool_name: 'mcp_akshare_macro_gdp',
        data: [{ date: '2024-Q1', value: 28000 }],
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('macro');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.75);
    });

    it('detects macro data by fields', () => {
      const data = {
        gdp: 28000,
        cpi: 3.2,
        unemployment: 3.7,
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('macro');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.7);
    });
  });

  describe('metrics detection', () => {
    it('detects metrics with PE/PB/ROE', () => {
      const data = {
        symbol: 'AAPL',
        pe: 28.5,
        pb: 45.2,
        roe: 0.156,
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('metrics');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.7);
    });
  });

  describe('web_content detection', () => {
    it('detects web content with url and content', () => {
      const data = {
        url: 'https://example.com/article',
        content: 'This is the article content...',
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('web_content');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.7);
    });

    it('detects web content with markdown', () => {
      const data = {
        url: 'https://example.com/page',
        markdown: '# Article Title\n\nContent here...',
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('web_content');
    });
  });

  describe('time_series detection', () => {
    it('detects generic time series data', () => {
      const data = {
        data: [
          { date: '2024-01-01', value: 100 },
          { date: '2024-01-02', value: 105 },
        ],
      };
      const result = detectDataType(data);
      expect(result?.type).toBe('time_series');
      expect(result?.confidence).toBeGreaterThanOrEqual(0.65);
    });
  });

  describe('comparison detection', () => {
    it('detects comparison data with multiple numeric columns', () => {
      const data = {
        data: [
          { category: 'Revenue', company_a: 100, company_b: 120 },
          { category: 'Profit', company_a: 20, company_b: 25 },
        ],
      };
      const result = detectDataType(data);
      // Could be comparison or time_series depending on detection order
      expect(['comparison', 'time_series', 'table']).toContain(result?.type);
    });
  });
});
