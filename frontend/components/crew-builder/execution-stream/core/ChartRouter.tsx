// frontend/components/crew-builder/execution-stream/core/ChartRouter.tsx
/**
 * ChartRouter - Routes detected data types to appropriate visualization components
 *
 * Uses ChartDataDetector to identify data type and renders the correct
 * chart component based on detection result. Missing components gracefully
 * fall back to a JSON preview.
 */
'use client';

import React, { Suspense, useMemo, ComponentType, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { detectDataType, DataType, DetectionResult } from './ChartDataDetector';
import { cardVariants } from './animations';
import {
  getChartComponent,
  ChartComponentProps,
  // Re-export for backward compatibility
  registerChartComponent,
} from './chartRegistry';

// ============ Re-exports for backward compatibility ============

export { registerChartComponent };
export type { ChartComponentProps };

// ============ Loading Placeholder ============

export function ChartLoadingPlaceholder() {
  return (
    <div className="flex items-center justify-center p-8 bg-slate-800/50 rounded-lg border border-slate-700/50">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-slate-400">Loading visualization...</span>
      </div>
    </div>
  );
}

// ============ Fallback Component ============

function FallbackChart({ data, metadata }: ChartComponentProps) {
  return (
    <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
      <div className="text-sm text-slate-400 mb-2">
        {metadata?.title || 'Data Preview'}
      </div>
      <pre className="text-xs text-slate-300 overflow-auto max-h-64">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

// ============ Chart Renderer Component ============

function ChartRenderer({
  type,
  data,
  metadata,
  onLoad,
}: {
  type: DataType;
  data: any;
  metadata?: DetectionResult['metadata'];
  onLoad?: () => void;
}) {
  const [Component, setComponent] = useState<ComponentType<ChartComponentProps> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check registry for component
    const registeredComponent = getChartComponent(type);

    if (registeredComponent) {
      setComponent(() => registeredComponent);
      setLoading(false);
      onLoad?.();
    } else {
      // No component registered yet - use fallback
      setLoading(false);
    }
  }, [type, onLoad]);

  if (loading) {
    return <ChartLoadingPlaceholder />;
  }

  if (!Component) {
    // Graceful fallback for missing components (Phase 2 components not yet created)
    return <FallbackChart data={data} metadata={metadata} />;
  }

  return <Component data={data} metadata={metadata} />;
}

// ============ Props & Types ============

export interface ChartRouterProps {
  /** Raw data payload from tool output or API response */
  data: any;
  /** Optional override for data type detection */
  forceType?: DataType;
  /** Callback when chart component loads */
  onLoad?: () => void;
  /** Additional className for container */
  className?: string;
}

// ============ Chart Router Component ============

export function ChartRouter({
  data,
  forceType,
  onLoad,
  className,
}: ChartRouterProps) {
  // Memoize detection to avoid recalculating on every render
  const detection = useMemo(() => {
    if (data === null || data === undefined) {
      return null;
    }

    const result = detectDataType(data);

    // DEBUG: Log detection results
    if (process.env.NODE_ENV === 'development') {
      console.log('[ChartRouter] Input data:', typeof data, data);
      console.log('[ChartRouter] Detection result:', result);
      if (result) {
        const component = getChartComponent(result.type);
        console.log('[ChartRouter] Component for type', result.type, ':', component ? 'FOUND' : 'NOT FOUND');
      }
    }

    // Override type if forceType is provided
    if (result && forceType) {
      return { ...result, type: forceType };
    }

    return result;
  }, [data, forceType]);

  // Return null for undetectable data
  if (!detection) {
    return null;
  }

  return (
    <motion.div
      data-testid="chart-router-container"
      className={className}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
    >
      <Suspense fallback={<ChartLoadingPlaceholder />}>
        <ChartRenderer
          type={detection.type}
          data={detection.data}
          metadata={detection.metadata}
          onLoad={onLoad}
        />
      </Suspense>
    </motion.div>
  );
}

export default ChartRouter;

// ============ Type Re-exports ============

export type { DataType, DetectionResult };
