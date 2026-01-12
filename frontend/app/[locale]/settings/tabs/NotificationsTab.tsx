"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Bell, BellOff, Loader2, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import apiClient from "@/lib/api";
import { useToast } from "@/lib/toast";
import { useTranslations } from "next-intl";
import type { UserNotificationPreferences } from "@/lib/types";

interface ToggleProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  disabled?: boolean;
  label: string;
  description?: string;
}

function Toggle({ enabled, onChange, disabled, label, description }: ToggleProps) {
  return (
    <div className="flex items-center justify-between py-3">
      <div className="flex-1">
        <div className="font-medium text-[var(--text-primary)]">{label}</div>
        {description && (
          <div className="text-sm text-[var(--text-secondary)] mt-0.5">{description}</div>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        onClick={() => !disabled && onChange(!enabled)}
        disabled={disabled}
        className={`
          relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200
          ${enabled ? 'bg-[var(--accent-green)]' : 'bg-zinc-600'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        <span
          className={`
            inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200
            ${enabled ? 'translate-x-6' : 'translate-x-1'}
          `}
        />
      </button>
    </div>
  );
}

function PushSubscriptionStatus({ hasSubscription }: { hasSubscription: boolean }) {
  const t = useTranslations('notifications');

  if (hasSubscription) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-bold rounded-full bg-green-900/20 text-green-400 border border-green-900/50">
        <CheckCircle className="w-3 h-3" />
        {t('pushSubscribed')}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-bold rounded-full bg-zinc-900/20 text-zinc-400 border border-zinc-700">
      <XCircle className="w-3 h-3" />
      {t('pushNotSubscribed')}
    </span>
  );
}

export function NotificationsTab() {
  const t = useTranslations('notifications');
  const tSettings = useTranslations('settings');
  const { success, error } = useToast();

  const [preferences, setPreferences] = useState<UserNotificationPreferences | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubscribing, setIsSubscribing] = useState(false);
  const [pushSupported, setPushSupported] = useState(false);
  const [pushPermission, setPushPermission] = useState<NotificationPermission | null>(null);

  // Check if push notifications are supported
  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window && "serviceWorker" in navigator) {
      setPushSupported(true);
      setPushPermission(Notification.permission);
    }
  }, []);

  const loadPreferences = useCallback(async () => {
    try {
      setIsLoading(true);
      const resp = await apiClient.getNotificationPreferences();
      setPreferences(resp);
    } catch (err: any) {
      console.error(t('failed') + " to load notification preferences:", err);
      error(
        tSettings('notifications'),
        err?.message || t('loadFailed')
      );
    } finally {
      setIsLoading(false);
    }
  }, [error, t, tSettings]);

  useEffect(() => {
    void loadPreferences();
  }, [loadPreferences]);

  const handleToggle = async (
    field: "enabled" | "analysis_completion" | "system_updates",
    value: boolean
  ) => {
    if (!preferences) return;

    const updatedPrefs = { ...preferences, [field]: value };

    // Optimistic update
    setPreferences(updatedPrefs);

    try {
      setIsSaving(true);
      const resp = await apiClient.updateNotificationPreferences({
        enabled: updatedPrefs.enabled,
        analysis_completion: updatedPrefs.analysis_completion,
        system_updates: updatedPrefs.system_updates,
      });
      setPreferences(resp);
      success(
        tSettings('notifications'),
        t('preferencesSaved')
      );
    } catch (err: any) {
      // Revert optimistic update
      setPreferences(preferences);
      console.error(t('failed') + " to save notification preferences:", err);
      error(
        tSettings('notifications'),
        err?.message || t('saveFailed')
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubscribePush = async () => {
    if (!pushSupported) {
      error(
        tSettings('notifications'),
        t('pushNotSupported')
      );
      return;
    }

    try {
      setIsSubscribing(true);

      // Request notification permission
      const permission = await Notification.requestPermission();
      setPushPermission(permission);

      if (permission !== "granted") {
        error(
          tSettings('notifications'),
          t('pushPermissionDenied')
        );
        return;
      }

      // Get service worker registration
      const registration = await navigator.serviceWorker.ready;

      // Subscribe to push notifications
      // Note: In production, you'd get the VAPID public key from your backend
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY,
      });

      // Send subscription to backend
      const subscriptionJson = subscription.toJSON();
      const resp = await apiClient.updateNotificationPreferences({
        enabled: preferences?.enabled ?? true,
        analysis_completion: preferences?.analysis_completion ?? true,
        system_updates: preferences?.system_updates ?? true,
        push_subscription: {
          endpoint: subscriptionJson.endpoint!,
          keys: {
            p256dh: subscriptionJson.keys!.p256dh!,
            auth: subscriptionJson.keys!.auth!,
          },
        },
      });

      setPreferences(resp);
      success(
        tSettings('notifications'),
        t('pushSubscribed')
      );
    } catch (err: any) {
      console.error(t('failed') + " to subscribe to push notifications:", err);
      error(
        tSettings('notifications'),
        err?.message || t('pushSubscribeFailed')
      );
    } finally {
      setIsSubscribing(false);
    }
  };

  const handleUnsubscribePush = async () => {
    try {
      setIsSubscribing(true);
      const resp = await apiClient.unsubscribePushNotifications();
      setPreferences(resp);
      success(
        tSettings('notifications'),
        t('pushUnsubscribed')
      );
    } catch (err: any) {
      console.error("{t('failed')} to unsubscribe from push notifications:", err);
      error(
        tSettings('notifications'),
        err?.message || t('pushUnsubscribeFailed')
      );
    } finally {
      setIsSubscribing(false);
    }
  };

  const isDisabled = isLoading || isSaving;
  const notificationsEnabled = preferences?.enabled ?? false;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold mb-1 flex items-center gap-2">
          {notificationsEnabled ? (
            <Bell className="w-5 h-5 text-[var(--accent-green)]" />
          ) : (
            <BellOff className="w-5 h-5 text-zinc-500" />
          )}
          {tSettings('notifications')}
        </h2>
        <p className="text-sm text-[var(--text-secondary)]">
          {t('description')}
        </p>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-[var(--accent-blue)]" />
        </div>
      )}

      {/* Main preferences */}
      {!isLoading && preferences && (
        <>
          {/* Master toggle */}
          <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg">
            <Toggle
              enabled={notificationsEnabled}
              onChange={(v) => handleToggle("enabled", v)}
              disabled={isDisabled}
              label={t('enableNotifications')}
              description={t('enableDescription')}
            />
          </div>

          {/* Notification types */}
          <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg space-y-1">
            <div className="font-medium text-[var(--text-primary)] mb-3">
              {t('notificationTypes')}
            </div>

            <div className={`divide-y divide-[var(--border-color)] ${!notificationsEnabled ? 'opacity-50' : ''}`}>
              <Toggle
                enabled={preferences.analysis_completion}
                onChange={(v) => handleToggle("analysis_completion", v)}
                disabled={isDisabled || !notificationsEnabled}
                label={t('analysisCompletion')}
                description={t('analysisCompletionDesc')}
              />

              <Toggle
                enabled={preferences.system_updates}
                onChange={(v) => handleToggle("system_updates", v)}
                disabled={isDisabled || !notificationsEnabled}
                label={t('systemUpdates')}
                description={t('systemUpdatesDesc')}
              />
            </div>

            {!notificationsEnabled && (
              <div className="flex items-center gap-2 mt-3 p-2 bg-yellow-900/20 border border-yellow-900/50 rounded text-sm text-yellow-400">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                {t('enableFirst')}
              </div>
            )}
          </div>

          {/* Browser push notifications */}
          <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-[var(--text-primary)]">
                  {t('browserPush')}
                </div>
                <div className="text-sm text-[var(--text-secondary)] mt-0.5">
                  {t('browserPushDesc')}
                </div>
              </div>
              <PushSubscriptionStatus hasSubscription={preferences.has_push_subscription} />
            </div>

            {!pushSupported && (
              <div className="text-sm text-[var(--text-secondary)] p-2 bg-zinc-900/50 rounded">
                {t('pushNotSupportedBrowser')}
              </div>
            )}

            {pushSupported && pushPermission === "denied" && (
              <div className="flex items-center gap-2 p-2 bg-red-900/20 border border-red-900/50 rounded text-sm text-red-400">
                <XCircle className="w-4 h-4 flex-shrink-0" />
                {t('pushBlocked')}
              </div>
            )}

            {pushSupported && pushPermission !== "denied" && (
              <div className="flex gap-2">
                {!preferences.has_push_subscription ? (
                  <button
                    onClick={handleSubscribePush}
                    disabled={isSubscribing || !notificationsEnabled}
                    className="px-4 py-2 rounded-lg text-sm font-bold bg-[var(--accent-blue)] text-white disabled:opacity-60 flex items-center gap-2"
                  >
                    {isSubscribing && <Loader2 className="w-4 h-4 animate-spin" />}
                    {t('enablePush')}
                  </button>
                ) : (
                  <button
                    onClick={handleUnsubscribePush}
                    disabled={isSubscribing}
                    className="px-4 py-2 rounded-lg text-sm font-bold border border-[var(--border-color)] bg-[var(--bg-panel)] text-[var(--text-primary)] disabled:opacity-60 flex items-center gap-2"
                  >
                    {isSubscribing && <Loader2 className="w-4 h-4 animate-spin" />}
                    {t('disablePush')}
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Info section */}
          <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-sm text-[var(--text-secondary)]">
            <div className="font-medium text-[var(--text-primary)] mb-2">
              {t('aboutNotifications')}
            </div>
            <ul className="list-disc ml-5 space-y-1">
              <li>
                {t('infoAnalysis')}
              </li>
              <li>
                {t('infoSystem')}
              </li>
              <li>
                {t('infoPush')}
              </li>
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
