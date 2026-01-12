"use client";

import React from "react";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { useTranslations } from "next-intl";


function TermsOfServicePage() {
  const t = useTranslations('terms');
  return (
    <PublicLayout>
      <div className="py-24 px-6 max-w-4xl mx-auto">
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold mb-4">{t('termsOfService')}</h1>
          <p className="text-[var(--text-secondary)]">Last updated: December 21, 2025</p>
        </div>

        <div className="prose prose-invert prose-lg max-w-none space-y-8">
          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">{t('acceptanceOfTerms')}</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>By accessing or using FinanceAI's services, you agree to be bound by these {t('termsOfService')} and all applicable laws and regulations. If you do not agree with any of these terms, you are prohibited from using our services.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">2. Description of Service</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>FinanceAI provides an AI-powered platform for financial analysis and research. Our services include:</p>
              <ul className="list-disc pl-6 space-y-2">
                <li>Autonomous AI agent crews for financial research</li>
                <li>Visual crew builder interface</li>
                <li>Integration with financial data sources</li>
                <li>{t('analysisReportGeneration')}</li>
                <li>API access for programmatic usage</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">3. User Accounts</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>To use our services, you must create an account. You are responsible for:</p>
              <ul className="list-disc pl-6 space-y-2">
                <li>Maintaining the confidentiality of your account credentials</li>
                <li>{t('allActivitiesAccount')}</li>
                <li>{t('notifyingUnauthorizedUse')}</li>
                <li>Providing accurate and complete information</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">4. Acceptable Use</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>You agree not to use our services for:</p>
              <ul className="list-disc pl-6 space-y-2">
                <li>Any unlawful purpose or in violation of any applicable laws</li>
                <li>{t('marketManipulation')}</li>
                <li>Attempting to gain unauthorized access to our systems</li>
                <li>Distributing malware or conducting cyberattacks</li>
                <li>Reverse engineering or attempting to extract our proprietary algorithms</li>
                <li>Exceeding rate limits or attempting to overload our infrastructure</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">5. Financial Disclaimer</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <p className="font-semibold text-yellow-400 mb-2">{t('importantInvestmentDisclaimer')}</p>
                <p>FinanceAI provides analysis tools and information for educational and research purposes only. Our services do not constitute financial advice, investment recommendations, or trading signals. All investment decisions are your responsibility.</p>
              </div>
              <ul className="list-disc pl-6 space-y-2">
                <li>Past performance does not guarantee future results</li>
                <li>{t('allInvestmentsCarryRisk')}</li>
                <li>Consult with qualified financial advisors before making investment decisions</li>
                <li>We are not a registered investment advisor</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">6. Subscription and Billing</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>For paid services:</p>
              <ul className="list-disc pl-6 space-y-2">
                <li>Subscriptions automatically renew unless cancelled</li>
                <li>You can cancel anytime through your account settings</li>
                <li>Refunds are provided according to our refund policy</li>
                <li>Price changes will be communicated 30 days in advance</li>
                <li>Usage-based charges are billed monthly in arrears</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">7. Intellectual Property</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>FinanceAI retains all rights to our platform, algorithms, and proprietary technology. You retain rights to your input data and analysis results. By using our services, you grant us a limited license to process your data to provide the requested services.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">8. Limitation of Liability</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>To the maximum extent permitted by law, FinanceAI shall not be liable for any indirect, incidental, special, or consequential damages, including but not limited to trading losses, lost profits, or business interruption.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">9. Termination</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>We may terminate or suspend your account immediately if you violate these terms. Upon termination, your right to use our services ceases, and we may delete your account data according to our data retention policy.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">10. {t('contactInformation')}</h2>
            <div className="text-[var(--text-secondary)]">
              <p>For questions about these {t('termsOfService')}, contact us at:</p>
              <div className="mt-4 p-4 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg">
                <p><strong>{t('email')}</strong> legal@financeai.com</p>
                <p><strong>{t('address')}</strong> FinanceAI Inc., 123 Wall Street, New York, NY 10005</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </PublicLayout>
  );
}

export default TermsOfServicePage;
