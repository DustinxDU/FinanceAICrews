"use client";

import React from "react";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { useTranslations } from "next-intl";


function PrivacyPolicyPage() {
  const t = useTranslations('privacy');
  return (
    <PublicLayout>
      <div className="py-24 px-6 max-w-4xl mx-auto">
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold mb-4">{t('privacyPolicy')}</h1>
          <p className="text-[var(--text-secondary)]">Last updated: December 21, 2025</p>
        </div>

        <div className="prose prose-invert prose-lg max-w-none space-y-8">
          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">1. Information We Collect</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>We collect information you provide directly to us, such as when you create an account, use our services, or contact us for support.</p>
              <ul className="list-disc pl-6 space-y-2">
                <li><strong>Account Information:</strong> {t('emailAddressNamePassword')}</li>
                <li><strong>Usage Data:</strong> Information about how you use our platform, including crew configurations and analysis requests</li>
                <li><strong>{t('technicalData')}</strong> IP address, browser type, device information, and usage analytics</li>
                <li><strong>Financial Data:</strong> Only the ticker symbols and analysis parameters you input - we never store your personal financial information</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">2. How We Use Your Information</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>We use the information we collect to:</p>
              <ul className="list-disc pl-6 space-y-2">
                <li>Provide, maintain, and improve our services</li>
                <li>Process your analysis requests and deliver results</li>
                <li>Send you technical notices and support messages</li>
                <li>Monitor and analyze usage patterns to improve our platform</li>
                <li>Ensure security and prevent fraud</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">3. Data Security</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>We implement industry-standard security measures to protect your information:</p>
              <ul className="list-disc pl-6 space-y-2">
                <li><strong>Encryption:</strong> All data is encrypted in transit and at rest using AES-256</li>
                <li><strong>Access Controls:</strong> Strict access controls and authentication requirements</li>
                <li><strong>SOC2 Compliance:</strong> We maintain SOC2 Type II certification</li>
                <li><strong>BYOK Support:</strong> Enterprise customers can bring their own encryption keys</li>
                <li><strong>Regular Audits:</strong> Third-party security audits and penetration testing</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">4. AI Model Training</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p className="font-semibold text-[var(--accent-green)]">Your data never trains our models.</p>
              <p>We want to be crystal clear about this: None of your input data, analysis results, or usage patterns are used to train or improve AI models. Your financial analysis requests and results remain completely private to your account.</p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">5. Data Sharing</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>We do not sell, trade, or otherwise transfer your personal information to third parties except:</p>
              <ul className="list-disc pl-6 space-y-2">
                <li>With your explicit consent</li>
                <li>To comply with legal obligations</li>
                <li>To protect our rights and prevent fraud</li>
                <li>With service providers who assist in our operations (under strict confidentiality agreements)</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">6. Your Rights</h2>
            <div className="text-[var(--text-secondary)] space-y-4">
              <p>You have the right to:</p>
              <ul className="list-disc pl-6 space-y-2">
                <li>Access your personal information</li>
                <li>Correct inaccurate information</li>
                <li>{t('deleteYourAccount')}</li>
                <li>{t('exportYourData')}</li>
                <li>Opt out of non-essential communications</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">7. Contact Us</h2>
            <div className="text-[var(--text-secondary)]">
              <p>If you have any questions about this {t('privacyPolicy')}, please contact us at:</p>
              <div className="mt-4 p-4 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg">
                <p><strong>{t('email')}</strong> privacy@financeai.com</p>
                <p><strong>{t('address')}</strong> FinanceAI Inc., 123 Wall Street, New York, NY 10005</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </PublicLayout>
  );
}

export default PrivacyPolicyPage;
