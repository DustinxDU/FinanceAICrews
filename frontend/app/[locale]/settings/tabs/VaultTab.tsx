"use client";

import React from "react";
import { Lock } from "lucide-react";

interface VaultTabProps {
  savedProviders: any[];
}

export function VaultTab({ savedProviders }: VaultTabProps) {
  return (
    <div className="animate-in fade-in duration-300">
      <h2 className="text-xl font-bold mb-1">API Vault</h2>
      <p className="text-sm text-[var(--text-secondary)] mb-6">Manage all your secure credentials in one place.</p>
      <div className="space-y-4">
        {savedProviders.map((p) => (
          <div key={p.id} className="flex items-center justify-between p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded bg-zinc-800 text-[var(--text-secondary)] flex items-center justify-center border border-[var(--border-color)]">
                <Lock className="w-4 h-4" />
              </div>
              <div>
                <div className="font-medium">{p.name} Access Key</div>
                <div className="text-xs text-[var(--text-secondary)] font-mono">{p.key}</div>
              </div>
            </div>
            <div className="text-xs text-[var(--text-secondary)]">Synced from Model Providers</div>
          </div>
        ))}
        {!savedProviders.length && (
          <div className="text-center py-10 text-[var(--text-secondary)]">
            No API credentials found. Add a provider in the Model Providers tab.
          </div>
        )}
      </div>
    </div>
  );
}
