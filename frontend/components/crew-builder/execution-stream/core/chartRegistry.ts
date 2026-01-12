/**
 * Chart Registry - Central registration for chart components
 *
 * This module provides the registry Map and registration function.
 * Chart components import from here to register themselves.
 * ChartRouter imports from here to look up components.
 *
 * IMPORTANT: This file should NOT import any chart components directly
 * to avoid circular dependencies. Chart components register themselves
 * when they are imported elsewhere.
 */

import { ComponentType } from 'react';
import { DataType, DetectionResult } from './ChartDataDetector';

// ============ Common Props Type ============

export interface ChartComponentProps {
  data: any;
  metadata?: DetectionResult['metadata'];
}

// ============ Chart Component Registry ============

// Registry of chart components - populated by chart component imports
const chartRegistry = new Map<DataType, ComponentType<ChartComponentProps>>();

/**
 * Register a chart component for a specific data type
 * Used by chart components to register themselves
 */
export function registerChartComponent(
  type: DataType,
  component: ComponentType<ChartComponentProps>
) {
  chartRegistry.set(type, component);
}

/**
 * Get a chart component for a specific data type
 * Returns null if no component is registered
 */
export function getChartComponent(type: DataType): ComponentType<ChartComponentProps> | null {
  return chartRegistry.get(type) || null;
}

/**
 * Check if a component is registered for a data type
 */
export function hasChartComponent(type: DataType): boolean {
  return chartRegistry.has(type);
}
