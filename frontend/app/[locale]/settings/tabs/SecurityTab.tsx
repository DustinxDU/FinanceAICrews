"use client";

import React, { useEffect, useState } from "react";
import {
  Loader2,
  Shield,
  Smartphone,
  KeyRound,
  RefreshCw,
  Trash2,
  History,
  CheckCircle,
  XCircle,
} from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import { useToast } from "@/lib/toast";

interface TwoFactorStatus {
  enabled: boolean;
  method: string | null;
  backup_codes_remaining: number;
}

interface TwoFactorSetup {
  secret: string;
  qr_code_url: string;
  backup_codes: string[];
}

interface LoginSessionItem {
  id: number;
  device_info: string;
  ip_address: string;
  location?: string | null;
  is_current: boolean;
  created_at: string;
  last_active: string;
  expires_at?: string | null;
}

interface LoginHistoryItem {
  id: number;
  timestamp: string;
  device_info: string;
  ip_address: string;
  location?: string | null;
  status: string;
  failure_reason?: string | null;
}

export function SecurityTab() {
  const t = useTranslations("settings");
  const { success, error } = useToast();

  const [status, setStatus] = useState<TwoFactorStatus | null>(null);
  const [setupData, setSetupData] = useState<TwoFactorSetup | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [isSettingUp, setIsSettingUp] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isDisabling, setIsDisabling] = useState(false);
  const [verifyCode, setVerifyCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");
  const [disableCode, setDisableCode] = useState("");

  const [sessions, setSessions] = useState<LoginSessionItem[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isRevokingSession, setIsRevokingSession] = useState<number | null>(null);
  const [isRevokingAll, setIsRevokingAll] = useState(false);

  const [history, setHistory] = useState<LoginHistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  useEffect(() => {
    void loadAll();
  }, []);

  async function loadAll() {
    await Promise.all([loadStatus(), loadSessions(), loadHistory()]);
  }

  async function loadStatus() {
    try {
      setIsLoadingStatus(true);
      const response = await apiClient.get2FAStatus();
      setStatus(response);
    } catch (err: any) {
      console.error("{t('failed')} to load 2FA status:", err);
      error("Security", err?.message || "{t('failed')} to load 2FA status");
    } finally {
      setIsLoadingStatus(false);
    }
  }

  async function loadSessions() {
    try {
      setIsLoadingSessions(true);
      const response = await apiClient.getSessions();
      setSessions(response.sessions || []);
    } catch (err: any) {
      console.error("{t('failed')} to load sessions:", err);
      error("Security", err?.message || "{t('failed')} to load sessions");
    } finally {
      setIsLoadingSessions(false);
    }
  }

  async function loadHistory() {
    try {
      setIsLoadingHistory(true);
      const response = await apiClient.getLoginHistory(30);
      setHistory(response.history || []);
    } catch (err: any) {
      console.error("{t('failed')} to load login history:", err);
      error("Security", err?.message || "{t('failed')} to load login history");
    } finally {
      setIsLoadingHistory(false);
    }
  }

  async function handleStartSetup() {
    try {
      setIsSettingUp(true);
      const response = await apiClient.setup2FA("totp");
      setSetupData(response);
      success("2FA Setup", "Scan the QR code and verify to enable 2FA");
    } catch (err: any) {
      console.error("2FA setup failed:", err);
      error("2FA Setup {t('failed')}", err?.message || "Please try again");
    } finally {
      setIsSettingUp(false);
    }
  }

  async function handleVerifySetup() {
    if (!verifyCode.trim()) {
      error("Verification Code", "Please enter the 6-digit code");
      return;
    }

    try {
      setIsVerifying(true);
      const response = await apiClient.verify2FA(verifyCode.trim());
      setStatus(response);
      success("2FA Enabled", "Two-factor authentication is now active");
      setVerifyCode("");
    } catch (err: any) {
      console.error("2FA verification failed:", err);
      error("Verification {t('failed')}", err?.message || "Invalid code");
    } finally {
      setIsVerifying(false);
    }
  }

  async function handleDisable2FA() {
    if (!disablePassword.trim() || !disableCode.trim()) {
      error("Disable 2FA", "Password and verification code are required");
      return;
    }

    try {
      setIsDisabling(true);
      const response = await apiClient.disable2FA(disablePassword, disableCode);
      setStatus(response);
      setSetupData(null);
      setDisablePassword("");
      setDisableCode("");
      success("2FA Disabled", "Two-factor authentication has been disabled");
    } catch (err: any) {
      console.error("Disable 2FA failed:", err);
      error("Disable {t('failed')}", err?.message || "Unable to disable 2FA");
    } finally {
      setIsDisabling(false);
    }
  }

  async function handleRevokeSession(sessionId: number) {
    try {
      setIsRevokingSession(sessionId);
      await apiClient.revokeSession(sessionId);
      success("Session Revoked", "The session has been revoked");
      await loadSessions();
    } catch (err: any) {
      console.error("{t('failed')} to revoke session:", err);
      error("Revoke {t('failed')}", err?.message || "Unable to revoke session");
    } finally {
      setIsRevokingSession(null);
    }
  }

  async function handleRevokeAll() {
    try {
      setIsRevokingAll(true);
      const response = await apiClient.revokeAllSessions();
      success("Sessions Revoked", `Revoked ${response.revoked_count} session(s)`);
      await loadSessions();
    } catch (err: any) {
      console.error("{t('failed')} to revoke all sessions:", err);
      error("Revoke {t('failed')}", err?.message || "Unable to revoke sessions");
    } finally {
      setIsRevokingAll(false);
    }
  }

  function formatDateTime(value?: string | null): string {
    if (!value) return "N/A";
    const date = new Date(value);
    return date.toLocaleString();
  }

  function renderStatusBadge(enabled: boolean) {
    return enabled ? (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-bold rounded-full bg-green-900/20 text-green-400 border border-green-900/50">
        <CheckCircle className="w-3 h-3" /> Enabled
      </span>
    ) : (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-bold rounded-full bg-red-900/20 text-red-400 border border-red-900/50">
        <XCircle className="w-3 h-3" /> Disabled
      </span>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div>
        <h2 className="text-xl font-bold mb-1">Security</h2>
        <p className="text-sm text-[var(--text-secondary)]">Manage two-factor authentication and active sessions.</p>
      </div>

      {/* Two-Factor Authentication */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-bold">
              <Shield className="w-4 h-4" /> Two-Factor Authentication (2FA)
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Add an extra layer of security to your account with an authenticator app.
            </p>
          </div>
          <button
            onClick={loadStatus}
            className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" /> {t('refresh')}
          </button>
        </div>

        {isLoadingStatus ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-[var(--accent-blue)]" />
          </div>
        ) : (
          <div className="mt-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="text-sm text-[var(--text-secondary)]">{t('status')}</div>
              {renderStatusBadge(Boolean(status?.enabled))}
            </div>

            {status?.enabled ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--text-secondary)]">
                  <span className="inline-flex items-center gap-1">
                    <Smartphone className="w-3 h-3" /> Method: {status.method || "totp"}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <KeyRound className="w-3 h-3" /> Backup codes remaining: {status.backup_codes_remaining}
                  </span>
                </div>

                <div className="border-t border-[var(--border-color)] pt-4">
                  <div className="text-sm font-semibold mb-2">Disable 2FA</div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <input
                      type="password"
                      placeholder="Current password"
                      value={disablePassword}
                      onChange={(e) => setDisablePassword(e.target.value)}
                      className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm"
                    />
                    <input
                      type="text"
                      placeholder="6-digit code or backup code"
                      value={disableCode}
                      onChange={(e) => setDisableCode(e.target.value)}
                      className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm"
                    />
                  </div>
                  <button
                    onClick={handleDisable2FA}
                    disabled={isDisabling}
                    className="mt-3 px-4 py-2 text-sm font-semibold bg-red-600 text-white rounded-lg hover:bg-red-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isDisabling ? "Disabling..." : "Disable 2FA"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <button
                  onClick={handleStartSetup}
                  disabled={isSettingUp}
                  className="px-4 py-2 text-sm font-semibold bg-[var(--text-primary)] text-black rounded-lg hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSettingUp ? "Starting..." : "Enable 2FA"}
                </button>

                {setupData && (
                  <div className="border border-[var(--border-color)] rounded-lg p-4 space-y-4">
                    <div className="text-sm font-semibold">Setup 2FA</div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <div className="text-xs text-[var(--text-secondary)]">Scan QR Code</div>
                        <img
                          src={setupData.qr_code_url}
                          alt="2FA QR Code"
                          className="w-40 h-40 border border-[var(--border-color)] rounded-md bg-white"
                        />
                      </div>
                      <div className="space-y-2">
                        <div className="text-xs text-[var(--text-secondary)]">Manual Entry Key</div>
                        <div className="font-mono text-sm bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2">
                          {setupData.secret}
                        </div>
                        <div className="text-xs text-[var(--text-secondary)]">{t('backupCodes')}</div>
                        <div className="grid grid-cols-2 gap-2">
                          {setupData.backup_codes.map((code) => (
                            <div
                              key={code}
                              className="font-mono text-xs bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-md px-2 py-1"
                            >
                              {code}
                            </div>
                          ))}
                        </div>
                        <p className="text-xs text-[var(--text-secondary)]">
                          Store these codes securely. Each code can be used once.
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-col sm:flex-row gap-3">
                      <input
                        type="text"
                        placeholder="Enter 6-digit code"
                        value={verifyCode}
                        onChange={(e) => setVerifyCode(e.target.value)}
                        className="flex-1 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm"
                      />
                      <button
                        onClick={handleVerifySetup}
                        disabled={isVerifying}
                        className="px-4 py-2 text-sm font-semibold bg-[var(--accent-blue)] text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isVerifying ? "Verifying..." : "Verify & Enable"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* {t('active')} Sessions */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-bold">
              <KeyRound className="w-4 h-4" /> {t('active')} Sessions
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Review and revoke sessions you do not recognize.
            </p>
          </div>
          <button
            onClick={handleRevokeAll}
            disabled={isRevokingAll}
            className="text-xs font-semibold border border-[var(--border-color)] rounded-md px-3 py-2 hover:bg-[var(--bg-panel)] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRevokingAll ? "Revoking..." : "Revoke All Other Sessions"}
          </button>
        </div>

        {isLoadingSessions ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-[var(--accent-blue)]" />
          </div>
        ) : sessions.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs uppercase text-[var(--text-secondary)]">
                <tr className="border-b border-[var(--border-color)]">
                  <th className="text-left py-2 pr-4">Device</th>
                  <th className="text-left py-2 pr-4">IP Address</th>
                  <th className="text-left py-2 pr-4">Location</th>
                  <th className="text-left py-2 pr-4">Last {t('active')}</th>
                  <th className="text-right py-2">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-color)]">
                {sessions.map((session) => (
                  <tr key={session.id} className="hover:bg-[var(--bg-panel)]">
                    <td className="py-3 pr-4">
                      <div className="font-medium text-[var(--text-primary)]">{session.device_info}</div>
                      {session.is_current && (
                        <span className="text-xs text-[var(--accent-green)] font-semibold">Current session</span>
                      )}
                    </td>
                    <td className="py-3 pr-4 text-[var(--text-secondary)]">{session.ip_address}</td>
                    <td className="py-3 pr-4 text-[var(--text-secondary)]">{session.location || "Unknown"}</td>
                    <td className="py-3 pr-4 text-[var(--text-secondary)]">{formatDateTime(session.last_active)}</td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => handleRevokeSession(session.id)}
                        disabled={session.is_current || isRevokingSession === session.id}
                        className="inline-flex items-center gap-1 text-xs text-red-400 hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isRevokingSession === session.id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Trash2 className="w-3 h-3" />
                        )}
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-sm text-[var(--text-secondary)] py-6">{t('noActiveSessionsFound')}</div>
        )}
      </div>

      {/* {t('loginHistory')} */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-bold">
              <History className="w-4 h-4" /> {t('loginHistory')}
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Recent login activity for your account.
            </p>
          </div>
          <button
            onClick={loadHistory}
            className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" /> {t('refresh')}
          </button>
        </div>

        {isLoadingHistory ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-[var(--accent-blue)]" />
          </div>
        ) : history.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs uppercase text-[var(--text-secondary)]">
                <tr className="border-b border-[var(--border-color)]">
                  <th className="text-left py-2 pr-4">{t('time')}</th>
                  <th className="text-left py-2 pr-4">Device</th>
                  <th className="text-left py-2 pr-4">IP</th>
                  <th className="text-left py-2 pr-4">Location</th>
                  <th className="text-left py-2 pr-4">{t('status')}</th>
                  <th className="text-left py-2">{t('details')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-color)]">
                {history.map((item) => (
                  <tr key={item.id} className="hover:bg-[var(--bg-panel)]">
                    <td className="py-3 pr-4 text-[var(--text-secondary)]">{formatDateTime(item.timestamp)}</td>
                    <td className="py-3 pr-4 text-[var(--text-secondary)]">{item.device_info}</td>
                    <td className="py-3 pr-4 text-[var(--text-secondary)]">{item.ip_address}</td>
                    <td className="py-3 pr-4 text-[var(--text-secondary)]">{item.location || "Unknown"}</td>
                    <td className="py-3 pr-4">
                      <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                        item.status === "success"
                          ? "bg-green-900/20 text-green-400 border border-green-900/50"
                          : "bg-red-900/20 text-red-400 border border-red-900/50"
                      }`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3 text-[var(--text-secondary)]">
                      {item.failure_reason || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-sm text-[var(--text-secondary)] py-6">{t('noLoginHistoryRecorded')}</div>
        )}
      </div>
    </div>
  );
}
