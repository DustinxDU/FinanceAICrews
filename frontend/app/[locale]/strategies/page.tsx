"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/routing";
import { useTranslations } from "next-intl";

// Redirect to unified Tools page with strategies tab
export default function StrategiesPage() {
  const t = useTranslations('library');
  const router = useRouter();

  useEffect(() => {
    router.replace("/tools?tab=strategies");
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-muted-foreground">{t('redirecting')}</p>
    </div>
  );
}
