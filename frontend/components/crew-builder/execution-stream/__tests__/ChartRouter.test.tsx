import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { ChartRouter } from '../core/ChartRouter';

describe('ChartRouter', () => {
  it('renders nothing for null data', () => {
    const { container } = render(<ChartRouter data={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders stock_info card for stock info data', () => {
    const data = {
      symbol: 'AAPL',
      info: {
        shortName: 'Apple Inc.',
        sector: 'Technology',
        currentPrice: 180.5,
      },
    };
    render(<ChartRouter data={data} />);
    expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
  });

  it('renders quote card for quote data', () => {
    const data = {
      symbol: 'AAPL',
      price: 180.5,
      change: 2.5,
      change_percent: 1.4,
    };
    render(<ChartRouter data={data} />);
    expect(screen.getByTestId('chart-router-container')).toBeInTheDocument();
  });
});
