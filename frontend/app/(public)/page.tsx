"use client";

import React from "react";
import Link from "next/link";
import { Zap, ArrowRight, PlayCircle, BrainCircuit, Database, ShieldCheck } from "lucide-react";

function PublicNavbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[var(--bg-app)]/80 backdrop-blur-md border-b border-[var(--border-color)]">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <Zap className="w-5 h-5 text-[var(--accent-green)]" />
          <span className="font-bold text-lg tracking-tight">FinanceAI</span>
        </Link>
        
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-[var(--text-secondary)]">
          <a href="#features" className="hover:text-[var(--text-primary)] transition-colors">Features</a>
          <Link href="/pricing" className="hover:text-[var(--text-primary)] transition-colors">Pricing</Link>
          <Link href="/docs" className="hover:text-[var(--text-primary)] transition-colors">Docs</Link>
        </div>

        <div className="flex items-center gap-4">
          <Link href="/login" className="text-sm font-medium text-[var(--text-primary)] hover:text-[var(--text-secondary)] transition-colors">Sign In</Link>
          <Link href="/register" className="bg-[var(--text-primary)] text-[var(--bg-app)] px-4 py-2 rounded-lg text-sm font-bold hover:bg-white/90 transition-colors">
            Get Started
          </Link>
        </div>
      </div>
    </nav>
  );
}

function PublicFooter() {
  return (
    <footer className="border-t border-[var(--border-color)] bg-[var(--bg-panel)] pt-16 pb-8">
      <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-[var(--accent-green)]" />
            <span className="font-bold">FinanceAI</span>
          </div>
          <p className="text-sm text-[var(--text-secondary)]">
            The operating system for modern finance teams.
          </p>
        </div>
        <div>
          <h4 className="font-bold mb-4">Product</h4>
          <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
            <li><Link href="/pricing" className="hover:text-[var(--text-primary)]">Pricing</Link></li>
            <li><Link href="/changelog" className="hover:text-[var(--text-primary)]">Changelog</Link></li>
            <li><Link href="/mcp" className="hover:text-[var(--text-primary)]">MCP Store</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="font-bold mb-4">Resources</h4>
          <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
            <li><Link href="/docs" className="hover:text-[var(--text-primary)]">Documentation</Link></li>
            <li><Link href="/status" className="hover:text-[var(--text-primary)]">System Status</Link></li>
            <li><a href="#" className="hover:text-[var(--text-primary)]">API Reference</a></li>
          </ul>
        </div>
        <div>
          <h4 className="font-bold mb-4">Legal</h4>
          <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
            <li><Link href="/legal" className="hover:text-[var(--text-primary)]">Privacy Policy</Link></li>
            <li><Link href="/legal" className="hover:text-[var(--text-primary)]">Terms of Service</Link></li>
            <li><Link href="/legal" className="hover:text-[var(--text-primary)]">Disclaimer</Link></li>
          </ul>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-6 pt-8 border-t border-[var(--border-color)] text-center text-xs text-[var(--text-secondary)]">
        &copy; 2025 FinanceAI Inc. All rights reserved.
      </div>
    </footer>
  );
}

function HeroSection() {
  return (
    <section className="relative pt-32 pb-24 px-6 overflow-hidden">
      <div className="absolute inset-0 grid-bg opacity-30 -z-10" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-green-500/10 blur-[120px] rounded-full -z-10" />

      <div className="max-w-7xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-zinc-800 bg-zinc-900/50 mb-8">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
          </span>
          <span className="text-xs font-medium text-zinc-400">FinanceAI V3.0 is live</span>
        </div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8">
          Build Your AI <br />
          <span className="text-[var(--accent-green)] neon-text-green">Wall Street Team</span>
        </h1>
        
        <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto mb-12">
          Deploy autonomous research crews. Connect institutional data sources. Generate alpha-seeking reports in minutes, not weeks.
        </p>

        <div className="flex flex-col md:flex-row items-center justify-center gap-4">
          <Link href="/register" className="w-full md:w-auto px-8 py-4 bg-[var(--text-primary)] text-black font-bold rounded-lg hover:bg-white/90 transition-all flex items-center justify-center gap-2">
            Start for Free <ArrowRight className="w-4 h-4" />
          </Link>
          <a href="#demo" className="w-full md:w-auto px-8 py-4 bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] font-medium rounded-lg hover:bg-[var(--bg-panel)] transition-all flex items-center justify-center gap-2">
            <PlayCircle className="w-4 h-4" /> Watch Demo
          </a>
        </div>
      </div>
      
      {/* Terminal Animation Mockup */}
      <div className="max-w-5xl mx-auto mt-20 rounded-xl border border-[var(--border-color)] bg-[#0c0c0e] shadow-2xl overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-color)] bg-zinc-900/50">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500/50" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
            <div className="w-3 h-3 rounded-full bg-green-500/50" />
          </div>
          <div className="ml-4 text-xs text-zinc-500 font-mono">finance-ai-agent — python main.py</div>
        </div>
        <div className="p-6 font-mono text-sm text-zinc-300 h-[400px] overflow-hidden relative">
          <div className="space-y-2">
            <div className="text-green-400">➜ system init --mode=alpha_seek</div>
            <div className="text-blue-400">[Orchestrator] Crew initialized with 3 agents.</div>
            <div className="text-zinc-500">[Researcher] Scanning Bloomberg Terminal for &quot;Lithium Shortage&quot;...</div>
            <div className="text-zinc-500">[Researcher] Found 24 relevant reports. Analyzing sentiment...</div>
            <div className="text-yellow-400">[Analyst] Detected divergence in spot price vs futures.</div>
            <div className="text-purple-400">[Writer] Drafting investment thesis...</div>
            <div className="pl-4 border-l-2 border-green-500/30 text-zinc-400 mt-4">
              &quot;Recommendation: OVERWEIGHT on mining sector. The supply gap for Q4 is projected to widen by 15% based on new EV production targets in SEA.&quot;
            </div>
            <div className="animate-pulse mt-4">_</div>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#0c0c0e] to-transparent" />
        </div>
      </div>
    </section>
  );
}

function FeatureCard({ icon: Icon, title, desc }: { icon: React.ElementType; title: string; desc: string }) {
  return (
    <div className="p-6 rounded-2xl bg-[var(--bg-panel)] border border-[var(--border-color)] hover:border-[var(--text-secondary)] transition-colors">
      <div className="w-12 h-12 rounded-lg bg-[var(--bg-card)] flex items-center justify-center border border-[var(--border-color)] mb-4">
        <Icon className="w-6 h-6 text-[var(--text-primary)]" />
      </div>
      <h3 className="text-xl font-bold mb-2">{title}</h3>
      <p className="text-[var(--text-secondary)] leading-relaxed">{desc}</p>
    </div>
  );
}

function FeaturesSection() {
  return (
    <section id="features" className="py-24 px-6 border-t border-[var(--border-color)] bg-[var(--bg-app)]">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Orchestrate Your Financial Future</h2>
          <p className="text-[var(--text-secondary)]">Everything you need to analyze markets at machine speed.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <FeatureCard 
            icon={BrainCircuit} 
            title="Autonomous Crews" 
            desc="Create teams of specialized AI agents (Researchers, Analysts, Traders) that work together to solve complex problems."
          />
          <FeatureCard 
            icon={Database} 
            title="Institutional Data" 
            desc="Plug into Bloomberg, Reuters, and SEC filings via our MCP (Model Context Protocol) store."
          />
          <FeatureCard 
            icon={ShieldCheck} 
            title="Enterprise Security" 
            desc="Your data never trains our models. SOC2 compliant infrastructure with BYOK (Bring Your Own Key) support."
          />
        </div>
      </div>
    </section>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--bg-app)] text-[var(--text-primary)] font-sans selection:bg-[var(--accent-green)] selection:text-black">
      <PublicNavbar />
      <main className="pt-16">
        <HeroSection />
        <FeaturesSection />
      </main>
      <PublicFooter />
    </div>
  );
}
