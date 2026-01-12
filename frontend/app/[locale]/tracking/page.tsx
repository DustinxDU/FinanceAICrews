"use client";

import { useState, useEffect } from "react";
import { Link } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import {
  ArrowLeft,
  Activity,
  Clock,
  CheckCircle2,
  XCircle,
  Wrench,
  Cpu,
  BarChart3,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import apiClient, { TrackingHistoryItem, CompletionReport, LiveStatus } from "@/lib/api";
import { formatDate, getCrewDisplayName } from "@/lib/utils";

export default function TrackingPage() {
  const t = useTranslations('tracking');
  const [history, setHistory] = useState<TrackingHistoryItem[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [report, setReport] = useState<CompletionReport | null>(null);
  const [liveStatus, setLiveStatus] = useState<LiveStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedSection, setExpandedSection] = useState<string | null>("tools");

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    if (selectedJobId) {
      loadJobDetails(selectedJobId);
    }
  }, [selectedJobId]);

  useEffect(() => {
    if (!liveStatus || liveStatus.status !== "running") return;

    const interval = setInterval(async () => {
      if (selectedJobId) {
        try {
          const status = await apiClient.getLiveStatus(selectedJobId);
          setLiveStatus(status);
          if (status.status !== "running") {
            const fullReport = await apiClient.getCompletionReport(selectedJobId);
            setReport(fullReport);
          }
        } catch (error) {
          console.error("Failed to poll status:", error);
        }
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [liveStatus, selectedJobId]);

  const loadHistory = async () => {
    try {
      const data = await apiClient.listTrackingHistory(30);
      setHistory(data);
    } catch (error) {
      console.error("Failed to load history:", error);
    }
  };

  const loadJobDetails = async (jobId: string) => {
    setIsLoading(true);
    try {
      const status = await apiClient.getLiveStatus(jobId);
      setLiveStatus(status);

      if (status.status === "completed" || status.status === "failed") {
        const fullReport = await apiClient.getCompletionReport(jobId);
        setReport(fullReport);
      } else {
        setReport(null);
      }
    } catch (error) {
      console.error("Failed to load job details:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDuration = (ms: number | undefined): string => {
    if (!ms) return "-";
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <Badge variant="success">{t('completed')}</Badge>;
      case "running":
        return <Badge variant="info">{t('running')}</Badge>;
      case "failed":
        return <Badge variant="destructive">{t('failed')}</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur">
        <div className="container flex h-14 items-center px-4">
          <Link href="/" className="flex items-center gap-2 text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" />
            <span>{t('backToWorkbench')}</span>
          </Link>
          <div className="ml-4 flex items-center gap-2">
            <Activity className="h-5 w-5" />
            <h1 className="text-lg font-semibold">{t('taskTracking')}</h1>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto"
            onClick={loadHistory}
          >
            <RefreshCw className="h-4 w-4 mr-1" />
            {t('refresh')}
          </Button>
        </div>
      </header>

      <main className="container py-6 px-4">
        <div className="grid gap-6 lg:grid-cols-3">
          {/* History List */}
          <div className="lg:col-span-1">
            <h2 className="text-lg font-semibold mb-4">{t('executionHistory')}</h2>
            <div className="space-y-2">
              {history.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>{t('noRecords')}</p>
                  </CardContent>
                </Card>
              ) : (
                history.map((item) => (
                  <Card
                    key={item.job_id}
                    className={`cursor-pointer transition-colors hover:bg-muted/50 ${
                      selectedJobId === item.job_id ? "border-primary" : ""
                    }`}
                    onClick={() => setSelectedJobId(item.job_id)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium">{item.ticker}</span>
                        {getStatusBadge(item.status)}
                      </div>
                      <div className="text-xs text-muted-foreground space-y-0.5">
                        <p>{getCrewDisplayName(item.crew_name)}</p>
                        <p>{formatDate(item.started_at)}</p>
                        <div className="flex gap-3 mt-1">
                          <span className="flex items-center gap-1">
                            <Wrench className="h-3 w-3" />
                            {item.tool_calls}
                          </span>
                          <span className="flex items-center gap-1">
                            <Cpu className="h-3 w-3" />
                            {item.llm_calls}
                          </span>
                          <span className="flex items-center gap-1">
                            <BarChart3 className="h-3 w-3" />
                            {item.total_tokens}
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </div>

          {/* Detail Panel */}
          <div className="lg:col-span-2">
            {!selectedJobId ? (
              <Card>
                <CardContent className="py-16 text-center text-muted-foreground">
                  <BarChart3 className="h-16 w-16 mx-auto mb-4 opacity-50" />
                  <h3 className="text-lg font-medium mb-2">{t('selectRecord')}</h3>
                  <p className="text-sm">{t('fromLeftList')}</p>
                </CardContent>
              </Card>
            ) : isLoading ? (
              <Card>
                <CardContent className="py-16 text-center">
                  <RefreshCw className="h-8 w-8 mx-auto mb-4 animate-spin text-primary" />
                  <p>{t('loading')}</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {/* Task Overview */}
                <Card>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">
                        {liveStatus?.ticker} - {getCrewDisplayName(liveStatus?.crew_name || "")}
                      </CardTitle>
                      {getStatusBadge(liveStatus?.status || "")}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-4 gap-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-primary">
                          {liveStatus?.tool_call_count || 0}
                        </div>
                        <div className="text-xs text-muted-foreground">{t('toolCalls')}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-500">
                          {liveStatus?.llm_call_count || 0}
                        </div>
                        <div className="text-xs text-muted-foreground">{t('llmCalls')}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-500">
                          {liveStatus?.total_tokens || 0}
                        </div>
                        <div className="text-xs text-muted-foreground">{t('totalTokens')}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-orange-500">
                          {formatDuration(liveStatus?.elapsed_ms || (report?.duration_seconds ? report.duration_seconds * 1000 : undefined))}
                        </div>
                        <div className="text-xs text-muted-foreground">{t('duration')}</div>
                      </div>
                    </div>

                    {/* Realtime Progress */}
                    {liveStatus?.status === "running" && (
                      <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                          <span className="text-sm font-medium">{t('executing')}</span>
                        </div>
                        {liveStatus.current_agent && (
                          <p className="text-sm text-muted-foreground">
                            <strong>{liveStatus.current_agent}</strong>: {liveStatus.current_activity}
                          </p>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Realtime Activity Stream */}
                {liveStatus?.status === "running" && liveStatus.recent_activities.length > 0 && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base flex items-center gap-2">
                        <Activity className="h-4 w-4" />
                        {t('realtimeActivity')}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2 max-h-60 overflow-y-auto">
                        {liveStatus.recent_activities.slice().reverse().map((activity, index) => (
                          <div key={index} className="flex gap-3 text-sm">
                            <span className="text-xs text-muted-foreground w-16 shrink-0">
                              {new Date(activity.timestamp).toLocaleTimeString()}
                            </span>
                            <Badge variant="secondary" className="text-xs shrink-0">
                              {activity.agent}
                            </Badge>
                            <span className="text-muted-foreground truncate">
                              {activity.message}
                            </span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Completion Report */}
                {report && (
                  <>
                    {/* Tool Statistics */}
                    <Card>
                      <CardHeader
                        className="pb-2 cursor-pointer"
                        onClick={() => setExpandedSection(expandedSection === "tools" ? null : "tools")}
                      >
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-base flex items-center gap-2">
                            <Wrench className="h-4 w-4" />
                            {t('toolUsageStats')}
                          </CardTitle>
                          {expandedSection === "tools" ? (
                            <ChevronUp className="h-4 w-4" />
                          ) : (
                            <ChevronDown className="h-4 w-4" />
                          )}
                        </div>
                      </CardHeader>
                      {expandedSection === "tools" && (
                        <CardContent>
                          <div className="grid grid-cols-3 gap-4 mb-4">
                            <div className="text-center p-3 bg-muted rounded-lg">
                              <div className="text-xl font-bold">{report.tools_summary.total_calls}</div>
                              <div className="text-xs text-muted-foreground">{t('totalCalls')}</div>
                            </div>
                            <div className="text-center p-3 bg-green-50 rounded-lg">
                              <div className="text-xl font-bold text-green-600">
                                {report.tools_summary.success}
                              </div>
                              <div className="text-xs text-muted-foreground">{t('success')}</div>
                            </div>
                            <div className="text-center p-3 bg-red-50 rounded-lg">
                              <div className="text-xl font-bold text-red-600">
                                {report.tools_summary.failed}
                              </div>
                              <div className="text-xs text-muted-foreground">{t('failed')}</div>
                            </div>
                          </div>

                          <div className="space-y-2">
                            {Object.entries(report.tools_summary.by_tool).map(([toolName, data]) => (
                              <div key={toolName} className="flex items-center gap-3">
                                <span className="text-sm font-medium w-40 truncate">{toolName}</span>
                                <div className="flex-1">
                                  <Progress
                                    value={(data.success / data.count) * 100}
                                    className="h-2"
                                  />
                                </div>
                                <div className="flex items-center gap-2 text-xs w-32 justify-end">
                                  <span className="text-green-600">{data.success}</span>
                                  <span>/</span>
                                  <span>{data.count}</span>
                                  <span className="text-muted-foreground">
                                    ({formatDuration(data.avg_duration_ms)})
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>

                          {report.tool_calls.length > 0 && (
                            <div className="mt-4">
                              <h4 className="text-sm font-medium mb-2">{t('toolDetails')}</h4>
                              <div className="max-h-40 overflow-y-auto border rounded-md">
                                <table className="w-full text-xs">
                                  <thead className="bg-muted sticky top-0">
                                    <tr>
                                      <th className="p-2 text-left">{t('time')}</th>
                                      <th className="p-2 text-left">{t('tool')}</th>
                                      <th className="p-2 text-left">Agent</th>
                                      <th className="p-2 text-left">{t('status')}</th>
                                      <th className="p-2 text-right">{t('durationMs')}</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {report.tool_calls.map((call, index) => (
                                      <tr key={index} className="border-t">
                                        <td className="p-2">
                                          {call.timestamp ? new Date(call.timestamp).toLocaleTimeString() : "-"}
                                        </td>
                                        <td className="p-2 font-medium">{call.tool_name}</td>
                                        <td className="p-2">{call.agent_name}</td>
                                        <td className="p-2">
                                          {call.status === "success" ? (
                                            <CheckCircle2 className="h-3 w-3 text-green-500" />
                                          ) : (
                                            <XCircle className="h-3 w-3 text-red-500" />
                                          )}
                                        </td>
                                        <td className="p-2 text-right">
                                          {formatDuration(call.duration_ms)}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}
                        </CardContent>
                      )}
                    </Card>

                    {/* LLM Statistics */}
                    <Card>
                      <CardHeader
                        className="pb-2 cursor-pointer"
                        onClick={() => setExpandedSection(expandedSection === "llm" ? null : "llm")}
                      >
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-base flex items-center gap-2">
                            <Cpu className="h-4 w-4" />
                            {t('llmUsageStats')}
                          </CardTitle>
                          {expandedSection === "llm" ? (
                            <ChevronUp className="h-4 w-4" />
                          ) : (
                            <ChevronDown className="h-4 w-4" />
                          )}
                        </div>
                      </CardHeader>
                      {expandedSection === "llm" && (
                        <CardContent>
                          <div className="grid grid-cols-4 gap-4 mb-4">
                            <div className="text-center p-3 bg-muted rounded-lg">
                              <div className="text-xl font-bold">{report.llm_summary.total_calls}</div>
                              <div className="text-xs text-muted-foreground">{t('totalCalls')}</div>
                            </div>
                            <div className="text-center p-3 bg-blue-50 rounded-lg">
                              <div className="text-xl font-bold text-blue-600">
                                {report.llm_summary.prompt_tokens}
                              </div>
                              <div className="text-xs text-muted-foreground">Prompt Tokens</div>
                            </div>
                            <div className="text-center p-3 bg-purple-50 rounded-lg">
                              <div className="text-xl font-bold text-purple-600">
                                {report.llm_summary.completion_tokens}
                              </div>
                              <div className="text-xs text-muted-foreground">Completion Tokens</div>
                            </div>
                            <div className="text-center p-3 bg-green-50 rounded-lg">
                              <div className="text-xl font-bold text-green-600">
                                {report.llm_summary.total_tokens}
                              </div>
                              <div className="text-xs text-muted-foreground">{t('totalTokens')}</div>
                            </div>
                          </div>

                          <div className="space-y-2">
                            {Object.entries(report.llm_summary.by_model).map(([modelName, data]) => (
                              <div key={modelName} className="flex items-center justify-between p-2 bg-muted/50 rounded">
                                <span className="text-sm font-medium">{modelName}</span>
                                <div className="flex items-center gap-4 text-xs">
                                  <span>{data.count} {t('calls')}</span>
                                  <span className="text-blue-600">{data.tokens} tokens</span>
                                  <span className="text-muted-foreground">
                                    avg {formatDuration(data.avg_duration_ms)}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>

                          {report.llm_calls.length > 0 && (
                            <div className="mt-4">
                              <h4 className="text-sm font-medium mb-2">{t('toolDetails')}</h4>
                              <div className="max-h-40 overflow-y-auto border rounded-md">
                                <table className="w-full text-xs">
                                  <thead className="bg-muted sticky top-0">
                                    <tr>
                                      <th className="p-2 text-left">{t('time')}</th>
                                      <th className="p-2 text-left">{t('model')}</th>
                                      <th className="p-2 text-left">Agent</th>
                                      <th className="p-2 text-right">Tokens</th>
                                      <th className="p-2 text-right">{t('durationMs')}</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {report.llm_calls.map((call, index) => (
                                      <tr key={index} className="border-t">
                                        <td className="p-2">
                                          {call.timestamp ? new Date(call.timestamp).toLocaleTimeString() : "-"}
                                        </td>
                                        <td className="p-2 font-medium">{call.provider}/{call.model}</td>
                                        <td className="p-2">{call.agent_name}</td>
                                        <td className="p-2 text-right">{call.tokens || "-"}</td>
                                        <td className="p-2 text-right">
                                          {formatDuration(call.duration_ms)}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}
                        </CardContent>
                      )}
                    </Card>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
