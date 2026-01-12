"use client";

import React, { useState, useEffect, useCallback } from "react";
import { AppLayout } from "@/components/layout";
import { withAuth } from "@/contexts/AuthContext";
import { useToast } from "@/lib/toast";
import apiClient from "@/lib/api";
import {
  User as UserIcon, Activity, Bell, CreditCard, Key, Bot, ShieldCheck, Settings as SettingsIcon, Shield,
} from "lucide-react";
import { useTranslations } from "next-intl";

// Modular Tab Components
import { ProfileTab } from "./tabs/ProfileTab";
import { UsageTab } from "./tabs/UsageTab";
import { BillingTab } from "./tabs/BillingTab";
import { SecurityTab } from "./tabs/SecurityTab";
import { NotificationsTab } from "./tabs/NotificationsTab";
import { PreferencesTab } from "./tabs/PreferencesTab";
import { APIKeysTab } from "./tabs/APIKeysTab";
import { AgentModelsTab } from "./tabs/AgentModelsTab";
import { PrivacyTab } from "./tabs/PrivacyTab";

// Modals
import { ProfileEditModal } from "@/components/settings/ProfileEditModal";

function SettingsPage() {
  const { error, success } = useToast();
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const [activeTab, setActiveTab] = useState("usage");
  const [userProfile, setUserProfile] = useState<any>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [showProfileEdit, setShowProfileEdit] = useState(false);

  // API Keys Tab State
  const [savedProviders, setSavedProviders] = useState<any[]>([]);
  const [availableProviders, setAvailableProviders] = useState<any[]>([]);
  const [isLoadingProviders, setIsLoadingProviders] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoadingProfile(true);
    setIsLoadingProviders(true);

    try {
      // 1. Fetch User Profile
      const profile = await apiClient.getCurrentUser();
      setUserProfile(profile);

      // 2. Fetch Providers for API Keys Tab
      // MIGRATION COMPLETE: Phase 3 - Using modern BYOK profiles API
      // Previous architecture note: Deferred migration from UserLLMConfig to LLMUserByokProfile
      // Completed in Phase 3: Full migration to /api/v1/llm-policy/byok-profiles
      const [savedResp, availableResp] = await Promise.all([
        apiClient.listByokProfiles(),           // Modern BYOK API (MIGRATED in Phase 3)
        apiClient.listLlmPolicyProviders(),     // Modern Providers API (MIGRATED in Task 4)
      ]);
      setSavedProviders(savedResp || []);
      setAvailableProviders(availableResp || []);

    } catch (err: any) {
      console.error(t('failed') + " to fetch settings data:", err);
      error("Data Load Error", err.message || t('failed') + " to load settings data");
    } finally {
      setIsLoadingProfile(false);
      setIsLoadingProviders(false);
    }
  }, [error]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // API Keys Tab Handlers
  const handleSaveProvider = async (data: any) => {
    // LLMProviderForm 已经调用了 saveProviderConfig，这里只需要刷新数据
    success("Provider Saved", "Provider configuration saved successfully");
    await fetchData();
  };

  const handleDeleteProvider = async (provider: any) => {
    setIsDeleting(true);
    try {
      await apiClient.deleteProviderConfig(provider.id);
      success("Provider Deleted", "Provider removed successfully");
      await fetchData();
    } catch (err: any) {
      error(t('failed'), err?.message || t('failed') + " to delete provider");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleEditProvider = (provider: any) => {
    // Edit is handled within APIKeysTab component
  };

  const refreshModels = async () => {
    await fetchData();
  };

  const tabs = [
    { id: "profile", label: t('profile'), icon: UserIcon },
    { id: "usage", label: t('usage'), icon: Activity },
    { id: "billing", label: t('billing'), icon: CreditCard },
    { id: "security", label: t('security'), icon: ShieldCheck },
    { id: "notifications", label: t('notifications'), icon: Bell },
    { id: "api_keys", label: t('apiKeys'), icon: Key },
    { id: "agent_models", label: t('agentModels'), icon: Bot },
    { id: "preferences", label: t('preferences'), icon: SettingsIcon },
    { id: "privacy", label: t('privacy'), icon: Shield },
  ];

  return (
    <AppLayout>
      <div className="p-8 max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">{t('title')}</h1>
        <div className="flex flex-col md:flex-row gap-8">
          <div className="w-full md:w-64 shrink-0">
            <nav className="flex flex-col gap-1">
              {tabs.map((tab) => (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${activeTab === tab.id ? "bg-[var(--bg-card)] text-[var(--text-primary)]" : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-panel)]"}`}>
                  <tab.icon className="w-4 h-4" />{tab.label}
                </button>
              ))}
            </nav>
          </div>
          <div className="flex-1 min-w-0 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-6 min-h-[500px]">
            {activeTab === "profile" && (
              <ProfileTab
                userProfile={userProfile}
                isLoadingProfile={isLoadingProfile}
                onEditProfile={() => setShowProfileEdit(true)}
                onChangePassword={() => setShowProfileEdit(true)}
              />
            )}
            {activeTab === "usage" && <UsageTab />}
            {activeTab === "billing" && <BillingTab />}
            {activeTab === "security" && <SecurityTab />}
            {activeTab === "notifications" && <NotificationsTab />}
            {activeTab === "api_keys" && (
              <APIKeysTab
                savedProviders={savedProviders}
                availableProviders={availableProviders}
                isLoadingProviders={isLoadingProviders}
                isDeleting={isDeleting}
                onSaveProvider={handleSaveProvider}
                onDeleteProvider={handleDeleteProvider}
                onEditProvider={handleEditProvider}
                refreshModels={refreshModels}
              />
            )}
            {activeTab === "agent_models" && <AgentModelsTab />}
            {activeTab === "preferences" && <PreferencesTab />}
            {activeTab === "privacy" && <PrivacyTab />}
          </div>
        </div>
      </div>

      <ProfileEditModal
        isOpen={showProfileEdit}
        onClose={() => setShowProfileEdit(false)}
        onSave={async (data) => {
          try {
            const updated = await apiClient.updateProfile(data);

            // {t('refresh')} user profile data
            await fetchData();

            // Show success message
            if (data.email && data.email !== userProfile?.email) {
              success("Profile Updated", t('email') + " change pending verification. Please check your inbox.");
            } else if (data.new_password) {
              success("Profile Updated", "Your password has been changed successfully.");
            } else {
              success("Profile Updated", "Your profile has been updated successfully.");
            }
          } catch (err: any) {
            console.error("Profile update failed:", err);
            error(t('failed'), err?.message || t('failed') + " to update profile. Please try again.");
            throw err; // Re-throw to keep modal open
          }
        }}
        currentEmail={userProfile?.email || ""}
        currentFullName={userProfile?.full_name}
        currentAvatarUrl={userProfile?.avatar_url}
        currentPhoneNumber={userProfile?.phone_number}
      />
    </AppLayout>
  );
}

export default withAuth(SettingsPage);
