export const AUTH_PATHNAMES = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
] as const;

export type AuthPathname = (typeof AUTH_PATHNAMES)[number];

export function isAuthRoutePathname(pathname: string): pathname is AuthPathname {
  return (AUTH_PATHNAMES as readonly string[]).includes(pathname);
}

export function getLoginRedirectTarget(pathname: string): "/login" | null {
  if (isAuthRoutePathname(pathname)) return null;
  return "/login";
}

export function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  const target = getLoginRedirectTarget(window.location.pathname);
  if (!target) return;
  window.location.assign(target);
}

