"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import apiClient from "@/lib/api";
import { getToken } from "@/lib/auth";

export type ThemeOption = "light" | "dark" | "system";

interface ThemeContextValue {
  theme: ThemeOption;
  isLoading: boolean;
  setTheme: (theme: ThemeOption) => Promise<void>;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const applyThemeClass = (theme: ThemeOption) => {
  if (typeof document === "undefined") return;

  const root = document.documentElement;
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const resolved = theme === "system" ? (prefersDark ? "dark" : "light") : theme;

  root.classList.remove("light", "dark");
  root.classList.add(resolved);
  root.dataset.theme = theme;
};

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeOption>("system");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    applyThemeClass(theme);
  }, [theme]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      if (theme === "system") {
        applyThemeClass("system");
      }
    };
    media.addEventListener("change", handler);
    return () => media.removeEventListener("change", handler);
  }, [theme]);

  useEffect(() => {
    const loadPreferences = async () => {
      try {
        if (!getToken()) {
          setThemeState("system");
          return;
        }
        const prefs = await apiClient.getPreferences();
        setThemeState(prefs.theme);
      } catch (err) {
        console.warn("Failed to load preferences", err);
      } finally {
        setIsLoading(false);
      }
    };

    void loadPreferences();
  }, []);

  const setTheme = async (nextTheme: ThemeOption) => {
    setThemeState(nextTheme);
    if (!getToken()) return;

    try {
      await apiClient.updatePreferences({ theme: nextTheme });
    } catch (err) {
      console.warn("Failed to update theme", err);
    }
  };

  const value = useMemo(() => ({ theme, isLoading, setTheme }), [theme, isLoading]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}
