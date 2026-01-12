"use client";

import { useState } from "react";
import { Link } from "@/i18n/routing";
import { Plus, History, Settings, TrendingUp, Users, Activity, Database, Store } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { cn, getStatusColor, getStatusText, getCrewDisplayName, formatDate } from "@/lib/utils";
import { JobStatus } from "@/lib/api";
import UserMenu from "@/components/UserMenu";

interface SidebarProps {
  jobs: JobStatus[];
  selectedJobId: string | null;
  onSelectJob: (jobId: string) => void;
  onStartAnalysis: (ticker: string, crewName: string) => void;
  isLoading: boolean;
  crews: string[];
}

export function Sidebar({
  jobs,
  selectedJobId,
  onSelectJob,
  onStartAnalysis,
  isLoading,
  crews,
}: SidebarProps) {
  const [ticker, setTicker] = useState("");
  const [crewName, setCrewName] = useState("standard");
  const [showForm, setShowForm] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (ticker.trim()) {
      onStartAnalysis(ticker.trim().toUpperCase(), crewName);
      setTicker("");
      setShowForm(false);
    }
  };

  const crewOptions = crews.map((crew) => ({
    value: crew,
    label: getCrewDisplayName(crew),
  }));

  return (
    <aside className="w-80 border-r bg-muted/30 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="h-6 w-6 text-primary" />
          <h1 className="font-bold text-lg">FinanceAI</h1>
        </div>
        <Button
          onClick={() => setShowForm(!showForm)}
          className="w-full"
          variant={showForm ? "secondary" : "default"}
        >
          <Plus className="h-4 w-4 mr-2" />
          New Analysis
        </Button>
      </div>

      {/* New Analysis Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="p-4 border-b bg-background/50">
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium mb-1 block">Ticker</label>
              <Input
                placeholder="e.g., US:AAPL, CN:600519"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Analysis Strategy</label>
              <Select
                options={crewOptions}
                value={crewName}
                onChange={(e) => setCrewName(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading || !ticker.trim()}>
              {isLoading ? "Submitting..." : "Start Analysis"}
            </Button>
          </div>
        </form>
      )}

      {/* Job History */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-3 border-b">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <History className="h-4 w-4" />
            <span>History</span>
            <span className="ml-auto">{jobs.length}</span>
          </div>
        </div>
        <div className="divide-y">
          {jobs.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No analysis tasks
            </div>
          ) : (
            jobs.map((job) => (
              <button
                key={job.job_id}
                onClick={() => onSelectJob(job.job_id)}
                className={cn(
                  "w-full p-3 text-left hover:bg-muted/50 transition-colors",
                  selectedJobId === job.job_id && "bg-muted"
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium">{job.ticker || "Unknown"}</span>
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
                    className="text-xs"
                  >
                    {getStatusText(job.status)}
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground">
                  {getCrewDisplayName(job.crew_name || "standard")}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {formatDate(job.created_at)}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 border-t space-y-1">
        <Link href="/tracking">
          <Button variant="ghost" size="sm" className="w-full justify-start">
            <Activity className="h-4 w-4 mr-2" />
            Task Tracking
          </Button>
        </Link>
        <Link href="/crew-builder">
          <Button variant="ghost" size="sm" className="w-full justify-start">
            <Users className="h-4 w-4 mr-2" />
            Crew Builder
          </Button>
        </Link>
        <Link href="/tools">
          <Button variant="ghost" size="sm" className="w-full justify-start">
            <Database className="h-4 w-4 mr-2" />
            Extensions
          </Button>
        </Link>
        <Link href="/settings">
          <Button variant="ghost" size="sm" className="w-full justify-start">
            <Settings className="h-4 w-4 mr-2" />
            LLM Settings
          </Button>
        </Link>
      </div>

      {/* User Menu */}
      <div className="p-3 border-t bg-slate-900/50">
        <UserMenu />
      </div>
    </aside>
  );
}
