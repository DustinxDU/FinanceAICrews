'use client';

/**
 * InfographicReport Component
 *
 * Renders beautiful infographic reports using AntV Infographic engine.
 * Designed for displaying analysis results in a visually appealing format.
 *
 * @see https://github.com/antvis/Infographic
 */

import React, { useEffect, useRef, useState } from 'react';
import { Download, Maximize2, Minimize2, Loader2, RefreshCw } from 'lucide-react';

// Type definitions for @antv/infographic
interface InfographicOptions {
  container: HTMLElement;
  width?: number;
  height?: number;
  editable?: boolean;
  theme?: string;
}

interface InfographicInstance {
  render: (dsl: string) => void;
  destroy: () => void;
  exportSVG?: () => string;
  exportPNG?: () => Promise<Blob>;
}

interface InfographicReportProps {
  /** DSL string to render */
  dsl: string;
  /** Report title */
  title?: string;
  /** Initial width */
  width?: number;
  /** Initial height */
  height?: number;
  /** Enable built-in editor */
  editable?: boolean;
  /** Theme: 'default' | 'hand-drawn' | 'gradient' */
  theme?: string;
  /** Class name for container */
  className?: string;
  /** Callback when render completes */
  onRenderComplete?: () => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export const InfographicReport = ({
  dsl,
  title,
  width = 600,
  height = 400,
  editable = false,
  theme = 'default',
  className = '',
  onRenderComplete,
  onError,
}: InfographicReportProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLibLoaded, setIsLibLoaded] = useState(false);

  // Dynamically import the library (client-side only)
  useEffect(() => {
    let mounted = true;

    const loadLibrary = async () => {
      try {
        // Dynamic import to avoid SSR issues
        const { Infographic } = await import('@antv/infographic');
        if (mounted) {
          (window as any).__InfographicClass = Infographic;
          setIsLibLoaded(true);
        }
      } catch (err) {
        console.error('Failed to load @antv/infographic:', err);
        if (mounted) {
          setError('Failed to load infographic library');
          onError?.(err as Error);
        }
      }
    };

    loadLibrary();
    return () => { mounted = false; };
  }, []);

  // Initialize and render chart
  useEffect(() => {
    if (!isLibLoaded || !containerRef.current || !dsl) return;

    const InfographicClass = (window as any).__InfographicClass;
    if (!InfographicClass) return;

    setIsLoading(true);
    setError(null);

    try {
      // Destroy previous instance
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }

      // Create new instance with container and basic options
      const instance = new InfographicClass({
        container: containerRef.current,
        width: isFullscreen ? window.innerWidth - 100 : width,
        height: isFullscreen ? window.innerHeight - 200 : height,
        editable,
        theme,
      }) as any;

      // Set up event listeners for errors and warnings
      instance.on('error', (err: Error) => {
        console.error('Infographic error:', err);
        setError(err.message || 'Unknown error');
        setIsLoading(false);
        onError?.(err);
      });

      instance.on('warning', (warnings: any[]) => {
        console.warn('Infographic warnings:', warnings);
      });

      chartRef.current = instance;

      // Render with DSL string (not options object)
      instance.render(dsl);
      setIsLoading(false);
      onRenderComplete?.();
    } catch (err) {
      console.error('Failed to render infographic:', err);
      setError((err as Error).message);
      setIsLoading(false);
      onError?.(err as Error);
    }

    // Cleanup
    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [dsl, isLibLoaded, width, height, editable, theme, isFullscreen, onError, onRenderComplete]);

  // Handle fullscreen resize
  useEffect(() => {
    if (!isFullscreen || !chartRef.current || !dsl) return;

    const handleResize = () => {
      if (chartRef.current && containerRef.current) {
        chartRef.current.destroy();
        const InfographicClass = (window as any).__InfographicClass;
        if (InfographicClass) {
          const instance = new InfographicClass({
            container: containerRef.current,
            width: window.innerWidth - 100,
            height: window.innerHeight - 200,
            editable,
            theme,
          }) as any;

          instance.on('error', () => {}); // Suppress errors on resize
          chartRef.current = instance;
          instance.render(dsl);
        }
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isFullscreen, dsl, editable, theme]);

  // Export handlers
  const handleExportSVG = async () => {
    if (!chartRef.current) return;

    try {
      // Use toDataURL method for SVG export
      const dataUrl = await chartRef.current.toDataURL({ type: 'svg' });
      const svgString = dataUrl.split(',')[1];
      const blob = new Blob([atob(svgString)], { type: 'image/svg+xml' });
      downloadBlob(blob, `${title || 'report'}.svg`);
    } catch (err) {
      // Fallback: get SVG from container
      const svg = containerRef.current?.querySelector('svg');
      if (svg) {
        const svgData = new XMLSerializer().serializeToString(svg);
        const blob = new Blob([svgData], { type: 'image/svg+xml' });
        downloadBlob(blob, `${title || 'report'}.svg`);
      }
    }
  };

  const handleExportPNG = async () => {
    if (!chartRef.current) return;

    try {
      // Use toDataURL method for PNG export
      const dataUrl = await chartRef.current.toDataURL({ type: 'png' });
      const pngData = dataUrl.split(',')[1];
      const blob = new Blob([atob(pngData)], { type: 'image/png' });
      downloadBlob(blob, `${title || 'report'}.png`);
    } catch (err) {
      // Fallback: use canvas to convert SVG to PNG
      const svg = containerRef.current?.querySelector('svg');
      if (!svg) return;

      const svgData = new XMLSerializer().serializeToString(svg);
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();

      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx?.drawImage(img, 0, 0);
        canvas.toBlob((blob) => {
          if (blob) {
            downloadBlob(blob, `${title || 'report'}.png`);
          }
        }, 'image/png');
      };

      img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
    }
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleRefresh = () => {
    if (chartRef.current && dsl) {
      chartRef.current.render(dsl);
    }
  };

  // Fullscreen container wrapper
  const containerClass = isFullscreen
    ? 'fixed inset-0 z-50 bg-gray-900 p-8 flex flex-col'
    : className;

  return (
    <div className={containerClass}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        {title && (
          <h4 className="text-sm font-semibold text-gray-200">{title}</h4>
        )}
        <div className="flex items-center gap-2">
          {/* Refresh */}
          <button
            onClick={handleRefresh}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-gray-200"
            title="Refresh"
          >
            <RefreshCw size={14} />
          </button>

          {/* Export SVG */}
          <button
            onClick={handleExportSVG}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-gray-200"
            title="Export SVG"
          >
            <Download size={14} />
          </button>

          {/* Fullscreen toggle */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-gray-200"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>

      {/* Chart Container */}
      <div className="relative bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 z-10">
            <Loader2 className="w-6 h-6 animate-spin text-green-400" />
            <span className="ml-2 text-sm text-gray-400">Generating report...</span>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 z-10">
            <div className="text-center">
              <p className="text-red-400 text-sm">{error}</p>
              <button
                onClick={handleRefresh}
                className="mt-2 text-xs text-gray-400 hover:text-gray-200"
              >
                Try again
              </button>
            </div>
          </div>
        )}

        <div
          ref={containerRef}
          style={{
            width: isFullscreen ? '100%' : width,
            height: isFullscreen ? 'calc(100vh - 200px)' : height,
            minHeight: 200,
          }}
        />
      </div>

      {/* Export buttons (fullscreen mode) */}
      {isFullscreen && (
        <div className="flex justify-center gap-3 mt-4">
          <button
            onClick={handleExportSVG}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-gray-200 flex items-center gap-2"
          >
            <Download size={16} />
            Export SVG
          </button>
          <button
            onClick={handleExportPNG}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-gray-200 flex items-center gap-2"
          >
            <Download size={16} />
            Export PNG
          </button>
        </div>
      )}
    </div>
  );
};

export default InfographicReport;
