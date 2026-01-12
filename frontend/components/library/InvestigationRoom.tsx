"use client";

import React from "react";

interface InvestigationRoomProps {
  insightId: number;
}

export default function InvestigationRoom({ insightId }: InvestigationRoomProps) {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4 text-[var(--text-primary)]">Investigation Room</h2>
      <p className="text-sm text-[var(--text-secondary)]">Viewing insight #{insightId}</p>
    </div>
  );
}
