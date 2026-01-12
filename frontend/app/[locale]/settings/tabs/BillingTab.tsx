"use client";

import React, { useState, useEffect } from "react";
import { CreditCard, Download, Loader2 } from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import { useToast } from "@/lib/toast";

interface Invoice {
  id: number;
  stripe_invoice_id: string;
  amount: number;
  currency: string;
  status: string;
  invoice_pdf?: string;
  hosted_invoice_url?: string;
  period_start?: string;
  period_end?: string;
  created_at: string;
}

interface Subscription {
  id: number;
  stripe_subscription_id?: string;
  stripe_price_id?: string;
  status: string;
  current_period_start?: string;
  current_period_end?: string;
  cancel_at_period_end: boolean;
  canceled_at?: string;
}

// Stripe price ID - replace with your actual Stripe price ID
const STRIPE_PRICE_ID = "price_1MonthlyPlan";

export function BillingTab() {
  const t = useTranslations("settings");
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpgrading, setIsUpgrading] = useState(false);
  const [isOpeningPortal, setIsOpeningPortal] = useState(false);
  const toast = useToast();

  useEffect(() => {
    loadBillingData();
  }, []);

  async function loadBillingData() {
    try {
      setIsLoading(true);
      const [subResponse, invoicesResponse] = await Promise.all([
        apiClient.getSubscription().catch(() => null),
        apiClient.getInvoices(1, 20).catch(() => ({ invoices: [] }))
      ]);
      setSubscription(subResponse);
      setInvoices(invoicesResponse.invoices || []);
    } catch (error) {
      console.error(t('failed') + " to load billing data:", error);
      toast.error(t('failed') + " to load billing data", "Please try refreshing the page");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleUpgrade() {
    try {
      setIsUpgrading(true);
      const baseUrl = window.location.origin;
      const response = await apiClient.createCheckoutSession(
        STRIPE_PRICE_ID,
        `${baseUrl}/settings?tab=billing&checkout=success`,
        `${baseUrl}/settings?tab=billing&checkout=cancel`
      );
      window.location.href = response.url;
    } catch (error: any) {
      console.error("Checkout failed:", error);
      toast.error(t('failed') + " to start checkout", error.message || "Please try again later");
      setIsUpgrading(false);
    }
  }

  async function handleManageBilling() {
    try {
      setIsOpeningPortal(true);
      const baseUrl = window.location.origin;
      const response = await apiClient.createPortalSession(`${baseUrl}/settings?tab=billing`);
      window.location.href = response.url;
    } catch (error: any) {
      console.error("Portal redirect failed:", error);
      toast.error(t('failed') + " to open billing portal", error.message || "Please try again later");
      setIsOpeningPortal(false);
    }
  }

  function formatCurrency(amount: number, currency: string = 'usd'): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase(),
    }).format(amount / 100);
  }

  function formatDate(dateString?: string): string {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
      </div>
    );
  }

  const hasSubscription = subscription !== null;
  const planName = subscription?.status === 'active' ? 'Pro Plan' : 'Free Plan';
  const statusColor = subscription?.status === 'active'
    ? 'bg-[var(--accent-green)] text-black'
    : subscription?.status === 'canceled'
    ? 'bg-red-500 text-white'
    : 'bg-yellow-500 text-black';

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div>
        <h2 className="text-xl font-bold mb-1">Billing & Subscription</h2>
        <p className="text-sm text-[var(--text-secondary)]">Manage your plan and payment methods.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 p-6 bg-gradient-to-br from-[var(--bg-card)] to-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl relative overflow-hidden">
          <div className="relative z-10">
            <div className="flex justify-between items-start mb-6">
              <div>
                <div className="text-xs text-[var(--text-secondary)] uppercase font-bold mb-2">Current Plan</div>
                <h3 className="text-3xl font-bold mb-1">{planName}</h3>
                {hasSubscription && subscription.current_period_end && (
                  <p className="text-sm text-[var(--text-secondary)]">
                    Renews on {formatDate(subscription.current_period_end)}
                    {subscription.cancel_at_period_end && ' (' + t('cancel') + 's at period end)'}
                  </p>
                )}
                {!hasSubscription && (
                  <p className="text-sm text-[var(--text-secondary)]">{t('noActiveSubscription')}</p>
                )}
              </div>
              <span className={`px-3 py-1 font-bold text-xs rounded-full capitalize ${statusColor}`}>
                {subscription?.status || "Free"}
              </span>
            </div>
            <div className="flex gap-3">
              {!hasSubscription ? (
                <button
                  onClick={handleUpgrade}
                  disabled={isUpgrading}
                  className="px-4 py-2 bg-[var(--text-primary)] text-black font-bold rounded-lg text-sm hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isUpgrading && <Loader2 className="w-4 h-4 animate-spin" />}
                  {isUpgrading ? 'Redirecting...' : 'Upgrade to Pro'}
                </button>
              ) : (
                <>
                  <button
                    onClick={handleManageBilling}
                    disabled={isOpeningPortal}
                    className="px-4 py-2 bg-[var(--text-primary)] text-black font-bold rounded-lg text-sm hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {isOpeningPortal && <Loader2 className="w-4 h-4 animate-spin" />}
                    {isOpeningPortal ? 'Opening...' : 'Manage Billing'}
                  </button>
                  {!subscription.cancel_at_period_end && (
                    <button
                      onClick={handleManageBilling}
                      disabled={isOpeningPortal}
                      className="px-4 py-2 bg-transparent border border-[var(--border-color)] text-[var(--text-primary)] font-medium rounded-lg text-sm hover:bg-[var(--bg-card)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {t('cancel')} Subscription
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        <div className="p-6 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl flex flex-col justify-between">
          <div>
            <div className="text-xs text-[var(--text-secondary)] uppercase font-bold mb-4">Payment Method</div>
            {hasSubscription ? (
              <div className="mb-4">
                <p className="text-sm text-[var(--text-secondary)]">
                  Payment method is managed through Stripe.
                </p>
              </div>
            ) : (
              <p className="text-sm text-[var(--text-secondary)] mb-4">
                No payment method on file
              </p>
            )}
          </div>
          {hasSubscription && (
            <button
              onClick={handleManageBilling}
              disabled={isOpeningPortal}
              className="text-sm text-[var(--accent-blue)] hover:underline text-left disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('updatePaymentMethod')}
            </button>
          )}
        </div>
      </div>

      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden">
        <div className="p-4 border-b border-[var(--border-color)]">
          <h3 className="text-sm font-bold">{t('billingHistory')}</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-[var(--bg-panel)] text-[var(--text-secondary)] uppercase text-xs">
              <tr>
                <th className="px-6 py-3 font-medium">{t('date')}</th>
                <th className="px-6 py-3 font-medium">Invoice ID</th>
                <th className="px-6 py-3 font-medium">Period</th>
                <th className="px-6 py-3 font-medium">Amount</th>
                <th className="px-6 py-3 font-medium">{t("status")}</th>
                <th className="px-6 py-3 font-medium text-right">Invoice</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-color)]">
              {invoices.length > 0 ? invoices.map((invoice) => (
                <tr key={invoice.id} className="hover:bg-[var(--bg-panel)] transition-colors">
                  <td className="px-6 py-4 font-mono text-xs text-[var(--text-secondary)]">
                    {formatDate(invoice.created_at)}
                  </td>
                  <td className="px-6 py-4 font-mono text-xs text-[var(--text-secondary)]">
                    {invoice.stripe_invoice_id}
                  </td>
                  <td className="px-6 py-4 text-xs text-[var(--text-secondary)]">
                    {formatDate(invoice.period_start)} - {formatDate(invoice.period_end)}
                  </td>
                  <td className="px-6 py-4 font-bold">
                    {formatCurrency(invoice.amount, invoice.currency)}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                      invoice.status === 'paid'
                        ? 'bg-green-900/20 text-green-400 border border-green-900/50'
                        : invoice.status === 'open'
                        ? 'bg-yellow-900/20 text-yellow-400 border border-yellow-900/50'
                        : 'bg-red-900/20 text-red-400 border border-red-900/50'
                    }`}>
                      {invoice.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    {invoice.invoice_pdf && (
                      <a
                        href={invoice.invoice_pdf}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex items-center justify-end gap-1 ml-auto group"
                      >
                        <span className="text-xs group-hover:underline">{t('download')}</span>
                        <Download className="w-3 h-3" />
                      </a>
                    )}
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-[var(--text-secondary)]">
                    No billing history available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
