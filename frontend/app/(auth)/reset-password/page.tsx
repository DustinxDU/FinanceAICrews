"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Loader2, Eye, EyeOff } from "lucide-react";

// Disable static prerender to allow useSearchParams without Suspense
export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isValidating, setIsValidating] = useState(true);
  const [isValidToken, setIsValidToken] = useState(false);

  useEffect(() => {
    // Validate token on page load
    const validateToken = async () => {
      if (!token) {
        setError("Invalid or expired reset link");
        setIsValidating(false);
        return;
      }

      try {
        const response = await fetch(
          `${API_BASE_URL}/api/v1/auth/validate-reset-token?token=${token}`
        );
        if (response.ok) {
          setIsValidToken(true);
        } else {
          setError("Invalid or expired reset link");
        }
      } catch {
        setError("Failed to validate reset link");
      } finally {
        setIsValidating(false);
      }
    };

    validateToken();
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to reset password");
      }

      setIsSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset password");
    } finally {
      setIsLoading(false);
    }
  };

  if (isValidating) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--bg-app)] px-4">
        <div className="w-full max-w-md bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-8 shadow-2xl text-center">
          <Loader2 className="w-8 h-8 mx-auto mb-4 animate-spin text-[var(--accent-green)]" />
          <p className="text-[var(--text-secondary)]">Validating reset link...</p>
        </div>
      </div>
    );
  }

  if (!isValidToken && !token) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--bg-app)] px-4">
        <div className="w-full max-w-md bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-8 shadow-2xl text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-red-900/20 mb-4 border border-red-900/50">
            <svg
              className="w-5 h-5 text-red-400"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          </div>
          <h1 className="text-xl font-bold mb-2">Invalid Reset Link</h1>
          <p className="text-[var(--text-secondary)] text-sm mb-6">
            {error || "This password reset link is invalid or has expired."}
          </p>
          <Link
            href="/forgot-password"
            className="inline-flex items-center justify-center gap-2 w-full bg-[var(--text-primary)] text-black font-bold py-2.5 rounded-lg hover:bg-white/90 transition-colors"
          >
            Request New Link
          </Link>
        </div>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--bg-app)] px-4">
        <div className="w-full max-w-md bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-8 shadow-2xl text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-900/20 mb-4 border border-green-900/50">
            <svg
              className="w-5 h-5 text-green-400"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <h1 className="text-xl font-bold mb-2">Password Reset</h1>
          <p className="text-[var(--text-secondary)] text-sm mb-6">
            Your password has been successfully reset. You can now sign in with your new password.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center justify-center gap-2 w-full bg-[var(--text-primary)] text-black font-bold py-2.5 rounded-lg hover:bg-white/90 transition-colors"
          >
            Go to Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--bg-app)] px-4">
      <div className="w-full max-w-md bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-8 shadow-2xl">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[var(--bg-card)] mb-4 border border-[var(--border-color)]">
            <svg
              className="w-5 h-5 text-[var(--text-secondary)]"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold mb-2">Set New Password</h1>
          <p className="text-[var(--text-secondary)] text-sm">
            Enter your new password below.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-red-900/20 border border-red-900/50 rounded-lg text-sm text-red-400">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
              New Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter new password"
                required
                minLength={6}
                className="w-full bg-[var(--bg-app)] border border-[var(--border-color)] rounded-lg px-3 py-2 pr-10 text-sm focus:border-[var(--accent-green)] outline-none transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              >
                {showPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
              Confirm Password
            </label>
            <div className="relative">
              <input
                type={showConfirmPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
                required
                className="w-full bg-[var(--bg-app)] border border-[var(--border-color)] rounded-lg px-3 py-2 pr-10 text-sm focus:border-[var(--accent-green)] outline-none transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              >
                {showConfirmPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-[var(--text-primary)] text-black font-bold py-2.5 rounded-lg hover:bg-white/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
            Reset Password
          </button>
        </form>

        <div className="mt-8 text-center">
          <Link
            href="/login"
            className="text-sm text-[var(--accent-green)] hover:underline flex items-center justify-center gap-1"
          >
            <ArrowLeft className="w-3 h-3" />
            Back to Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--bg-app)] px-4">
          <div className="w-full max-w-md bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-8 shadow-2xl text-center">
            <Loader2 className="w-8 h-8 mx-auto mb-4 animate-spin text-[var(--accent-green)]" />
            <p className="text-[var(--text-secondary)]">Loading...</p>
          </div>
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
