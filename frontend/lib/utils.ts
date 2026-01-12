import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { getToken, clearAuth } from "./auth";
import { redirectToLogin } from "./authRoutes";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * 带认证的 fetch wrapper
 * 自动添加 Authorization header、处理 401 错误
 */
export async function authFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, { ...options, headers });

  // 401 未授权时清除认证并跳转登录
  if (response.status === 401) {
    clearAuth();
    redirectToLogin();
  }

  return response;
}

export function formatDate(dateString: string | undefined): string {
  if (!dateString) return "-";
  const date = new Date(dateString);
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function getStatusColor(status: string): string {
  switch (status) {
    case "completed":
      return "text-green-600 bg-green-50";
    case "running":
      return "text-blue-600 bg-blue-50";
    case "pending":
      return "text-yellow-600 bg-yellow-50";
    case "failed":
      return "text-red-600 bg-red-50";
    case "cancelled":
      return "text-gray-600 bg-gray-50";
    default:
      return "text-gray-600 bg-gray-50";
  }
}

export function getStatusText(status: string): string {
  switch (status) {
    case "completed":
      return "已完成";
    case "running":
      return "运行中";
    case "pending":
      return "等待中";
    case "failed":
      return "失败";
    case "cancelled":
      return "已取消";
    default:
      return status;
  }
}

export function getCrewDisplayName(crewName: string): string {
  const names: Record<string, string> = {
    buffett: "巴菲特战队",
    soros: "索罗斯战队",
    bridgewater: "桥水战队",
    standard: "标准分析",
  };
  return names[crewName] || crewName;
}
