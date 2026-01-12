"use client";

import React from "react";
import { Link } from "@/i18n/routing";
import NextLink from "next/link";
import { ArrowRight, PlayCircle, BrainCircuit, Database, ShieldCheck, TrendingUp } from "lucide-react";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { useAuth } from "@/contexts/AuthContext";
import { useTranslations } from "next-intl";

function HeroSection() {
  const { isAuthenticated } = useAuth();
  const t = useTranslations('homepage');

  return (
    <section className="relative pt-32 pb-24 px-6 overflow-hidden">
      <div className="absolute inset-0 grid-bg opacity-30 -z-10"></div>
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-green-500/10 blur-[120px] rounded-full -z-10"></div>

      <div className="max-w-7xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-zinc-800 bg-zinc-900/50 mb-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
          </span>
          <span className="text-xs font-medium text-zinc-400">{t('liveVersion')}</span>
        </div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8 animate-in fade-in slide-in-from-bottom-6 duration-700 delay-100">
          {t('title')}
        </h1>

        <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto mb-12 animate-in fade-in slide-in-from-bottom-6 duration-700 delay-200">
          {t('subtitle')}
        </p>

        <div className="flex flex-col md:flex-row items-center justify-center gap-4 animate-in fade-in slide-in-from-bottom-6 duration-700 delay-300">
          {isAuthenticated ? (
            <Link
              href="/dashboard"
              className="w-full md:w-auto px-8 py-4 bg-[var(--text-primary)] text-black font-bold rounded-lg hover:bg-white/90 transition-all flex items-center justify-center gap-2"
            >
              {t('goToDashboard')} <ArrowRight className="w-4 h-4" />
            </Link>
          ) : (
            <NextLink
              href="/register"
              className="w-full md:w-auto px-8 py-4 bg-[var(--text-primary)] text-black font-bold rounded-lg hover:bg-white/90 transition-all flex items-center justify-center gap-2"
            >
              {t('startForFree')} <ArrowRight className="w-4 h-4" />
            </NextLink>
          )}

          {isAuthenticated ? (
            <Link
              href="/dashboard"
              className="w-full md:w-auto px-8 py-4 bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] font-medium rounded-lg hover:bg-[var(--bg-panel)] transition-all flex items-center justify-center gap-2"
            >
              <PlayCircle className="w-4 h-4" /> {t('openDashboard')}
            </Link>
          ) : (
            <a
              href="#demo"
              className="w-full md:w-auto px-8 py-4 bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] font-medium rounded-lg hover:bg-[var(--bg-panel)] transition-all flex items-center justify-center gap-2"
            >
              <PlayCircle className="w-4 h-4" /> {t('watchDemo')}
            </a>
          )}
        </div>
      </div>
      
      {/* Terminal Animation Mockup */}
      <div className="max-w-5xl mx-auto mt-20 rounded-xl border border-[var(--border-color)] bg-[#0c0c0e] shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-1000 delay-500">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-color)] bg-zinc-900/50">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500/50"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500/50"></div>
            <div className="w-3 h-3 rounded-full bg-green-500/50"></div>
          </div>
          <div className="ml-4 text-xs text-zinc-500 font-mono">finance-ai-agent — python main.py</div>
        </div>
        <div className="p-6 font-mono text-sm text-zinc-300 h-[400px] overflow-hidden relative">
          <div className="space-y-2">
            <div className="text-green-400">➜ system init --mode=alpha_seek</div>
            <div className="text-blue-400">[Orchestrator] Crew initialized with 3 agents.</div>
            <div className="text-zinc-500">[Researcher] Scanning Bloomberg Terminal for "Lithium Shortage"...</div>
            <div className="text-zinc-500">[Researcher] Found 24 relevant reports. Analyzing sentiment...</div>
            <div className="text-yellow-400">[Analyst] Detected divergence in spot price vs futures.</div>
            <div className="text-purple-400">[Writer] Drafting investment thesis...</div>
            <div className="pl-4 border-l-2 border-green-500/30 text-zinc-400 mt-4">
              "Recommendation: OVERWEIGHT on mining sector. The supply gap for Q4 is projected to widen by 15% based on new EV production targets in SEA."
            </div>
            <div className="animate-pulse mt-4">_</div>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#0c0c0e] to-transparent"></div>
        </div>
      </div>
    </section>
  );
}

interface FeatureCardProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  desc: string;
  delay: string;
}

function FeatureCard({ icon: Icon, title, desc, delay }: FeatureCardProps) {
  return (
    <div 
      className="p-6 rounded-2xl bg-[var(--bg-panel)] border border-[var(--border-color)] hover:border-[var(--text-secondary)] transition-colors animate-in fade-in slide-in-from-bottom-8 duration-700"
      style={{ animationDelay: delay }}
    >
      <div className="w-12 h-12 rounded-lg bg-[var(--bg-card)] flex items-center justify-center border border-[var(--border-color)] mb-4">
        <Icon className="w-6 h-6 text-[var(--text-primary)]" />
      </div>
      <h3 className="text-xl font-bold mb-2">{title}</h3>
      <p className="text-[var(--text-secondary)] leading-relaxed">{desc}</p>
    </div>
  );
}

function FeaturesSection() {
  const t = useTranslations('homepage');

  return (
    <section id="features" className="py-24 px-6 border-t border-[var(--border-color)] bg-[var(--bg-app)]">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">{t('features.title')}</h2>
          <p className="text-[var(--text-secondary)]">{t('features.subtitle')}</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <FeatureCard
            icon={BrainCircuit}
            title={t('features.autonomousCrews.title')}
            desc={t('features.autonomousCrews.description')}
            delay="0ms"
          />
          <FeatureCard
            icon={Database}
            title={t('features.institutionalData.title')}
            desc={t('features.institutionalData.description')}
            delay="100ms"
          />
          <FeatureCard
            icon={ShieldCheck}
            title={t('features.enterpriseSecurity.title')}
            desc={t('features.enterpriseSecurity.description')}
            delay="200ms"
          />
        </div>
      </div>
    </section>
  );
}

function LandingPage() {
  return (
    <PublicLayout>
      <HeroSection />
      <FeaturesSection />
    </PublicLayout>
  );
}

export default LandingPage;
