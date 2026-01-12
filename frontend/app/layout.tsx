import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import {routing} from '@/i18n/routing';
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import { ToastProvider } from "@/lib/toast";
import { ThemeProvider } from "@/contexts/ThemeContext";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FinanceAI Platform",
  description: "AI-Powered Financial Analysis Platform",
};

export default async function RootLayout({
  children,
  params
}: {
  children: React.ReactNode;
  params: Promise<{locale?: string}>;
}) {
  const {locale} = await params;
  const validLocale = locale || 'en';
  const messages = await getMessages();

  return (
    <html lang={validLocale} className="dark">
      <body className={inter.className}>
        <NextIntlClientProvider messages={messages} locale={validLocale}>
          <ToastProvider>
            <AuthProvider>
              <ThemeProvider>
                {children}
              </ThemeProvider>
            </AuthProvider>
          </ToastProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
