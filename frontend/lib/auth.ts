/**
 * Auth Utilities - 认证工具函数
 * 
 * 处理 Token 存储和认证状态
 */

const TOKEN_KEY = 'financeai_token';
const USER_KEY = 'financeai_user';

export interface User {
  id: number;
  email: string;
  subscription_level: string;
  created_at: string;
}

export interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
}

/**
 * 保存认证信息到 localStorage
 */
export function saveAuth(token: string, user: User): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
}

/**
 * 获取存储的 Token
 */
export function getToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(TOKEN_KEY);
  }
  return null;
}

/**
 * 获取存储的用户信息
 */
export function getUser(): User | null {
  if (typeof window !== 'undefined') {
    const userStr = localStorage.getItem(USER_KEY);
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch {
        return null;
      }
    }
  }
  return null;
}

/**
 * 获取完整认证状态
 */
export function getAuthState(): AuthState {
  const token = getToken();
  const user = getUser();
  return {
    token,
    user,
    isAuthenticated: !!token && !!user,
  };
}

/**
 * 清除认证信息 (登出)
 */
export function clearAuth(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
}

/**
 * 检查是否已登录
 */
export function isAuthenticated(): boolean {
  return !!getToken();
}
