"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/routing";
import { useTranslations } from "next-intl";

// Redirect to unified MCP management page
export default function DataSourcesPage() {
  const router = useRouter();
  const t = useTranslations('common');

  useEffect(() => {
    router.replace("/mcp");
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-muted-foreground">{t('redirectingToMCP')}</p>
    </div>
  );
}
