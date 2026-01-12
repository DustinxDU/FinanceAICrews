"use client";

import React from "react";
import { LanguageSelectorButton } from "@/components/LanguageSelector";
import { useTranslations } from "next-intl";
import { useTheme } from "@/contexts/ThemeContext";

export function PreferencesTab() {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const { theme, setTheme, isLoading: isThemeLoading } = useTheme();

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <h2 className="text-xl font-bold mb-4">{t('preferences')}</h2>

      <div className="flex items-center justify-between p-4 bg-[var(--bg-card)] rounded-lg">
        <div>
          <div className="font-medium">{tCommon('theme')}</div>
          <div className="text-xs text-[var(--text-secondary)]">{t('chooseInterfaceAppearance')}</div>
        </div>
        <select
          className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded px-2 py-1 text-sm"
          value={theme}
          onChange={async (e) => setTheme(e.target.value as typeof theme)}
          disabled={isThemeLoading}
        >
          <option value="dark">Dark</option>
          <option value="light">Light</option>
          <option value="system">{t('system')}</option>
        </select>
      </div>

      <div className="flex items-center justify-between p-4 bg-[var(--bg-card)] rounded-lg">
        <div>
          <div className="font-medium">{tCommon('language')}</div>
          <div className="text-xs text-[var(--text-secondary)]">{t('selectPlatformLanguage')}</div>
        </div>
        <LanguageSelectorButton variant="settings" />
      </div>
    </div>
  );
}
