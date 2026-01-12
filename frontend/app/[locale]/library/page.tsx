"use client";

import React, { useState } from "react";
import { AppLayout } from "@/components/layout";
import { useTranslations } from "next-intl";

// Import new Library components (same directory) - using default exports
import AssetBookshelf from "./AssetBookshelf";
import SignalTimeline from "./SignalTimeline";
import InvestigationRoom from "./InvestigationRoom";

export default function LibraryPage() {
  const t = useTranslations('library');
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [selectedInsightId, setSelectedInsightId] = useState<number | null>(null);

  const handleAssetSelect = (ticker: string) => {
    setSelectedTicker(ticker);
    setSelectedInsightId(null);
  };

  const handleInsightSelect = (insightId: number) => {
    setSelectedInsightId(insightId);
  };

  return (
    <AppLayout>
      <div className="flex h-[calc(100vh-3.5rem)] bg-[var(--bg-app)] overflow-hidden">
        {/* Left: Asset Bookshelf */}
        <div className="w-80 border-r border-[var(--border-color)] bg-[var(--bg-panel)] flex flex-col shrink-0 h-full">
          <AssetBookshelf
            onAssetSelect={handleAssetSelect}
            selectedTicker={selectedTicker}
          />
        </div>

        {/* Middle: Signal Timeline */}
        <div className="w-96 border-r border-[var(--border-color)] bg-[var(--bg-panel)] flex flex-col shrink-0 h-full">
          <SignalTimeline
            ticker={selectedTicker || undefined}
            onInsightSelect={handleInsightSelect}
            selectedInsightId={selectedInsightId}
          />
        </div>

        {/* Right: Investigation Room */}
        <div className="flex-1 bg-[var(--bg-panel)] flex flex-col min-w-0 border-r border-[var(--border-color)] h-full">
          {selectedInsightId ? (
            <InvestigationRoom insightId={selectedInsightId} />
          ) : (
            <div className="flex-1 flex items-center justify-center h-full">
              <div className="text-center animate-fade-in">
                {/* Animated icon */}
                <div className="relative w-20 h-20 mx-auto mb-4">
                  <div className="absolute inset-0 rounded-full bg-[var(--accent-blue)]/20 animate-ping opacity-75" />
                  <div className="relative w-20 h-20 rounded-full bg-[var(--bg-card)] flex items-center justify-center border border-[var(--border-color)]">
                    <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--accent-blue)]">
                      <circle cx="11" cy="11" r="8"></circle>
                      <path d="m21 21-4.3-4.3"></path>
                      <path d="M11 8v6"></path>
                      <path d="M8 11h6"></path>
                    </svg>
                  </div>
                </div>
                <p className="text-lg font-medium text-[var(--text-primary)]">{t('assetIntelligenceBureau')}</p>
                <p className="text-sm text-[var(--text-secondary)] mt-2">
                  {t('selectAssetToView')}
                </p>
                <p className="text-xs text-[var(--text-secondary)]/60 mt-1">
                  {t('createAnalysisHint')}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
