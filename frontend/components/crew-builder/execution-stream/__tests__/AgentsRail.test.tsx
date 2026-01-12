import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentsRail } from '../AgentsRail';
import { AgentState } from '../agentState';

vi.mock('next-intl', () => ({
  useTranslations: () => (_key: string) => _key,
}));

const mockAgents: AgentState[] = [
  {
    agentName: 'Market Data Researcher',
    status: 'running',
    currentActionLabel: 'Calling mcp_yfinance_stock_history',
    lastToolName: 'mcp_yfinance_stock_history',
    lastToolDurationMs: 1234,
    lastSeenAt: '2025-01-09T10:00:00Z'
  },
  {
    agentName: 'Technical Analyst',
    status: 'idle',
    currentActionLabel: 'Waiting',
    lastSeenAt: ''
  },
  {
    agentName: 'Sentiment Analyst',
    status: 'done',
    currentActionLabel: 'Completed',
    lastToolName: 'mcp_akshare_news_sentiment',
    lastToolDurationMs: 5678,
    lastSeenAt: '2025-01-09T09:45:00Z'
  }
];

describe('AgentsRail', () => {
  const defaultProps = {
    agents: mockAgents,
    selectedAgentName: null as string | null,
    activeAgentName: 'Market Data Researcher',
    followActive: true,
    onSelect: vi.fn(),
    onToggleFollow: vi.fn()
  };

  it('should render all agents', () => {
    render(<AgentsRail {...defaultProps} />);

    expect(screen.getByText('Market Data Researcher')).toBeInTheDocument();
    expect(screen.getByText('Technical Analyst')).toBeInTheDocument();
    expect(screen.getByText('Sentiment Analyst')).toBeInTheDocument();
  });

  it('should show status indicators', () => {
    render(<AgentsRail {...defaultProps} />);

    // Market Data Researcher is running (green pulse)
    const runningIndicator = screen.getAllByRole('status')[0];
    expect(runningIndicator).toHaveClass('bg-green-500');
  });

  it('should call onSelect when agent is clicked', () => {
    render(<AgentsRail {...defaultProps} />);

    fireEvent.click(screen.getByText('Market Data Researcher'));
    expect(defaultProps.onSelect).toHaveBeenCalledWith('Market Data Researcher');
  });

  it('should highlight selected agent', () => {
    render(<AgentsRail {...defaultProps} selectedAgentName="Market Data Researcher" />);

    const agentButton = screen.getByText('Market Data Researcher').closest('button');
    expect(agentButton).toHaveClass('bg-cyan-500/20');
  });

  it('should show follow toggle button', () => {
    render(<AgentsRail {...defaultProps} followActive={true} />);
    expect(screen.getByText(/follow/i)).toBeInTheDocument();

    render(<AgentsRail {...defaultProps} followActive={false} />);
    expect(screen.getByText(/pin/i)).toBeInTheDocument();
  });
});
