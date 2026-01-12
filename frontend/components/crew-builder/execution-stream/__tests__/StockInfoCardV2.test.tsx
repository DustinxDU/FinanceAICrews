import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { StockInfoCardV2 } from '../cards/StockInfoCardV2';

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

const mockData = {
  symbol: 'AAPL',
  info: {
    shortName: 'Apple Inc.',
    longName: 'Apple Inc.',
    sector: 'Technology',
    industry: 'Consumer Electronics',
    currentPrice: 180.50,
    previousClose: 178.00,
    fiftyTwoWeekLow: 140.25,
    fiftyTwoWeekHigh: 199.62,
    marketCap: 2800000000000, // 2.8T
    forwardPE: 28.5,
    priceToBook: 45.2,
    revenueGrowth: 0.085, // 8.5%
    longBusinessSummary: 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.',
  },
};

describe('StockInfoCardV2', () => {
  it('renders company name and symbol', () => {
    render(<StockInfoCardV2 data={mockData} />);

    expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
  });

  it('renders current price with change', () => {
    render(<StockInfoCardV2 data={mockData} />);

    // Current price
    expect(screen.getByText('$180.50')).toBeInTheDocument();

    // Change: 180.50 - 178.00 = +2.50 (+1.40%)
    expect(screen.getByText(/\+\$2\.50/)).toBeInTheDocument();
    expect(screen.getByText(/\+1\.40%/)).toBeInTheDocument();
  });

  it('renders sector and industry', () => {
    render(<StockInfoCardV2 data={mockData} />);

    expect(screen.getByText('Technology')).toBeInTheDocument();
    expect(screen.getByText('Consumer Electronics')).toBeInTheDocument();
  });

  it('renders 52-week range', () => {
    render(<StockInfoCardV2 data={mockData} />);

    expect(screen.getByText('140.25')).toBeInTheDocument();
    expect(screen.getByText('199.62')).toBeInTheDocument();
  });

  it('renders key metrics', () => {
    render(<StockInfoCardV2 data={mockData} />);

    // Market Cap: 2.8T
    expect(screen.getByText('2.8T')).toBeInTheDocument();

    // P/E (Fwd): 28.5
    expect(screen.getByText('28.50')).toBeInTheDocument();

    // P/B: 45.2
    expect(screen.getByText('45.20')).toBeInTheDocument();

    // Rev Growth: 8.5%
    expect(screen.getByText('8.50%')).toBeInTheDocument();
  });

  it('renders collapsible about section', () => {
    render(<StockInfoCardV2 data={mockData} />);

    // Should have an About section that can be toggled
    const aboutButton = screen.getByRole('button', { name: /about/i });
    expect(aboutButton).toBeInTheDocument();

    // Click to expand
    fireEvent.click(aboutButton);

    // Should show business summary
    expect(screen.getByText(/Apple Inc. designs, manufactures/)).toBeInTheDocument();
  });

  it('handles negative price change (red indicator)', () => {
    const negativeData = {
      ...mockData,
      info: {
        ...mockData.info,
        currentPrice: 175.00,
        previousClose: 180.00,
      },
    };

    render(<StockInfoCardV2 data={negativeData} />);

    // Change: 175.00 - 180.00 = -5.00 (-2.78%)
    expect(screen.getByText(/-\$5\.00/)).toBeInTheDocument();
    expect(screen.getByText(/-2\.78%/)).toBeInTheDocument();
  });

  it('handles missing optional fields gracefully', () => {
    const minimalData = {
      symbol: 'TSLA',
      info: {
        shortName: 'Tesla Inc.',
        currentPrice: 250.00,
      },
    };

    render(<StockInfoCardV2 data={minimalData} />);

    expect(screen.getByText('Tesla Inc.')).toBeInTheDocument();
    expect(screen.getByText('TSLA')).toBeInTheDocument();
    expect(screen.getByText('$250.00')).toBeInTheDocument();
  });
});
