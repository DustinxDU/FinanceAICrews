"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, CheckCircle2, Loader2, Clock } from "lucide-react";
import { getStatusText, getCrewDisplayName, formatDate } from "@/lib/utils";
import { JobStatus } from "@/lib/api";
import { CitationHighlight } from "@/components/CitationHighlight";

interface ReportViewerProps {
  job: JobStatus | null;
}

export function ReportViewer({ job }: ReportViewerProps) {
  if (!job) {
    return (
      <div className="flex-1 flex items-center justify-center bg-muted/20">
        <div className="text-center text-muted-foreground">
          <div className="text-4xl mb-4">📊</div>
          <h3 className="text-lg font-medium mb-2">Select or Create Analysis Task</h3>
          <p className="text-sm">Select a historical task from the left to view reports, or create a new analysis</p>
        </div>
      </div>
    );
  }

  const renderStatusIcon = () => {
    switch (job.status) {
      case "completed":
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case "running":
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      case "failed":
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-yellow-500" />;
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b bg-background p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {renderStatusIcon()}
            <div>
              <h2 className="text-xl font-bold">{job.ticker}</h2>
              <p className="text-sm text-muted-foreground">
                {getCrewDisplayName(job.crew_name || "standard")} · {formatDate(job.created_at)}
              </p>
            </div>
          </div>
          <Badge
            variant={
              job.status === "completed"
                ? "success"
                : job.status === "running"
                ? "info"
                : job.status === "failed"
                ? "destructive"
                : "secondary"
            }
          >
            {getStatusText(job.status)}
          </Badge>
        </div>

        {/* Progress Bar */}
        {(job.status === "running" || job.status === "pending") && (
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-muted-foreground">{job.progress_message}</span>
              <span className="font-medium">{job.progress}%</span>
            </div>
            <Progress value={job.progress} />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {job.status === "running" || job.status === "pending" ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Loader2 className="h-5 w-5 animate-spin" />
                AI Agents are analyzing...
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-muted-foreground">
                  Multiple AI agents are collaborating to analyze {job.ticker}, this may take 3-5 minutes.
                </p>
                <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                    <span>Fundamental Analyst is researching financial data...</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <div className="h-2 w-2 rounded-full bg-muted-foreground" />
                    <span>Technical Analyst waiting...</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <div className="h-2 w-2 rounded-full bg-muted-foreground" />
                    <span>Risk Evaluator waiting...</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ) : job.status === "failed" ? (
          <Card className="border-red-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-red-600">
                <AlertCircle className="h-5 w-5" />
                Analysis Failed
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground mb-4">Sorry, an error occurred during analysis:</p>
              <div className="bg-red-50 text-red-800 rounded-lg p-4 font-mono text-sm">
                {job.error || "Unknown Error"}
              </div>
            </CardContent>
          </Card>
        ) : job.result ? (
          <div className="markdown-content prose prose-slate dark:prose-invert max-w-none">
            {/* Check for citation markers, use CitationHighlight if present */}
            {job.result.includes("[Source:") ? (
              <CitationHighlight
                text={job.result}
                citations={job.structured_result?.citations}
              />
            ) : (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{job.result}</ReactMarkdown>
            )}
          </div>
        ) : (
          <div className="text-center text-muted-foreground py-12">
            <p>No analysis results yet</p>
          </div>
        )}
      </div>
    </div>
  );
}
