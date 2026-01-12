"use client";

import { AlertCircle, AlertTriangle, ExternalLink } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { Link } from "@/i18n/routing";

interface ToolHallucinationWarningProps {
  toolCallsCount: number;
  expectedTools: number;
  status: string;
  hints?: string[];
}

/**
 * 🔒 Fix 5: Tool Hallucination Warning Component
 *
 * Displays a critical warning when an agent completes execution without
 * calling any tools, indicating potential hallucination from LLM training data.
 */
export function ToolHallucinationWarning({
  toolCallsCount,
  expectedTools,
  status,
  hints = [],
}: ToolHallucinationWarningProps) {
  // Only show warning if:
  // 1. Agent has tools configured (expected > 0)
  // 2. No tools were called (actual = 0)
  // 3. Job completed (not failed/running)
  const shouldShowWarning =
    expectedTools > 0 && toolCallsCount === 0 && status === "completed";

  if (!shouldShowWarning) {
    return null;
  }

  return (
    <Alert variant="destructive" className="border-2 border-red-500 bg-red-50">
      <AlertCircle className="h-5 w-5" />
      <AlertTitle className="text-lg font-bold">
        ⚠️ Hallucination Risk Detected
      </AlertTitle>
      <AlertDescription className="space-y-3">
        <p className="text-sm">
          This agent was configured with <strong>{expectedTools} tool(s)</strong> but
          made <strong className="text-red-600">ZERO tool calls</strong> during
          execution. The output may contain{" "}
          <strong>fabricated data from LLM training knowledge</strong> instead of
          real-time data.
        </p>

        {hints.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-semibold">Possible Causes:</p>
            <ul className="list-disc list-inside space-y-1 text-sm">
              {hints
                .filter((hint) => hint.includes("HALLUCINATION") || hint.includes("tool"))
                .map((hint, index) => (
                  <li key={index} className="text-muted-foreground">
                    {hint.replace(/^⚠️\s*HALLUCINATION RISK:\s*/i, "")}
                  </li>
                ))}
            </ul>
          </div>
        )}

        <div className="space-y-2 pt-2 border-t border-red-200">
          <p className="text-sm font-semibold">Recommended Actions:</p>
          <ol className="list-decimal list-inside space-y-1 text-sm">
            <li>
              <strong>Verify Provider:</strong> Ensure your LLM provider supports
              function calling (OpenAI, Anthropic, Google recommended)
            </li>
            <li>
              <strong>Check Logs:</strong> Review backend logs for tool loading errors
            </li>
            <li>
              <strong>Task Description:</strong> Ensure task clearly instructs agent to
              use tools (e.g., "Use the get_stock_price tool to fetch...")
            </li>
            <li>
              <strong>Validate Output:</strong> Cross-check any data/dates in the output
              against external sources
            </li>
          </ol>
        </div>

        <Link
          href="/docs/troubleshooting#no-tool-calls"
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 underline"
        >
          <ExternalLink className="h-3 w-3" />
          View Troubleshooting Guide
        </Link>
      </AlertDescription>
    </Alert>
  );
}

/**
 * Compact version for use in list views
 */
export function ToolHallucinationBadge({
  toolCallsCount,
  expectedTools,
  status,
}: {
  toolCallsCount: number;
  expectedTools: number;
  status: string;
}) {
  const shouldShowBadge =
    expectedTools > 0 && toolCallsCount === 0 && status === "completed";

  if (!shouldShowBadge) {
    return null;
  }

  return (
    <div className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium">
      <AlertTriangle className="h-3 w-3" />
      Hallucination Risk
    </div>
  );
}
