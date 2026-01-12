import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SkillCardEnhanced } from '../SkillCardEnhanced';
import type { Skill } from '@/types/skills';
import { vi, describe, it, expect } from 'vitest';

const mockSkillReady: Skill = {
  skill_key: 'preset:rsi_14',
  kind: 'preset',
  capability_id: 'indicator_calc',
  title: 'RSI Indicator (14)',
  description: 'Relative Strength Index for identifying overbought/oversold',
  icon: null,
  tags: ['Technical', 'Momentum'],
  is_system: true,
  is_enabled: true,
  is_ready: true,
  blocked_reason: null,
  args_schema: { period: 14 },
  examples: [],
};

const mockSkillBlocked: Skill = {
  ...mockSkillReady,
  skill_key: 'cap:web_search',
  kind: 'capability',
  title: 'Web Search',
  is_ready: false,
  blocked_reason: 'Requires serper_dev_tool Provider to be enabled',
};

describe('SkillCardEnhanced', () => {
  describe('Status Indicator', () => {
    it('should show Ready status when ready', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={false}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.getByText('Available')).toBeInTheDocument();
      expect(screen.queryByText('Locked')).not.toBeInTheDocument();
    });

    it('should show Locked status when not ready', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillBlocked}
          isSelected={false}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.getByText('Locked')).toBeInTheDocument();
    });

    it('should show red dot indicator when locked', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillBlocked}
          isSelected={false}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.getByTestId('status-indicator')).toHaveClass('bg-red-400');
    });
  });

  describe('Recommendation Tag', () => {
    it('should show recommendation tag when isRecommended=true', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={false}
          isRecommended={true}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.getByText('Recommended')).toBeInTheDocument();
    });

    it('should not show recommendation tag when isRecommended=false', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={false}
          isRecommended={false}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.queryByText('Recommended')).not.toBeInTheDocument();
    });
  });

  describe('Selection State', () => {
    it('should show selected styling when isSelected=true', () => {
      const { container } = render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={true}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      const card = container.firstChild as HTMLElement;
      expect(card).toHaveClass('bg-blue-900/20');
      expect(card).toHaveClass('border-blue-500');
    });

    it('should not show selected styling when isSelected=false', () => {
      const { container } = render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={false}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      const card = container.firstChild as HTMLElement;
      expect(card).not.toHaveClass('bg-blue-900/20');
    });

    it('should call onToggle when clicking toggle button', () => {
      const onToggle = vi.fn();
      render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={false}
          onToggle={onToggle}
          onSelect={vi.fn()}
        />
      );

      const toggleButton = screen.getByRole('button');
      fireEvent.click(toggleButton);

      expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it('should stop propagation on toggle button click', () => {
      const onToggle = vi.fn();
      render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={false}
          onToggle={onToggle}
          onSelect={vi.fn()}
        />
      );

      const toggleButton = screen.getByRole('button');

      // Click on button should trigger toggle
      fireEvent.click(toggleButton);
      expect(onToggle).toHaveBeenCalledTimes(1);
    });
  });

  describe('Rendering', () => {
    it('should render skill title', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={false}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.getByText('RSI Indicator (14)')).toBeInTheDocument();
    });

    it('should render skill key', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={false}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.getByText('preset:rsi_14')).toBeInTheDocument();
    });

    it('should render description', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={false}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.getByText(/Relative Strength Index/)).toBeInTheDocument();
    });

    it('should render tags', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={false}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.getByText('Technical')).toBeInTheDocument();
      expect(screen.getByText('Momentum')).toBeInTheDocument();
    });

    it('should render toggle button', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={false}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('should show checkmark when selected', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={true}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.getByRole('button')).toContainHTML('<svg');
    });
  });

  describe('Skill Kind Styling', () => {
    it('should apply preset styling with purple icon', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillReady}
          isSelected={false}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.getByTestId('kind-icon')).toBeInTheDocument();
    });

    it('should apply capability styling with database icon', () => {
      render(
        <SkillCardEnhanced
          skill={mockSkillBlocked}
          isSelected={false}
          onToggle={vi.fn()}
          onSelect={vi.fn()}
        />
      );

      expect(screen.getByTestId('kind-icon')).toBeInTheDocument();
    });
  });
});
