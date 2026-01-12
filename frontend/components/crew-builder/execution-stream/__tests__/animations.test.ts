// frontend/components/crew-builder/execution-stream/__tests__/animations.test.ts
import { describe, it, expect } from 'vitest';
import {
  cardVariants,
  chartAnimation,
  numberAnimation,
  progressVariants,
  staggerChildren,
} from '../core/animations';

describe('animations', () => {
  it('cardVariants has hidden and visible states', () => {
    expect(cardVariants.hidden).toBeDefined();
    expect(cardVariants.visible).toBeDefined();
    // Type assertion needed due to Framer Motion's complex Variant types
    const hidden = cardVariants.hidden as { opacity: number };
    const visible = cardVariants.visible as { opacity: number };
    expect(hidden.opacity).toBe(0);
    expect(visible.opacity).toBe(1);
  });

  it('chartAnimation has duration and easing', () => {
    expect(chartAnimation.duration).toBeGreaterThan(0);
    expect(chartAnimation.easing).toBeDefined();
  });

  it('progressVariants returns correct width for percent', () => {
    // progressVariants.visible is a function that takes percent as custom prop
    const visibleFn = progressVariants.visible as (percent: number) => { width: string };
    const result = visibleFn(75);
    expect(result.width).toBe('75%');
  });

  it('staggerChildren provides proper delay', () => {
    const visible = staggerChildren.visible as { transition: { staggerChildren: number } };
    expect(visible.transition.staggerChildren).toBeGreaterThan(0);
  });

  it('numberAnimation has duration and ease', () => {
    expect(numberAnimation.duration).toBeGreaterThan(0);
    expect(numberAnimation.ease).toBeDefined();
  });
});
