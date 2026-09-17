"use client";

/**
 * `AuthProvider` (frontend-architecture.md §1/§3): hydrates
 * `{authenticated, username, is_admin_clerk, must_change_password}` from
 * `GET /api/session` on mount of any clerk route.
 *
 * - "Client-side route guards are UX only" (frontend-architecture.md §2) —
 *   the API is the security boundary, this only redirects for a better
 *   experience; a 401 from any authenticated call is handled separately by
 *   the caller (frontend-architecture.md §4's response table), not here.
 * - No session / an anonymous session redirects to `/login`
 *   (`router.replace`, matching LoginForm's own already-authenticated
 *   redirect so neither page is ever left in browser history mid-check).
 * - A `must_change_password` session redirects to `/change-password`
 *   (frontend-architecture.md §2) — children of this provider are never
 *   rendered in that case, since every other clerk route is off-limits
 *   while a password change is pending.
 * - While the check is in flight, children are not rendered — a
 *   "Checking your session…" status region is shown instead, matching
 *   LoginForm's `sessionCheck` pattern (screen-inventory.md #2/#4).
 * - `csrf_token` is stored via `setCsrfToken` as soon as it is known, so the
 *   first unsafe request a child island makes (e.g. `POST /api/complaints`)
 *   already has a valid token.
 *
 * This module stays a plain `.ts` file (frontend-architecture.md §1 names it
 * `src/lib/auth.ts`, not `.tsx`) — its one rendered element is built with
 * `createElement` rather than JSX for that reason.
 */

import { useRouter } from "next/navigation";
import {
  createContext,
  createElement,
  type ReactNode,
  useContext,
  useEffect,
  useState,
} from "react";
import { apiGet } from "@/lib/api";
import { setCsrfToken } from "@/lib/csrf";
import { S } from "@/strings/en";

export interface AuthContextValue {
  username: string;
  isAdminClerk: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

type CheckState = "checking" | "authenticated" | "redirecting";

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<CheckState>("checking");
  const [value, setValue] = useState<AuthContextValue | null>(null);

  // biome-ignore lint/correctness/useExhaustiveDependencies: mount-only check; router is stable.
  useEffect(() => {
    let cancelled = false;
    apiGet("/api/session")
      .then((response) => {
        if (cancelled) return;
        if (!response.authenticated) {
          setState("redirecting");
          router.replace("/login");
          return;
        }
        setCsrfToken(response.csrf_token);
        if (response.user.must_change_password) {
          setState("redirecting");
          router.replace("/change-password");
          return;
        }
        setValue({
          username: response.user.username,
          isAdminClerk: response.user.is_admin_clerk,
        });
        setState("authenticated");
      })
      .catch(() => {
        // A failed session check cannot be trusted as authenticated — fail
        // safe to the login page (mirrors LoginForm's own anonymous
        // fallback, but this route has no safe unauthenticated form to show).
        if (!cancelled) {
          setState("redirecting");
          router.replace("/login");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state !== "authenticated" || value === null) {
    return createElement(
      "div",
      { role: "status", "aria-live": "polite" },
      S.common.checkingSession,
    );
  }

  return createElement(AuthContext.Provider, { value }, children);
}

/** Read the current authenticated clerk's identity. Throws outside an
 * `AuthProvider` — every clerk-only island must be mounted inside one. */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
