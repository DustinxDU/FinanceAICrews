"use client";

import React, { useEffect, useState } from "react";
import { AlertTriangle, Download, Loader2, RefreshCw, Trash2, X } from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import { useToast } from "@/lib/toast";
import type {
  PrivacyStatusResponse,
  DataExportJobResponse,
  DataExportListResponse,
} from "@/lib/types";

export function PrivacyTab() {
  const t = useTranslations("settings");
  const { error, success } = useToast();
  const [status, setStatus] = useState<PrivacyStatusResponse | null>(null);
  const [exports, setExports] = useState<DataExportJobResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRequestingExport, setIsRequestingExport] = useState(false);
  const [isRequestingDeletion, setIsRequestingDeletion] = useState(false);
  const [isCancelingDeletion, setIsCancelingDeletion] = useState(false);
  const [showDeletionConfirm, setShowDeletionConfirm] = useState(false);
  const [deletionReason, setDeletionReason] = useState("");

  useEffect(() => {
    void loadData();
  }, []);

  async function loadData() {
    setIsLoading(true);
    try {
      const [statusResp, exportsResp] = await Promise.all([
        apiClient.getPrivacyStatus(),
        apiClient.listDataExports(5),
      ]);
      setStatus(statusResp);
      setExports(exportsResp.jobs);
    } catch (err: any) {
      console.error("{t('failed')} to load privacy data:", err);
      error("Privacy", err?.message || "{t('failed')} to load privacy settings");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRequestExport() {
    try {
      setIsRequestingExport(true);
      await apiClient.requestDataExport({
        include_analysis_reports: true,
        include_portfolios: true,
        include_settings: true,
      });
      success("{t('dataExport')}", "Export request submitted. You will be notified when ready.");
      await loadData();
    } catch (err: any) {
      console.error("{t('failed')} to request export:", err);
      error("{t('dataExport')}", err?.message || "{t('failed')} to request data export");
    } finally {
      setIsRequestingExport(false);
    }
  }

  async function handleRequestDeletion() {
    try {
      setIsRequestingDeletion(true);
      await apiClient.requestAccountDeletion({
        reason: deletionReason || undefined,
        confirm: true,
      });
      success("Account Deletion", "Account deletion scheduled. You have 30 days to cancel.");
      setShowDeletionConfirm(false);
      setDeletionReason("");
      await loadData();
    } catch (err: any) {
      console.error("{t('failed')} to request deletion:", err);
      error("Account Deletion", err?.message || "{t('failed')} to schedule account deletion");
    } finally {
      setIsRequestingDeletion(false);
    }
  }

  async function handleCancelDeletion() {
    try {
      setIsCancelingDeletion(true);
      await apiClient.cancelAccountDeletion();
      success("Account Deletion", "Account deletion cancelled.");
      await loadData();
    } catch (err: any) {
      console.error("{t('failed')} to cancel deletion:", err);
      error("Account Deletion", err?.message || "{t('failed')} to cancel account deletion");
    } finally {
      setIsCancelingDeletion(false);
    }
  }

  function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function getStatusBadgeClass(exportStatus: string): string {
    switch (exportStatus) {
      case "completed":
        return "bg-green-900/20 text-green-400 border-green-900/50";
      case "pending":
      case "processing":
        return "bg-blue-900/20 text-blue-400 border-blue-900/50";
      case "failed":
      case "expired":
        return "bg-red-900/20 text-red-400 border-red-900/50";
      default:
        return "bg-zinc-900/20 text-zinc-400 border-zinc-800";
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h2 className="text-xl font-bold mb-1">{t('privacyAndData')}</h2>
        <p className="text-sm text-[var(--text-secondary)]">
          Export your data or manage account deletion requests.
        </p>
      </div>

      {/* {t('dataExport')} Section */}
      <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold flex items-center gap-2">
              <Download className="w-4 h-4" />
              {t('dataExport')}
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              {t('download')} a copy of your data including analysis reports, portfolios, and settings.
            </p>
          </div>
          <button
            onClick={loadData}
            className="text-xs flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            {t('refresh')}
          </button>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRequestExport}
            disabled={isRequestingExport || status?.has_pending_export}
            className="px-4 py-2 bg-[var(--accent-blue)] text-white rounded-lg text-sm font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRequestingExport ? "Requesting..." : "Request Export"}
          </button>
          {status?.has_pending_export && (
            <span className="text-xs text-[var(--text-secondary)]">
              {t('exportInProgress')}
            </span>
          )}
          {status?.last_export_at && !status.has_pending_export && (
            <span className="text-xs text-[var(--text-secondary)]">
              Last export: {formatDate(status.last_export_at)}
            </span>
          )}
        </div>

        {exports.length > 0 && (
          <div className="space-y-2 mt-4">
            <div className="text-xs font-medium text-[var(--text-secondary)]">Recent Exports</div>
            {exports.map((job) => (
              <div
                key={job.id}
                className="flex items-center justify-between text-sm border border-[var(--border-color)] rounded-lg px-3 py-2"
              >
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${getStatusBadgeClass(job.status)}`}>
                    {job.status}
                  </span>
                  <span className="text-xs text-[var(--text-secondary)]">
                    {formatDate(job.requested_at)}
                  </span>
                </div>
                {job.status === "completed" && job.download_url && (
                  <a
                    href={job.download_url}
                    className="text-xs text-[var(--accent-blue)] hover:underline"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {t('download')}
                  </a>
                )}
                {job.status === "failed" && job.error_message && (
                  <span className="text-xs text-red-400" title={job.error_message}>
                    {t('failed')}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Account Deletion Section */}
      <div className="p-4 bg-[var(--bg-card)] border border-red-900/30 rounded-lg space-y-4">
        <div>
          <h3 className="font-semibold flex items-center gap-2 text-red-400">
            <Trash2 className="w-4 h-4" />
            {t('deleteAccount')}
          </h3>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Permanently delete your account and all associated data. This action has a 30-day grace period.
          </p>
        </div>

        {status?.has_scheduled_deletion ? (
          <div className="p-3 bg-red-900/10 border border-red-900/30 rounded-lg space-y-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span className="text-sm font-medium text-red-400">
                Account deletion scheduled
              </span>
            </div>
            <div className="text-xs text-[var(--text-secondary)]">
              Your account will be deleted on{" "}
              <span className="font-medium text-[var(--text-primary)]">
                {formatDate(status.deletion_scheduled_for)}
              </span>
              {status.deletion_days_remaining !== null && (
                <> ({status.deletion_days_remaining} days remaining)</>
              )}
            </div>
            <button
              onClick={handleCancelDeletion}
              disabled={isCancelingDeletion}
              className="px-4 py-2 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg text-sm font-medium hover:bg-[var(--bg-card)] disabled:opacity-50"
            >
              {isCancelingDeletion ? "Cancelling..." : "Cancel Deletion"}
            </button>
          </div>
        ) : showDeletionConfirm ? (
          <div className="p-3 bg-red-900/10 border border-red-900/30 rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-red-400">
                Confirm account deletion
              </span>
              <button
                onClick={() => setShowDeletionConfirm(false)}
                className="p-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              This will schedule your account for deletion in 30 days. You can cancel anytime during this period.
            </p>
            <textarea
              value={deletionReason}
              onChange={(e) => setDeletionReason(e.target.value)}
              placeholder="Reason for leaving (optional)"
              className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm resize-none"
              rows={2}
            />
            <div className="flex gap-2">
              <button
                onClick={handleRequestDeletion}
                disabled={isRequestingDeletion}
                className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
              >
                {isRequestingDeletion ? "Scheduling..." : "Confirm Delete"}
              </button>
              <button
                onClick={() => setShowDeletionConfirm(false)}
                className="px-4 py-2 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg text-sm font-medium hover:bg-[var(--bg-card)]"
              >
                {t('cancel')}
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowDeletionConfirm(true)}
            className="px-4 py-2 border border-red-900/50 text-red-400 rounded-lg text-sm font-medium hover:bg-red-900/10"
          >
            {t('deleteMyAccount')}
          </button>
        )}
      </div>
    </div>
  );
}
