"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to send reset link");
      }

      setIsSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send reset link");
    } finally {
      setIsLoading(false);
    }
  };

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
          <h1 className="text-2xl font-bold mb-2">Reset Password</h1>
          <p className="text-[var(--text-secondary)] text-sm">
            Enter your email address and we'll send you a link to reset your password.
          </p>
        </div>

        {!isSubmitted ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 bg-red-900/20 border border-red-900/50 rounded-lg text-sm text-red-400">
                {error}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                required
                className="w-full bg-[var(--bg-app)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm focus:border-[var(--accent-green)] outline-none transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-[var(--text-primary)] text-black font-bold py-2.5 rounded-lg hover:bg-white/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              Send Reset Link
            </button>
          </form>
        ) : (
          <div className="text-center animate-in fade-in zoom-in-95">
            <div className="bg-green-900/20 text-green-400 p-4 rounded-lg text-sm mb-6 border border-green-900/50">
              Check your email! We've sent a recovery link to your inbox.
            </div>
            <button
              onClick={() => setIsSubmitted(false)}
              className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            >
              Try another email
            </button>
          </div>
        )}

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
