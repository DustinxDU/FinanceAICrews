"use client";

import React, { useState, useEffect } from 'react';
import { Calendar } from 'lucide-react';

export interface TimeframeValue {
  type: 'preset' | 'custom';
  value: string; // preset key or "start:end"
  start?: string;
  end?: string;
}

interface TimeframePickerProps {
  value?: string | TimeframeValue;
  onChange: (value: TimeframeValue) => void;
  className?: string;
}

const presets = [
  { label: '1D', value: '1d' },
  { label: '5D', value: '5d' },
  { label: '1M', value: '1mo' },
  { label: '3M', value: '3mo' },
  { label: '6M', value: '6mo' },
  { label: '1Y', value: '1y' },
  { label: 'YTD', value: 'ytd' },
];

export function TimeframePicker({ value, onChange, className = "" }: TimeframePickerProps) {
  const [mode, setMode] = useState<'preset' | 'custom'>('preset');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  // Initialize from value prop
  useEffect(() => {
    if (typeof value === 'object' && value?.type === 'custom') {
      setMode('custom');
      setCustomStart(value.start || '');
      setCustomEnd(value.end || '');
    } else if (typeof value === 'string' || (typeof value === 'object' && value?.type === 'preset')) {
      setMode('preset');
    }
  }, [value]);

  // Helper to determine current selected value
  const currentValue = typeof value === 'string' ? value : value?.value;

  const handlePresetClick = (presetValue: string) => {
    setMode('preset');
    onChange({ type: 'preset', value: presetValue });
  };

  const handleCustomChange = (start: string, end: string) => {
    setCustomStart(start);
    setCustomEnd(end);
    if (start && end) {
      onChange({
        type: 'custom',
        value: `${start}:${end}`,
        start,
        end
      });
    }
  };

  const handleCustomClick = () => {
    setMode('custom');
    // Set default dates if not set
    if (!customStart) {
      const threeMonthsAgo = new Date();
      threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
      setCustomStart(threeMonthsAgo.toISOString().split('T')[0]);
    }
    if (!customEnd) {
      setCustomEnd(new Date().toISOString().split('T')[0]);
    }
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Presets Row */}
      <div className="flex flex-wrap gap-2">
        {presets.map((preset) => (
          <button
            key={preset.value}
            type="button"
            onClick={() => handlePresetClick(preset.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              mode === 'preset' && currentValue === preset.value
                ? 'bg-[var(--accent-green)] text-black shadow-[0_0_10px_rgba(16,185,129,0.2)]'
                : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-panel)] border border-[var(--border-color)]'
            }`}
          >
            {preset.label}
          </button>
        ))}
        <button
          type="button"
          onClick={handleCustomClick}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1 transition-all ${
            mode === 'custom'
              ? 'bg-[var(--accent-blue)] text-white shadow-[0_0_10px_rgba(59,130,246,0.3)]'
              : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-panel)] border border-[var(--border-color)]'
          }`}
        >
          <Calendar className="w-3 h-3" />
          Custom
        </button>
      </div>

      {/* Custom Date Range Inputs */}
      {mode === 'custom' && (
        <div className="flex items-center gap-2 p-3 bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] animate-in slide-in-from-top-2">
          <div className="flex-1">
            <label className="text-[10px] text-[var(--text-secondary)] uppercase font-bold block mb-1">Start Date</label>
            <input
              type="date"
              value={customStart}
              onChange={(e) => handleCustomChange(e.target.value, customEnd)}
              className="w-full bg-[var(--bg-app)] border border-[var(--border-color)] rounded px-2 py-1.5 text-xs outline-none focus:border-[var(--accent-blue)] text-[var(--text-primary)]"
            />
          </div>
          <div className="text-[var(--text-secondary)] pt-4">→</div>
          <div className="flex-1">
            <label className="text-[10px] text-[var(--text-secondary)] uppercase font-bold block mb-1">End Date</label>
            <input
              type="date"
              value={customEnd}
              onChange={(e) => handleCustomChange(customStart, e.target.value)}
              className="w-full bg-[var(--bg-app)] border border-[var(--border-color)] rounded px-2 py-1.5 text-xs outline-none focus:border-[var(--accent-blue)] text-[var(--text-primary)]"
            />
          </div>
        </div>
      )}
    </div>
  );
}
