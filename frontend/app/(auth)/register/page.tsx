"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agreedToTerms) {
      setError("Please agree to the Terms of Service and Privacy Policy");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      await register(email, username, password, fullName);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
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
            <h1 className="text-3xl font-bold mb-2">Create an account</h1>
            <p className="text-[var(--text-secondary)]">Start building your autonomous financial crew.</p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-900/20 border border-red-900/50 rounded-lg text-sm text-red-400">
              {error}
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="John Doe"
                className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm focus:border-[var(--accent-green)] outline-none transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="johndoe"
                required
                minLength={1}
                maxLength={50}
                className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm focus:border-[var(--accent-green)] outline-none transition-colors"
              />
            </div>
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
                placeholder="Create a password (min 8 characters)"
                required
                minLength={8}
                className="w-full bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm focus:border-[var(--accent-green)] outline-none transition-colors"
              />
            </div>
            
            <div className="flex items-start gap-2">
              <input
                type="checkbox"
                id="terms"
                checked={agreedToTerms}
                onChange={(e) => setAgreedToTerms(e.target.checked)}
                className="mt-1 rounded border-zinc-700 bg-zinc-800 text-green-500 focus:ring-0"
              />
              <label htmlFor="terms" className="text-xs text-[var(--text-secondary)]">
                I agree to the <Link href="/legal" className="underline hover:text-white">Terms of Service</Link> and <Link href="/legal" className="underline hover:text-white">Privacy Policy</Link>.
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-[var(--text-primary)] text-black font-bold py-2.5 rounded-lg hover:bg-white/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              Create Account
            </button>
          </form>
          
          <p className="mt-6 text-center text-sm text-[var(--text-secondary)]">
            Already have an account? <Link href="/login" className="text-[var(--accent-green)] hover:underline">Sign in</Link>
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
      </div>
    </div>
  );
}
