"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import AssetBookshelf from "./AssetBookshelf";
import SignalTimeline from "./SignalTimeline";
import InvestigationRoom from "./InvestigationRoom";

export default function LibraryPage() {
  const t = useTranslations('library');
  const searchParams = useSearchParams();
  const [selectedTicker, setSelectedTicker] = useState<string | null>(
    searchParams.get("asset")
  );
  const [selectedInsightId, setSelectedInsightId] = useState<number | null>(
    null
  );

  const handleAssetSelect = (ticker: string) => {
    setSelectedTicker(ticker);
    setSelectedInsightId(null);
  };

  const handleInsightSelect = (insightId: number) => {
    setSelectedInsightId(insightId);
  };

  return (
    <div className="flex min-h-[calc(100vh-56px)] bg-[var(--bg-app)]">
      {/* 左侧：资产书架 */}
      <div className="w-80 bg-[var(--bg-panel)] border-r border-[var(--border-color)] flex flex-col">
        <AssetBookshelf onAssetSelect={handleAssetSelect} />
      </div>

      {/* 中间：信号时间轴 */}
      <div className="w-96 bg-[var(--bg-panel)] border-r border-[var(--border-color)] flex flex-col">
        <SignalTimeline
          ticker={selectedTicker || undefined}
          onInsightSelect={handleInsightSelect}
        />
      </div>

      {/* 右侧：研报透视室 */}
      <div className="flex-1 bg-[var(--bg-panel)] flex flex-col overflow-hidden">
        {selectedInsightId ? (
          <InvestigationRoom insightId={selectedInsightId} />
        ) : (
          <div className="flex-1 flex items-center justify-center text-[var(--text-secondary)]">
            <div className="text-center">
              <div className="text-4xl mb-4">📚</div>
              <p className="text-lg text-[var(--text-primary)]">{t('assetIntelligenceBureau')}</p>
              <p className="text-sm mt-2 text-[var(--text-secondary)]">
                {t('selectAssetToView')}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
