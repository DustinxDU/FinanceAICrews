"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Github, Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left Side - Form */}
      <div className="flex-1 flex flex-col justify-center px-8 sm:px-12 lg:px-20 bg-[var(--bg-app)]">
        <div className="w-full max-w-sm mx-auto">
          <div className="mb-10">
            <Link href="/" className="flex items-center gap-2 mb-8 group w-fit">
              <ArrowLeft className="w-4 h-4 text-[var(--text-secondary)] group-hover:text-[var(--text-primary)] transition-colors" />
              <span className="text-sm text-[var(--text-secondary)] group-hover:text-[var(--text-primary)] transition-colors">Back to Home</span>
            </Link>
            <h1 className="text-3xl font-bold mb-2">Welcome back</h1>
            <p className="text-[var(--text-secondary)]">Enter your credentials to access your workspace.</p>
          </div>

          <div className="space-y-4 mb-8">
            <button className="w-full flex items-center justify-center gap-3 bg-[var(--bg-card)] hover:bg-[var(--bg-panel)] border border-[var(--border-color)] py-2.5 rounded-lg transition-colors text-sm font-medium">
              <Github className="w-5 h-5" /> Continue with GitHub
            </button>
            <button className="w-full flex items-center justify-center gap-3 bg-[var(--bg-card)] hover:bg-[var(--bg-panel)] border border-[var(--border-color)] py-2.5 rounded-lg transition-colors text-sm font-medium">
              <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
              Continue with Google
            </button>
          </div>

          <div className="relative mb-8">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-[var(--border-color)]"></div></div>
            <div className="relative flex justify-center text-xs uppercase"><span className="bg-[var(--bg-app)] px-2 text-[var(--text-secondary)]">Or continue with email</span></div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-900/20 border border-red-900/50 rounded-lg text-sm text-red-400">
              {error}
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                required
                className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm focus:border-[var(--accent-green)] outline-none transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm focus:border-[var(--accent-green)] outline-none transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-[var(--text-primary)] text-black font-bold py-2.5 rounded-lg hover:bg-white/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              Sign In
            </button>
          </form>
          
          <p className="mt-6 text-center text-sm text-[var(--text-secondary)]">
            Don't have an account? <Link href="/register" className="text-[var(--accent-green)] hover:underline">Sign up</Link>
          </p>
          <p className="mt-3 text-center text-sm text-[var(--text-secondary)]">
            <Link href="/forgot-password" className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:underline transition-colors">Forgot your password?</Link>
          </p>
        </div>
      </div>

      {/* Right Side - Visual */}
      <div className="hidden lg:block lg:w-1/2 relative overflow-hidden bg-black">
        <img
          src="https://images.unsplash.com/photo-1639322537228-f710d846310a?q=80&w=2832&auto=format&fit=crop"
          alt="Abstract Data Flow"
          className="absolute inset-0 w-full h-full object-cover opacity-60"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[var(--bg-app)] to-transparent" />
        <div className="absolute bottom-12 left-12 max-w-md">
          <blockquote className="text-xl font-medium mb-4">&quot;FinanceAI has completely transformed how our quant team operates. The agent orchestration is seamless.&quot;</blockquote>
          <div className="text-sm text-[var(--text-secondary)]">Sarah Chen, Portfolio Manager at AlphaFund</div>
        </div>
      </div>
    </div>
  );
}
