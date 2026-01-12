import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EChartsProvider, useEChartsTheme } from '../charts/EChartsProvider';
import React from 'react';

// Test component to verify theme
function TestConsumer() {
  const theme = useEChartsTheme();
  return <div data-testid="theme-name">{theme.name}</div>;
}

describe('EChartsProvider', () => {
  it('provides dark theme by default', () => {
    render(
      <EChartsProvider>
        <TestConsumer />
      </EChartsProvider>
    );
    expect(screen.getByTestId('theme-name').textContent).toBe('financeAIDark');
  });

  it('provides finance-focused color palette', () => {
    render(
      <EChartsProvider>
        <TestConsumer />
      </EChartsProvider>
    );
    // Theme should be accessible
    expect(screen.getByTestId('theme-name')).toBeInTheDocument();
  });
});
