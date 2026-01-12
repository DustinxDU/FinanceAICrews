import { Variants } from 'framer-motion';

/**
 * Card entrance animation variants
 * Used for chart cards, info cards, etc.
 */
export const cardVariants: Variants = {
  hidden: {
    opacity: 0,
    y: 20,
    scale: 0.95,
  },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.4,
      ease: [0.25, 0.46, 0.45, 0.94], // easeOutQuad
    },
  },
  exit: {
    opacity: 0,
    y: -10,
    scale: 0.98,
    transition: {
      duration: 0.2,
    },
  },
};

/**
 * ECharts animation configuration
 * Used in ECharts option.animation
 */
export const chartAnimation = {
  duration: 800,
  easing: 'cubicOut',
  delay: (idx: number) => idx * 50, // Stagger data points
};

/**
 * Number scrolling animation
 * For animated counters
 */
export const numberAnimation = {
  duration: 1.2,
  ease: 'easeOut',
};

/**
 * Progress bar animation variants
 */
export const progressVariants: Variants = {
  hidden: { width: 0 },
  visible: (percent: number) => ({
    width: `${percent}%`,
    transition: {
      duration: 0.8,
      ease: 'easeOut',
    },
  }),
};

/**
 * Stagger children animation for lists
 */
export const staggerChildren: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
};

/**
 * Fade in animation
 */
export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.3 },
  },
};

/**
 * Slide up animation
 */
export const slideUp: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: 'easeOut' },
  },
};

/**
 * Scale in animation
 */
export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.3, ease: 'easeOut' },
  },
};

/**
 * Animation timing sequence for card components
 * 0ms     Card fade in + slide up
 * 200ms   Title appears
 * 400ms   Price/number scrolling starts
 * 600ms   Progress bar/chart expands
 * 800ms   Metrics grid entrance
 */
export const animationTimeline = {
  cardEntrance: 0,
  titleAppear: 200,
  numberScroll: 400,
  chartExpand: 600,
  metricsEntrance: 800,
};
