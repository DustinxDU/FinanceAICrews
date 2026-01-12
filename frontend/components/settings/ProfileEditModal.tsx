"use client";

import { useState, useEffect } from "react";
import { ProfileUpdateRequest } from "@/lib/types";

interface ProfileEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: ProfileUpdateRequest) => Promise<void>;
  currentEmail: string;
  currentFullName?: string;
  currentAvatarUrl?: string;
  currentPhoneNumber?: string;
}

export function ProfileEditModal({
  isOpen,
  onClose,
  onSave,
  currentEmail,
  currentFullName,
  currentAvatarUrl,
  currentPhoneNumber,
}: ProfileEditModalProps) {
  const [fullName, setFullName] = useState(currentFullName || "");
  const [avatarUrl, setAvatarUrl] = useState(currentAvatarUrl || "");
  const [email, setEmail] = useState(currentEmail);
  const [phoneNumber, setPhoneNumber] = useState(currentPhoneNumber || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // Reset form when modal opens with new data
  useEffect(() => {
    if (isOpen) {
      setFullName(currentFullName || "");
      setAvatarUrl(currentAvatarUrl || "");
      setEmail(currentEmail);
      setPhoneNumber(currentPhoneNumber || "");
      setCurrentPassword("");
      setNewPassword("");
    }
  }, [isOpen, currentEmail, currentFullName, currentAvatarUrl, currentPhoneNumber]);

  // Check if sensitive fields are being changed
  const emailChanged = email !== currentEmail;
  const phoneChanged = phoneNumber !== currentPhoneNumber;
  const passwordChanging = newPassword.length > 0;
  const needsPassword = emailChanged || phoneChanged || passwordChanging;

  // Check if any field has changed
  const hasChanges =
    fullName !== (currentFullName || "") ||
    avatarUrl !== (currentAvatarUrl || "") ||
    emailChanged ||
    phoneChanged ||
    passwordChanging;

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const updateData: ProfileUpdateRequest = {};

      // Non-sensitive fields
      if (fullName !== (currentFullName || "")) {
        updateData.full_name = fullName;
      }
      if (avatarUrl !== (currentAvatarUrl || "")) {
        updateData.avatar_url = avatarUrl;
      }

      // Sensitive fields
      if (emailChanged) {
        updateData.email = email;
      }
      if (phoneChanged) {
        updateData.phone_number = phoneNumber;
      }
      if (passwordChanging) {
        updateData.new_password = newPassword;
      }

      // Add current_password if needed
      if (needsPassword) {
        updateData.current_password = currentPassword;
      }

      await onSave(updateData);
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 z-[9999] flex items-center justify-center">
      <div className="bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold mb-4">Edit Profile</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-xs uppercase text-[var(--text-secondary)] mb-1">
              Full Name
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded px-3 py-2"
              placeholder="Enter your full name"
            />
          </div>

          <div>
            <label className="block text-xs uppercase text-[var(--text-secondary)] mb-1">
              Avatar URL
            </label>
            <input
              type="url"
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded px-3 py-2"
              placeholder="https://example.com/avatar.jpg"
            />
          </div>

          <div>
            <label className="block text-xs uppercase text-[var(--text-secondary)] mb-1">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded px-3 py-2"
            />
            {emailChanged && (
              <p className="text-xs text-yellow-500 mt-1">
                Email changes require verification. A verification email will be sent.
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs uppercase text-[var(--text-secondary)] mb-1">
              Phone Number
            </label>
            <input
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded px-3 py-2"
              placeholder="+1-555-123-4567"
            />
          </div>

          {needsPassword && (
            <div>
              <label className="block text-xs uppercase text-[var(--text-secondary)] mb-1">
                Current Password (required) *
              </label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded px-3 py-2"
                placeholder="Enter your current password"
              />
            </div>
          )}

          <div>
            <label className="block text-xs uppercase text-[var(--text-secondary)] mb-1">
              New Password (optional)
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded px-3 py-2"
              placeholder="Leave blank to keep current password"
            />
            {passwordChanging && (
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                Password must be at least 8 characters with 3 of: uppercase, lowercase, digit, special character
              </p>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-sm">Cancel</button>
          <button
            onClick={handleSave}
            disabled={isSaving || !hasChanges || (needsPassword && !currentPassword)}
            className="px-4 py-2 bg-[var(--accent-blue)] text-white rounded-lg disabled:opacity-50"
          >
            {isSaving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
