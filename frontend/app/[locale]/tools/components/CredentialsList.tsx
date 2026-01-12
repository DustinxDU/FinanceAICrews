"use client";

import React from "react";
import { Key, Check, AlertCircle, ExternalLink } from "lucide-react";

// Credential requirement type matching backend response
export interface CredentialRequirement {
  key: string;
  display_name: string;
  description: string;
  required: boolean;
  get_key_url: string;
  has_credential: boolean;
  is_verified: boolean;
  uses_env_var: boolean;
}

interface CredentialsListProps {
  credentials: CredentialRequirement[];
  onConfigureCredential: (credential: CredentialRequirement) => void;
}

export function CredentialsList({ credentials, onConfigureCredential }: CredentialsListProps) {
  const getStatusBadge = (credential: CredentialRequirement) => {
    if (credential.uses_env_var) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-900/20 text-green-400 border border-green-900/30">
          <Check className="w-3 h-3 mr-1" />
          Env Var
        </span>
      );
    }

    if (credential.has_credential && credential.is_verified) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-900/20 text-green-400 border border-green-900/30">
          <Check className="w-3 h-3 mr-1" />
          Configured
        </span>
      );
    }

    if (credential.has_credential && !credential.is_verified) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-amber-900/20 text-amber-400 border border-amber-900/30">
          <AlertCircle className="w-3 h-3 mr-1" />
          Unverified
        </span>
      );
    }

    if (credential.required) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-900/20 text-red-400 border border-red-900/30">
          <AlertCircle className="w-3 h-3 mr-1" />
          Required
        </span>
      );
    }

    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
        Optional
      </span>
    );
  };

  if (credentials.length === 0) {
    return (
      <div className="text-center py-8 text-[var(--text-secondary)]">
        <Key className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No credentials configured for this provider.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {credentials.map((credential) => (
        <div
          key={credential.key}
          className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 hover:border-[var(--text-secondary)] transition-colors"
        >
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2">
              <Key className="w-4 h-4 text-[var(--text-secondary)]" />
              <span className="font-medium text-[var(--text-primary)]">
                {credential.display_name}
              </span>
            </div>
            {getStatusBadge(credential)}
          </div>

          <p className="text-sm text-[var(--text-secondary)] mb-3">
            {credential.description}
          </p>

          <div className="flex items-center gap-3">
            {!credential.uses_env_var && (
              <button
                onClick={() => onConfigureCredential(credential)}
                className="px-3 py-1.5 bg-[var(--accent-blue)] hover:bg-blue-600 text-white rounded text-sm font-medium transition-colors"
              >
                {credential.has_credential ? "Update" : "Configure"}
              </button>
            )}

            {credential.get_key_url && (
              <a
                href={credential.get_key_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-[var(--accent-blue)] hover:underline"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Get API Key
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
