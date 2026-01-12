"use client";

import React from "react";

interface SignalTimelineProps {
  ticker?: string;
  onInsightSelect: (insightId: number) => void;
}

export default function SignalTimeline({ ticker, onInsightSelect }: SignalTimelineProps) {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4 text-[var(--text-primary)]">Signal Timeline</h2>
      {ticker ? (
        <p className="text-sm text-[var(--text-secondary)]">Signals for {ticker}</p>
      ) : (
        <p className="text-sm text-[var(--text-secondary)]">Select an asset to view signals</p>
      )}
    </div>
  );
}
