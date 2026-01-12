"use client";

import React from "react";
import NextLink from "next/link";
import { Link } from "@/i18n/routing";
import { Zap, Menu, X } from "lucide-react";
import { LanguageSelectorButton } from "@/components/LanguageSelector";
import { useTranslations } from "next-intl";

function PublicNavbar() {
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);
  const tNav = useTranslations('navigation');
  const tFooter = useTranslations('footer');

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[var(--bg-app)]/80 backdrop-blur-md border-b border-[var(--border-color)]">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <Zap className="w-5 h-5 text-[var(--accent-green)] neon-text-green" />
          <span className="font-bold text-lg tracking-tight">FinanceAI</span>
        </Link>

        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-[var(--text-secondary)]">
          <Link href="/#features" className="hover:text-[var(--text-primary)] transition-colors">{tNav('features')}</Link>
          <Link href="/pricing" className="hover:text-[var(--text-primary)] transition-colors">{tNav('pricing')}</Link>
          <Link href="/docs" className="hover:text-[var(--text-primary)] transition-colors">{tNav('docs')}</Link>
          <Link href="/status" className="hover:text-[var(--text-primary)] transition-colors">{tNav('status')}</Link>
        </div>

        <div className="flex items-center gap-4">
          <NextLink href="/login" className="text-sm font-medium text-[var(--text-primary)] hover:text-[var(--text-secondary)] transition-colors">
            {tNav('signIn')}
          </NextLink>
          <NextLink href="/register" className="bg-[var(--text-primary)] text-[var(--bg-app)] px-4 py-2 rounded-lg text-sm font-bold hover:bg-white/90 transition-colors">
            {tNav('getStarted')}
          </NextLink>
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="md:hidden p-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            {isMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMenuOpen && (
        <div className="md:hidden bg-[var(--bg-panel)] border-t border-[var(--border-color)]">
          <div className="px-6 py-4 space-y-4">
            <Link href="/#features" className="block text-[var(--text-secondary)] hover:text-[var(--text-primary)]">{tNav('features')}</Link>
            <Link href="/pricing" className="block text-[var(--text-secondary)] hover:text-[var(--text-primary)]">{tNav('pricing')}</Link>
            <Link href="/docs" className="block text-[var(--text-secondary)] hover:text-[var(--text-primary)]">{tNav('docs')}</Link>
            <Link href="/status" className="block text-[var(--text-secondary)] hover:text-[var(--text-primary)]">{tNav('status')}</Link>
          </div>
        </div>
      )}
    </nav>
  );
}

function PublicFooter() {
  const t = useTranslations('footer');
  const tNav = useTranslations('navigation');

  return (
    <footer className="border-t border-[var(--border-color)] bg-[var(--bg-panel)] pt-16 pb-8">
      <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-[var(--accent-green)]" />
            <span className="font-bold">FinanceAI</span>
          </div>
          <p className="text-sm text-[var(--text-secondary)]">
            {t('tagline')}
          </p>
        </div>
        <div>
          <h4 className="font-bold mb-4">{t('product')}</h4>
          <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
            <li><Link href="/pricing" className="hover:text-[var(--text-primary)]">{tNav('pricing')}</Link></li>
            <li><Link href="/changelog" className="hover:text-[var(--text-primary)]">{t('changelog')}</Link></li>
            <li><Link href="/mcp" className="hover:text-[var(--text-primary)]">{t('mcpStore')}</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="font-bold mb-4">{t('resources')}</h4>
          <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
            <li><Link href="/docs" className="hover:text-[var(--text-primary)]">{t('documentation')}</Link></li>
            <li><Link href="/status" className="hover:text-[var(--text-primary)]">{t('systemStatus')}</Link></li>
            <li><Link href="/api" className="hover:text-[var(--text-primary)]">{t('apiReference')}</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="font-bold mb-4">{t('legal')}</h4>
          <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
            <li><Link href="/privacy" className="hover:text-[var(--text-primary)]">{t('privacyPolicy')}</Link></li>
            <li><Link href="/terms" className="hover:text-[var(--text-primary)]">{t('termsOfService')}</Link></li>
            <li><Link href="/disclaimer" className="hover:text-[var(--text-primary)]">{t('disclaimer')}</Link></li>
          </ul>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-6 pt-8 border-t border-[var(--border-color)]">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="text-xs text-[var(--text-secondary)] text-center md:text-left">
            {t('copyright')}
          </div>
          <div className="flex items-center gap-4 text-xs text-[var(--text-secondary)]">
            <LanguageSelectorButton variant="footer" />
          </div>
        </div>
      </div>
    </footer>
  );
}

interface PublicLayoutProps {
  children: React.ReactNode;
}

export function PublicLayout({ children }: PublicLayoutProps) {
  return (
    <div className="min-h-screen bg-[var(--bg-app)] text-[var(--text-primary)] font-sans selection:bg-[var(--accent-green)] selection:text-black">
      <PublicNavbar />
      <main className="pt-16">
        {children}
      </main>
      <PublicFooter />
    </div>
  );
}
