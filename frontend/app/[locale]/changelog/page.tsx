"use client";

import React from "react";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { useTranslations } from "next-intl";


interface ChangelogItemProps {
  date: string;
  title: string;
  content: React.ReactNode;
  version: string;
}

function ChangelogItem({ date, title, content, version }: ChangelogItemProps) {
  return (
    <div className="flex gap-8 mb-12 relative">
      <div className="w-32 shrink-0 text-right pt-1 hidden md:block">
        <div className="text-sm font-bold text-[var(--text-primary)]">{date}</div>
        <div className="text-xs text-[var(--text-secondary)]">{version}</div>
      </div>
      
      <div className="absolute left-[8.5rem] top-2 bottom-0 w-[1px] bg-[var(--border-color)] hidden md:block"></div>
      <div className="absolute left-[8.3rem] top-2 w-4 h-4 rounded-full bg-[var(--bg-app)] border border-[var(--accent-green)] hidden md:block"></div>

      <div className="flex-1 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-6">
        <div className="md:hidden mb-2 flex justify-between items-baseline">
          <span className="text-sm font-bold text-[var(--text-primary)]">{date}</span>
          <span className="text-xs text-[var(--text-secondary)]">{version}</span>
        </div>
        <h3 className="text-xl font-bold mb-4">{title}</h3>
        <div className="prose prose-invert prose-sm max-w-none text-[var(--text-secondary)]">
          {content}
        </div>
      </div>
    </div>
  );
}

function ChangelogPage() {
  const t = useTranslations("changelog");
  return (
    <PublicLayout>
      <div className="py-24 px-6 max-w-4xl mx-auto">
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold mb-4">{t('changelog')}</h1>
          <p className="text-[var(--text-secondary)]">New updates and improvements to FinanceAI.</p>
        </div>

        <div className="pl-0 md:pl-4">
          <ChangelogItem 
            date="Dec 20, 2025"
            version="v3.0.0"
            title="Introducing FinanceAI V3.0"
            content={
              <ul className="space-y-2">
                <li><strong>{t('crewBuilder')}</strong> Visual node-based editor for orchestrating agent teams.</li>
                <li><strong>DeepSeek-V3 Support:</strong> Added native support for the latest DeepSeek model, optimized for reasoning tasks.</li>
                <li><strong>MCP Store:</strong> A new marketplace to connect external tools like Bloomberg and SEC Edgar.</li>
                <li><strong>Dark Mode UI:</strong> Completely redesigned interface focusing on information density and readability.</li>
              </ul>
            }
          />
          <ChangelogItem
            date="Nov 15, 2025"
            version="v2.4.0"
            title="Enhanced Charting & Reporting"
            content={
              <ul className="space-y-2">
                <li>Added streaming response support for faster feedback.</li>
                <li>Integrated Chart.js for rendering financial charts directly within agent reports.</li>
                <li>Improved PDF parsing capabilities for annual reports.</li>
              </ul>
            }
          />
          <ChangelogItem
            date="Oct 28, 2025"
            version="v2.3.0"
            title="Performance & Security Updates"
            content={
              <ul className="space-y-2">
                <li>Implemented SOC2 Type II compliance framework.</li>
                <li>Added BYOK (Bring Your Own Key) support for enterprise customers.</li>
                <li>Optimized agent execution pipeline for 40% faster analysis times.</li>
                <li>Enhanced error handling and retry mechanisms.</li>
              </ul>
            }
          />
          <ChangelogItem 
            date="Sep 12, 2025"
            version="v2.2.0"
            title="Multi-Model Support"
            content={
              <ul className="space-y-2">
                <li>Added support for Claude 3.5 Sonnet and GPT-4 Turbo.</li>
                <li>Introduced model switching within active crews.</li>
                <li>Cost optimization features for high-volume users.</li>
                <li>Real-time model performance monitoring.</li>
              </ul>
            }
          />
        </div>
      </div>
    </PublicLayout>
  );
}

export default ChangelogPage;
