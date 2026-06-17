import { useCallback, useEffect, useState } from "react";

export type ThemeMode = "auto" | "light" | "dark";

/**
 * Dark mode is a DEFERRED phase. The `[data-theme="dark"]` token ramp in
 * tokens.css is intentionally empty and there is no `prefers-color-scheme`
 * fallback yet, so "dark" and "auto" would both resolve to the light tokens
 * — i.e. selecting them does nothing. Until the dark ramp is filled and
 * contrast re-verified, we hard-pin light and the UI disables the auto/dark
 * controls (see ShellTopbar). Flip this to `true` when dark ships.
 */
export const DARK_MODE_ENABLED = false;

const STORAGE_KEY = "patentagent-theme";

function readStoredTheme(): ThemeMode {
  if (!DARK_MODE_ENABLED) return "light";
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "auto") return stored;
  } catch {
    // localStorage unavailable
  }
  return "auto";
}

function applyTheme(mode: ThemeMode) {
  const root = document.documentElement;
  // While dark is deferred, always render light regardless of the stored or
  // requested value, so a previously-saved "auto"/"dark" can't strand the
  // user on an unstyled (no-op) theme.
  const effective: ThemeMode = DARK_MODE_ENABLED ? mode : "light";
  if (effective === "auto") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", effective);
  }
}

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeMode>(readStoredTheme);

  useEffect(() => {
    applyTheme(theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // ignore
    }
  }, [theme]);

  const setTheme = useCallback((mode: ThemeMode) => {
    // Ignore unsupported modes while dark is deferred.
    if (!DARK_MODE_ENABLED && mode !== "light") return;
    setThemeState(mode);
  }, []);

  return { theme, setTheme } as const;
}
