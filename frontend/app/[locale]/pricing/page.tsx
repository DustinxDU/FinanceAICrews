"use client";

import React from "react";
import { Link } from "@/i18n/routing";
import { Check } from "lucide-react";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { useTranslations } from "next-intl";


interface PricingCardProps {
  tier: string;
  price: string;
  features: string[];
  recommended?: boolean;
}

function PricingCard({ tier, price, features, recommended }: PricingCardProps) {
  return (
    <div className={`relative p-8 rounded-2xl border flex flex-col h-full ${recommended ? 'bg-[var(--bg-card)] border-[var(--accent-green)] shadow-2xl shadow-green-900/20' : 'bg-[var(--bg-panel)] border-[var(--border-color)]'}`}>
      {recommended && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-[var(--accent-green)] text-black text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">
          Most Popular
        </div>
      )}
      <h3 className="text-xl font-bold mb-2">{tier}</h3>
      <div className="mb-6">
        <span className="text-4xl font-bold">{price}</span>
        {price !== 'Custom' && <span className="text-[var(--text-secondary)]">/month</span>}
      </div>
      <ul className="space-y-4 mb-8 flex-1">
        {features.map((feat, i) => (
          <li key={i} className="flex items-start gap-3 text-sm text-[var(--text-secondary)]">
            <Check className="w-4 h-4 text-[var(--accent-green)] shrink-0 mt-0.5" />
            <span>{feat}</span>
          </li>
        ))}
      </ul>
      <Link 
        href="/register" 
        className={`w-full py-3 rounded-lg text-sm font-bold text-center transition-colors block ${recommended ? 'bg-[var(--accent-green)] text-black hover:bg-emerald-400' : 'bg-[var(--bg-card)] border border-[var(--border-color)] hover:text-white hover:border-zinc-500'}`}
      >
        {price === 'Custom' ? 'Contact Sales' : 'Get Started'}
      </Link>
    </div>
  );
}

function PricingPage() {
  const t = useTranslations('pricing');
  return (
    <PublicLayout>
      <div className="py-24 px-6 max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold mb-4">Simple, Transparent Pricing</h1>
          <p className="text-[var(--text-secondary)]">{t('choosePlanFitsTradingVolume')}</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <PricingCard 
            tier="Starter" 
            price="$0" 
            features={[
              "Local Models (Ollama) Support",
              "1 Concurrent Agent Crew",
              "Basic Market Data (Delayed)",
              "Community Support"
            ]} 
          />
          <PricingCard 
            tier="Pro" 
            price="$49" 
            recommended={true}
            features={[
              "Cloud Models (GPT-4, DeepSeek)",
              "Unlimited Concurrent Crews",
              "Real-time Data Connectors (MCP)",
              "Priority Email Support",
              "API Access"
            ]} 
          />
          <PricingCard 
            tier="Enterprise" 
            price="Custom" 
            features={[
              "Private Cloud Deployment",
              "SSO & Audit Logs",
              "Dedicated Account Manager",
              "Custom MCP Integration",
              "SLA Guarantees"
            ]} 
          />
        </div>
      </div>
    </PublicLayout>
  );
}

export default PricingPage;
