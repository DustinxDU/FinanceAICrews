"use client";

import React from "react";
import { Loader2, User as UserIcon } from "lucide-react";
import { useTranslations } from "next-intl";

interface ProfileTabProps {
  userProfile: any;
  isLoadingProfile: boolean;
  onEditProfile: () => void;
  onChangePassword: () => void;
}

export function ProfileTab({
  userProfile,
  isLoadingProfile,
  onEditProfile,
  onChangePassword
}: ProfileTabProps) {
  const t = useTranslations('settings');
  if (isLoadingProfile) {
    return (
      <div className="text-center py-20">
        <Loader2 className="w-8 h-8 mx-auto mb-4 animate-spin text-[var(--accent-blue)]" />
        <p className="text-sm text-[var(--text-secondary)]">{t('loadingProfile')}</p>
      </div>
    );
  }

  if (!userProfile) {
    return (
      <div className="text-center py-20">
        <p className="text-[var(--text-secondary)]">{t('failed')} to load profile. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in duration-300">
      <div className="space-y-6">
        <div className="text-center py-8">
          <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500 mx-auto mb-6 flex items-center justify-center text-4xl font-bold text-white">
            {userProfile.email.substring(0, 2).toUpperCase()}
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">{userProfile.email.split('@')[0]}</h2>
          <p className="text-[var(--text-secondary)] mb-2">{userProfile.email}</p>
          <span className="inline-block px-3 py-1 bg-gradient-to-r from-yellow-600 to-orange-600 text-white text-xs font-bold rounded-full uppercase">
            {userProfile.subscription_level}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg">
            <div className="text-xs text-[var(--text-secondary)] uppercase font-bold mb-2">{t('userId')}</div>
            <div className="text-lg font-mono text-[var(--text-primary)]">#{userProfile.id}</div>
          </div>
          <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg">
            <div className="text-xs text-[var(--text-secondary)] uppercase font-bold mb-2">Member Since</div>
            <div className="text-lg text-[var(--text-primary)]">{new Date(userProfile.created_at).toLocaleDateString()}</div>
          </div>
        </div>

        <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg">
          <h3 className="text-sm font-bold mb-3">Account Information</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-[var(--text-secondary)]">{t('email')}</span>
              <span className="text-sm font-medium text-[var(--text-primary)]">{userProfile.email}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-[var(--text-secondary)]">Subscription</span>
              <span className="text-sm font-medium text-[var(--text-primary)] capitalize">{userProfile.subscription_level}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-[var(--text-secondary)]">{t('accountStatus')}</span>
              <span className="text-xs px-2 py-1 bg-green-900/20 text-green-400 border border-green-900/50 rounded font-bold">{t('active')}</span>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onEditProfile}
            className="flex-1 px-4 py-2 bg-[var(--accent-blue)] text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            {t('editProfile')}
          </button>
          <button
            onClick={onChangePassword}
            className="px-4 py-2 border border-[var(--border-color)] text-[var(--text-secondary)] rounded-lg hover:bg-[var(--bg-card)] transition-colors"
          >
            {t('changePassword')}
          </button>
        </div>
      </div>
    </div>
  );
}
