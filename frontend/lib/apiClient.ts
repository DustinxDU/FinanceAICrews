const stripTrailingSlash = (value?: string): string => {
  if (!value) return "";
  return value.endsWith("/") ? value.slice(0, -1) : value;
};

const PUBLIC_API_BASE_URL = stripTrailingSlash(process.env.NEXT_PUBLIC_API_URL);
const INTERNAL_API_BASE_URL = stripTrailingSlash(process.env.INTERNAL_API_URL);

/**
 * Build API URL for both client-side and server-side environments.
 * - Browser：走 Nginx Gateway（NEXT_PUBLIC_API_URL）
 * - SSR/Server Actions：走 Docker 内网（INTERNAL_API_URL）
 */
export const buildApiUrl = (path: string): string => {
  const base =
    typeof window === "undefined"
      ? INTERNAL_API_BASE_URL || PUBLIC_API_BASE_URL
      : PUBLIC_API_BASE_URL;

  if (!base) {
    return path;
  }

  return path.startsWith("/") ? `${base}${path}` : `${base}/${path}`;
};
