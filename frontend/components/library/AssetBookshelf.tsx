"use client";

import React from "react";

interface AssetBookshelfProps {
  onAssetSelect: (ticker: string) => void;
}

export default function AssetBookshelf({ onAssetSelect }: AssetBookshelfProps) {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4 text-[var(--text-primary)]">Asset Bookshelf</h2>
      <p className="text-sm text-[var(--text-secondary)]">Coming soon...</p>
    </div>
  );
}
