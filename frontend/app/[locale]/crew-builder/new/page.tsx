"use client";

import { AppLayout } from "@/components/layout";
import { withAuth } from "@/contexts/AuthContext";
import { CrewBuilderNew } from "@/components/crew-builder";

function CrewBuilderNewPage() {
  return (
    <AppLayout>
      <CrewBuilderNew />
    </AppLayout>
  );
}

export default withAuth(CrewBuilderNewPage);
