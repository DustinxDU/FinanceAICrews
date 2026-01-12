'use client';

/**
 * Auth Context - 全局认证状态管理
 *
 * 提供登录、注册、登出功能和用户状态
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useRouter as useNextRouter } from 'next/navigation';
import {
  User,
  AuthState,
  getAuthState,
  saveAuth,
  clearAuth,
  getToken,
} from '@/lib/auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  loading: boolean;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Get the current locale from the URL path or default to 'en'
 * This is more robust than useLocale() which may fail in (auth) routes
 */
function getLocaleFromPath(): string {
  if (typeof window === 'undefined') return 'en';
  const pathSegments = window.location.pathname.split('/').filter(Boolean);
  const supportedLocales = ['en', 'zh-CN', 'zh-TW', 'ja', 'ko', 'ms', 'id', 'vi', 'th', 'es', 'fr', 'de', 'ru', 'ar', 'hi', 'pt'];
  if (pathSegments.length > 0 && supportedLocales.includes(pathSegments[0])) {
    return pathSegments[0];
  }
  return 'en';
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>({
    token: null,
    user: null,
    isAuthenticated: false,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const nextRouter = useNextRouter();

  // 初始化时从 localStorage 恢复状态
  useEffect(() => {
    const state = getAuthState();
    setAuthState(state);
    setLoading(false);
  }, []);

  // 登录
  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || '登录失败');
      }

      const data = await response.json();
      saveAuth(data.access_token, data.user);
      setAuthState({
        token: data.access_token,
        user: data.user,
        isAuthenticated: true,
      });

      // Navigate to locale-prefixed dashboard route
      // Use getLocaleFromPath() instead of useLocale() to avoid issues in (auth) routes
      const locale = getLocaleFromPath();
      nextRouter.push(`/${locale}/dashboard`);
    } catch (err) {
      const message = err instanceof Error ? err.message : '登录失败';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [nextRouter]);

  // 注册
  const register = useCallback(async (email: string, username: string, password: string, fullName?: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, username, password, full_name: fullName }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || '注册失败');
      }

      const data = await response.json();
      saveAuth(data.access_token, data.user);
      setAuthState({
        token: data.access_token,
        user: data.user,
        isAuthenticated: true,
      });

      // Navigate to locale-prefixed dashboard route
      // Use getLocaleFromPath() instead of useLocale() to avoid issues in (auth) routes
      const locale = getLocaleFromPath();
      nextRouter.push(`/${locale}/dashboard`);
    } catch (err) {
      const message = err instanceof Error ? err.message : '注册失败';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [nextRouter]);

  // 登出
  const logout = useCallback(() => {
    clearAuth();
    setAuthState({
      token: null,
      user: null,
      isAuthenticated: false,
    });
    nextRouter.push('/login');
  }, [nextRouter]);

  // 刷新用户信息
  const refreshUser = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const user = await response.json();
        saveAuth(token, user);
        setAuthState({
          token,
          user,
          isAuthenticated: true,
        });
      } else if (response.status === 401) {
        // Token 过期，清除认证
        logout();
      }
    } catch {
      // 网络错误，保持当前状态
    }
  }, [logout]);

  return (
    <AuthContext.Provider
      value={{
        ...authState,
        login,
        register,
        logout,
        refreshUser,
        loading,
        error,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

/**
 * 高阶组件：保护需要登录的页面
 */
export function withAuth<P extends object>(
  WrappedComponent: React.ComponentType<P>
) {
  return function AuthenticatedComponent(props: P) {
    const { isAuthenticated, loading } = useAuth();
    const router = useNextRouter();

    useEffect(() => {
      if (!loading && !isAuthenticated) {
        router.push('/login');
      }
    }, [isAuthenticated, loading, router]);

    if (loading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      );
    }

    if (!isAuthenticated) {
      return null;
    }

    return <WrappedComponent {...props} />;
  };
}
