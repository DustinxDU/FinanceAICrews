"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/routing";
import { useTranslations } from "next-intl";

// Redirect to unified Tools page
export default function MCPPage() {
  const router = useRouter();
  const t = useTranslations('common');

  useEffect(() => {
    router.replace("/tools");
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-muted-foreground">{t('redirectingToTools')}</p>
    </div>
  );
}
