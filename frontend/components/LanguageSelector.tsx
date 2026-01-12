"use client";

import React, { useState } from "react";
import { Globe, X, Check } from "lucide-react";
import { useRouter, usePathname } from "@/i18n/routing";
import { useLocale } from "next-intl";

export interface Language {
  code: string;
  name: string;
  nativeName: string;
  flag: string;
  region: string;
}

export const languages: Language[] = [
  // Global
  { code: "en", name: "English", nativeName: "English", flag: "🇺🇸", region: "global" },
  { code: "es", name: "Spanish", nativeName: "Español", flag: "🇪🇸", region: "global" },
  { code: "fr", name: "French", nativeName: "Français", flag: "🇫🇷", region: "global" },
  { code: "de", name: "German", nativeName: "Deutsch", flag: "🇩🇪", region: "global" },
  { code: "ru", name: "Russian", nativeName: "Русский", flag: "🇷🇺", region: "global" },
  { code: "pt", name: "Portuguese", nativeName: "Português", flag: "🇧🇷", region: "global" },
  { code: "ar", name: "Arabic", nativeName: "العربية", flag: "🇸🇦", region: "global" },
  { code: "hi", name: "Hindi", nativeName: "हिन्दी", flag: "🇮🇳", region: "global" },

  // Asia
  { code: "zh-CN", name: "Chinese (Simplified)", nativeName: "简体中文", flag: "🇨🇳", region: "asia" },
  { code: "zh-TW", name: "Chinese (Traditional)", nativeName: "繁體中文", flag: "🇨🇳", region: "asia" },
  { code: "ja", name: "Japanese", nativeName: "日本語", flag: "🇯🇵", region: "asia" },
  { code: "ko", name: "Korean", nativeName: "한국어", flag: "🇰🇷", region: "asia" },
  { code: "ms", name: "Malay", nativeName: "Bahasa Melayu", flag: "🇲🇾", region: "asia" },
  { code: "id", name: "Indonesian", nativeName: "Bahasa Indonesia", flag: "🇮🇩", region: "asia" },
  { code: "vi", name: "Vietnamese", nativeName: "Tiếng Việt", flag: "🇻🇳", region: "asia" },
  { code: "th", name: "Thai", nativeName: "ภาษาไทย", flag: "🇹🇭", region: "asia" },
];

interface LanguageSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function LanguageSelectorModal({ isOpen, onClose }: LanguageSelectorModalProps) {
  const router = useRouter();
  const pathname = usePathname();
  const currentLocale = useLocale();
  const [activeLocale, setActiveLocale] = useState(currentLocale);

  const handleLanguageChange = (languageCode: string) => {
    setActiveLocale(languageCode);
    // next-intl's router.push automatically handles locale prefix
    router.push(pathname, { locale: languageCode });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200" onClick={onClose}>
      <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl w-full max-w-2xl shadow-2xl overflow-hidden animate-in zoom-in-95" onClick={e => e.stopPropagation()}>
        <div className="p-4 border-b border-[var(--border-color)] flex justify-between items-center bg-[var(--bg-card)]">
          <h3 className="font-bold flex items-center gap-2">
            <Globe className="w-4 h-4 text-[var(--accent-blue)]" />
            Select Language
          </h3>
          <button onClick={onClose} className="p-1 hover:text-white text-[var(--text-secondary)]">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 max-h-[70vh] overflow-y-auto">
          <div className="grid md:grid-cols-2 gap-8">
            {/* Global Section */}
            <div>
              <h4 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-4 border-b border-[var(--border-color)] pb-2">Global</h4>
              <div className="grid grid-cols-1 gap-2">
                {languages.filter(l => l.region === 'global').map((language) => (
                  <button
                    key={language.code}
                    onClick={() => handleLanguageChange(language.code)}
                    className={`flex items-center gap-3 p-3 rounded-lg border transition-all hover:bg-[var(--bg-card)] text-left group ${activeLocale === language.code ? 'border-[var(--accent-green)] bg-[var(--bg-card)]' : 'border-transparent hover:border-[var(--border-color)]'}`}
                  >
                    <span className="text-2xl">{language.flag}</span>
                    <div className="flex-1">
                      <div className={`text-sm font-medium ${activeLocale === language.code ? 'text-[var(--accent-green)]' : 'text-[var(--text-primary)]'}`}>{language.name}</div>
                      <div className="text-xs text-[var(--text-secondary)] opacity-60 group-hover:opacity-100">{language.code}</div>
                    </div>
                    {activeLocale === language.code && <Check className="w-4 h-4 text-[var(--accent-green)]" />}
                  </button>
                ))}
              </div>
            </div>

            {/* Asia Pacific Section */}
            <div>
              <h4 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-4 border-b border-[var(--border-color)] pb-2">Asia Pacific</h4>
              <div className="grid grid-cols-1 gap-2">
                {languages.filter(l => l.region === 'asia').map((language) => (
                  <button
                    key={language.code}
                    onClick={() => handleLanguageChange(language.code)}
                    className={`flex items-center gap-3 p-3 rounded-lg border transition-all hover:bg-[var(--bg-card)] text-left group ${activeLocale === language.code ? 'border-[var(--accent-green)] bg-[var(--bg-card)]' : 'border-transparent hover:border-[var(--border-color)]'}`}
                  >
                    <span className="text-2xl">{language.flag}</span>
                    <div className="flex-1">
                      <div className={`text-sm font-medium ${activeLocale === language.code ? 'text-[var(--accent-green)]' : 'text-[var(--text-primary)]'}`}>{language.nativeName}</div>
                      <div className="text-xs text-[var(--text-secondary)] opacity-60 group-hover:opacity-100">{language.code}</div>
                    </div>
                    {activeLocale === language.code && <Check className="w-4 h-4 text-[var(--accent-green)]" />}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface LanguageSelectorButtonProps {
  variant?: "footer" | "settings" | "navbar";
  className?: string;
}

export function LanguageSelectorButton({ variant = "footer", className = "" }: LanguageSelectorButtonProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const currentLocale = useLocale();
  const currentLanguage = languages.find(lang => lang.code === currentLocale);

  if (variant === "navbar") {
    return (
      <>
        <button
          onClick={() => setIsModalOpen(true)}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[var(--text-secondary)] transition-all text-xs font-medium ${className}`}
        >
          <span className="text-sm">{currentLanguage?.flag}</span>
          <span className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
            {currentLanguage?.code.toUpperCase() || "EN"}
          </span>
          <Globe className="w-3 h-3 text-[var(--text-secondary)]" />
        </button>
        <LanguageSelectorModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
      </>
    );
  }

  if (variant === "footer") {
    return (
      <>
        <button
          onClick={() => setIsModalOpen(true)}
          className={`text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors flex items-center gap-1 ${className}`}
        >
          <Globe className="w-3 h-3" />
          {currentLanguage?.nativeName || "Language"}
        </button>
        <LanguageSelectorModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
      </>
    );
  }

  return (
    <>
      <button
        onClick={() => setIsModalOpen(true)}
        className={`flex items-center justify-between w-full p-3 rounded-lg bg-[var(--bg-panel)] border border-[var(--border-color)] hover:border-[var(--text-secondary)] transition-colors ${className}`}
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">{currentLanguage?.flag}</span>
          <div className="text-left">
            <div className="text-sm font-medium">{currentLanguage?.nativeName}</div>
            <div className="text-xs text-[var(--text-secondary)]">{currentLanguage?.name}</div>
          </div>
        </div>
        <Globe className="w-4 h-4 text-[var(--text-secondary)]" />
      </button>
      <LanguageSelectorModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </>
  );
}
