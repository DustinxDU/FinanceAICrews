/**
 * SkillSelector Integration Tests
 *
 * Tests the three-panel skill selector:
 * - Left: Kind navigation (Presets | Strategies | Skillsets | Capabilities)
 * - Middle: Skill card list (with search, filter)
 * - Right: Detail panel (full skill info)
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SkillSelector } from '../SkillSelector/SkillSelector';
import type { Skill } from '@/types/skills';
import { vi, describe, it, expect, beforeEach } from 'vitest';

// Mock the hooks module
vi.mock('@/hooks/useSkillCatalog', () => ({
  useSkillCatalog: vi.fn(),
}));

// Test data
const mockCatalog: {
  capabilities: Skill[];
  presets: Skill[];
  strategies: Skill[];
  skillsets: Skill[];
} = {
  capabilities: [
    {
      skill_key: 'cap:web_search',
      kind: 'capability',
      capability_id: 'web_search',
      title: 'Web Search',
      description: 'Search the web for information',
      icon: null,
      tags: ['web'],
      is_system: true,
      is_enabled: true,
      is_ready: false,
      blocked_reason: 'Requires serper_dev_tool to be enabled',
      args_schema: null,
      examples: [],
    },
  ],
  presets: [
    {
      skill_key: 'preset:rsi_14',
      kind: 'preset',
      capability_id: 'indicator_calc',
      title: 'RSI(14)',
      description: 'RSI indicator with 14-period lookback',
      icon: null,
      tags: ['Technical'],
      is_system: true,
      is_enabled: true,
      is_ready: true,
      blocked_reason: null,
      args_schema: { period: 14 },
      examples: [],
    },
    {
      skill_key: 'preset:macd',
      kind: 'preset',
      capability_id: 'indicator_calc',
      title: 'MACD',
      description: 'Moving Average Convergence Divergence',
      icon: null,
      tags: ['Trend'],
      is_system: true,
      is_enabled: true,
      is_ready: true,
      blocked_reason: null,
      args_schema: null,
      examples: [],
    },
  ],
  strategies: [
    {
      skill_key: 'strat:momentum',
      kind: 'strategy',
      capability_id: 'strategy_engine',
      title: 'Momentum Strategy',
      description: 'Trade based on momentum signals',
      icon: null,
      tags: ['Trading'],
      is_system: true,
      is_enabled: true,
      is_ready: true,
      blocked_reason: null,
      args_schema: null,
      examples: [],
    },
  ],
  skillsets: [
    {
      skill_key: 'skillset:analysis',
      kind: 'skillset',
      capability_id: null,
      title: 'Analysis Workflow',
      description: 'Multi-step analysis workflow',
      icon: null,
      tags: ['Analysis'],
      is_system: true,
      is_enabled: true,
      is_ready: true,
      blocked_reason: null,
      args_schema: null,
      examples: [],
    },
  ],
};

// Default mock return values
const defaultCatalogReturn = {
  catalog: mockCatalog,
  allSkills: [
    ...mockCatalog.capabilities,
    ...mockCatalog.presets,
    ...mockCatalog.strategies,
    ...mockCatalog.skillsets,
  ],
  isLoading: false,
  isError: false,
  error: null,
  mutate: vi.fn(),
};

// Import after mock is defined
import { useSkillCatalog } from '@/hooks/useSkillCatalog';

describe('SkillSelector Integration', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Set up default mock implementation
    (useSkillCatalog as ReturnType<typeof vi.fn>).mockReturnValue(defaultCatalogReturn);
  });

  describe('Initial Render', () => {
    it('should render the three-panel layout', () => {
      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      // Left panel - Kind navigation
      expect(screen.getByText('Skill Types')).toBeInTheDocument();

      // Middle panel - Search input
      expect(screen.getByPlaceholderText('Search skills...')).toBeInTheDocument();

      // Right panel - Detail placeholder
      expect(screen.getByText('Select a skill to view details')).toBeInTheDocument();
    });

    it('should show loading state while catalog is loading', () => {
      (useSkillCatalog as ReturnType<typeof vi.fn>).mockReturnValue({
        ...defaultCatalogReturn,
        isLoading: true,
      });

      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Loading skill catalog...')).toBeInTheDocument();
    });

    it('should show error state when catalog fails to load', () => {
      (useSkillCatalog as ReturnType<typeof vi.fn>).mockReturnValue({
        ...defaultCatalogReturn,
        isLoading: false,
        isError: true,
      });

      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Failed to load')).toBeInTheDocument();
    });
  });

  describe('Kind Navigation', () => {
    it('should display 4 Kind categories', () => {
      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('Presets')).toBeInTheDocument();
      expect(screen.getByText('Skillsets')).toBeInTheDocument();
      expect(screen.getByText('Strategies')).toBeInTheDocument();
      expect(screen.getByText('Capabilities')).toBeInTheDocument();
    });

    it('should show kind navigation buttons', () => {
      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

        expect(screen.getByText('Presets')).toBeInTheDocument();
        expect(screen.getByText('Skillsets')).toBeInTheDocument();
        expect(screen.getByText('Strategies')).toBeInTheDocument();
        expect(screen.getByText('Capabilities')).toBeInTheDocument();
    });

    it('should switch active kind when clicking navigation', () => {
      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      // Find and click Capabilities button
      const buttons = screen.getAllByRole('button');
      const capabilitiesButton = buttons.find(btn => btn.textContent?.includes('Capabilities'));

      expect(capabilitiesButton).toBeInTheDocument();
      fireEvent.click(capabilitiesButton!);

      // Now clicking on capabilities should show capabilities list
      // The Web Search capability should be visible
      expect(screen.getByText('Web Search')).toBeInTheDocument();
    });
  });

  describe('Search Function', () => {
    it('should filter skills when entering search term', () => {
      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      // Initially all presets visible
      expect(screen.getByText('RSI(14)')).toBeInTheDocument();
      expect(screen.getByText('MACD')).toBeInTheDocument();

      // Search for RSI
      const searchInput = screen.getByPlaceholderText('Search skills...');
      fireEvent.change(searchInput, { target: { value: 'RSI' } });

      // Only RSI should be visible
      expect(screen.getByText('RSI(14)')).toBeInTheDocument();
      expect(screen.queryByText('MACD')).not.toBeInTheDocument();
    });

    it('should filter by description when searching', () => {
      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search skills...');
      fireEvent.change(searchInput, { target: { value: 'Convergence' } });

      expect(screen.getByText('MACD')).toBeInTheDocument();
    });

    it('should show empty state when no matches found', () => {
      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search skills...');
      fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

      expect(screen.getByText('No matching skills found')).toBeInTheDocument();
    });

    it('should show clear search button when no matches found', () => {
      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search skills...');
      fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

      expect(screen.getByText('Clear search')).toBeInTheDocument();
    });

    it('should clear search when clicking clear button', () => {
      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search skills...');
      fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

      // Click clear
      fireEvent.click(screen.getByText('Clear search'));

      // All presets should be visible again
      expect(screen.getByText('RSI(14)')).toBeInTheDocument();
      expect(screen.getByText('MACD')).toBeInTheDocument();
    });
  });

  describe('Skill Selection', () => {
    it('should render skill cards with toggle buttons', async () => {
      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      // Wait for content to render
      await waitFor(() => {
        expect(screen.getByText('RSI(14)')).toBeInTheDocument();
      });

      // Find toggle button (button with check icon - appears as button element)
      const toggleButtons = screen.getAllByRole('button');
      // Navigation buttons (4) + skill card toggles (2) = 6 buttons total
      expect(toggleButtons.length).toBeGreaterThanOrEqual(6);
    });

    it('should show selected state for preselected skills', async () => {
      render(
        <SkillSelector
          selectedSkillKeys={['preset:rsi_14']}
          onChange={mockOnChange}
        />
      );

      // Wait for content and verify RSI is displayed
      await waitFor(() => {
        expect(screen.getByText('RSI(14)')).toBeInTheDocument();
      });
    });
  });

  describe('Detail Panel', () => {
    it('should show placeholder when no skill selected', async () => {
      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      // Wait for content to render
      await waitFor(() => {
        expect(screen.getByText('Select a skill to view details')).toBeInTheDocument();
      });
    });

    // Note: Detail panel opening is tested at the SkillCardEnhanced level
    // The SkillSelector just passes through to SkillDetailPanel
  });

  describe('Empty States', () => {
    it('should show empty state when kind has no skills', () => {
      (useSkillCatalog as ReturnType<typeof vi.fn>).mockReturnValue({
        catalog: {
          capabilities: [],
          presets: [],
          strategies: [],
          skillsets: [],
        },
        allSkills: [],
        isLoading: false,
        isError: false,
        error: null,
        mutate: vi.fn(),
      });

      render(
        <SkillSelector
          selectedSkillKeys={[]}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('No matching skills found')).toBeInTheDocument();
    });
  });
});
