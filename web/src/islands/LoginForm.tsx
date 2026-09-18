"use client";

/**
 * Login form island (screen-inventory.md #2, AC-001, interaction-patterns.md).
 *
 * - Native `required`/`aria-required` blocks submission client-side when a
 *   field is empty — no request is fired (TC-COMP-004).
 * - A 401 always shows the same generic message and clears + refocuses the
 *   password field (TC-COMP-005; coding-guidelines.md R4-4 — never
 *   distinguish "unknown user" from "wrong password"). The password field is
 *   also flagged `aria-invalid` + `aria-describedby` at the same time
 *   (accessibility-strategy.md).
 * - A 429 keeps the submit control disabled and counts down once per second
 *   (interaction-patterns.md rate-limit/backoff pattern, screen-inventory.md
 *   #2), re-enabling automatically at zero.
 * - On mount, the session is checked via `GET /api/session`; an already
 *   authenticated session redirects straight to /complaints without ever
 *   rendering the form (screen-inventory.md #2 "Already authenticated").
 * - A successful response rotates the in-memory CSRF token (ARCH-F4 / TD-B15)
 *   before navigating on, since the old token no longer matches after login.
 */

import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, apiGet, apiPost } from "@/lib/api";
import { setCsrfToken } from "@/lib/csrf";
import { S } from "@/strings/en";

type FormStatus = "idle" | "submitting" | "rate-limited";
type SessionCheck = "checking" | "anonymous" | "redirecting";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionExpired = searchParams?.get("expired") === "1";

  const [sessionCheck, setSessionCheck] = useState<SessionCheck>("checking");
  const [status, setStatus] = useState<FormStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [rateLimitSeconds, setRateLimitSeconds] = useState<number | null>(null);

  const passwordRef = useRef<HTMLInputElement>(null);
  const sessionBannerRef = useRef<HTMLDivElement>(null);
  const passwordHasError = errorMessage !== null;

  // screen-inventory.md #2 "Already authenticated": check the session once on
  // mount and redirect before the form ever renders. Nothing else in this
  // component should run/render until this resolves.
  // biome-ignore lint/correctness/useExhaustiveDependencies: mount-only check; router is stable.
  useEffect(() => {
    let cancelled = false;
    apiGet("/api/session")
      .then((response) => {
        if (cancelled) return;
        setCsrfToken(response.csrf_token);
        if (response.authenticated) {
          setSessionCheck("redirecting");
          router.replace("/complaints");
        } else {
          setSessionCheck("anonymous");
        }
      })
      .catch(() => {
        // Treat a failed session check as anonymous — the login form itself
        // is the safe fallback; do not block the user out.
        if (!cancelled) setSessionCheck("anonymous");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Focus the session-expiry banner on mount only — a callback ref would
  // re-run on every re-render and repeatedly steal focus back.
  // biome-ignore lint/correctness/useExhaustiveDependencies: focus on mount only, not on every re-render.
  useEffect(() => {
    if (sessionExpired) {
      sessionBannerRef.current?.focus();
    }
  }, []);

  // Rate-limit countdown: decrements once per second and only then re-enables
  // the submit control. Do not flip `status` back to "idle" until zero.
  useEffect(() => {
    if (rateLimitSeconds === null) return;
    if (rateLimitSeconds <= 0) {
      setStatus("idle");
      setRateLimitSeconds(null);
      return;
    }
    const timer = setInterval(() => {
      setRateLimitSeconds((current) => (current === null ? null : current - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [rateLimitSeconds]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // Load-bearing guard: the submit button's `aria-disabled` is visual only
    // (no pointer-events/disabled attribute), so this early return is what
    // actually blocks submission while submitting or rate-limited.
    if (status === "submitting" || status === "rate-limited") return;

    const form = event.currentTarget;
    const username = (form.elements.namedItem("username") as HTMLInputElement).value;
    const password = (form.elements.namedItem("password") as HTMLInputElement).value;

    setErrorMessage(null);
    setStatus("submitting");

    try {
      const response = await apiPost("/api/login", { username, password });
      // ARCH-F4 / TD-B15: rotate the stored CSRF token from the login
      // response body before issuing any further unsafe request.
      setCsrfToken(response.csrf_token);
      if (response.user.must_change_password) {
        router.push("/change-password");
      } else {
        router.push("/complaints");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setStatus("idle");
          setErrorMessage(S.login.invalidCredentials);
          if (passwordRef.current) {
            passwordRef.current.value = "";
            passwordRef.current.focus();
          }
          return;
        }
        if (err.status === 429) {
          // Stay disabled for the full countdown — status only returns to
          // "idle" when the countdown effect above reaches zero.
          setErrorMessage(
            `${S.login.rateLimitedPrefix}${err.retryAfterSeconds ?? "a few"}${S.login.rateLimitedSuffix}`,
          );
          setStatus("rate-limited");
          setRateLimitSeconds(err.retryAfterSeconds ?? 5);
          return;
        }
        // network_error / timeout / csrf_not_ready — generic copy only, per
        // src/lib/api.ts's doc comment: never render server-supplied text.
        setStatus("idle");
        setErrorMessage(S.errors.network);
        return;
      }
      setStatus("idle");
      setErrorMessage(S.errors.generic);
    }
  }

  function clearFieldError() {
    if (errorMessage) setErrorMessage(null);
  }

  if (sessionCheck !== "anonymous") {
    // "Already authenticated" (redirecting) or the check is still in flight:
    // never flash the login form in either case.
    return (
      <div role="status" aria-live="polite">
        {S.login.checkingSession}
      </div>
    );
  }

  const isSubmitting = status === "submitting";
  const isRateLimited = status === "rate-limited";
  const isBusy = isSubmitting || isRateLimited;

  return (
    <div>
      {sessionExpired && (
        // Focus must move to the banner on arrival (A11Y-06), matching the
        // Form Error Summary convention (component-spec.md #8). The focus
        // call itself lives in the mount-only effect above.
        <div role="alert" aria-live="assertive" tabIndex={-1} ref={sessionBannerRef}>
          {S.login.sessionExpiredBanner}
        </div>
      )}
      {errorMessage && (
        <div id="login-error" role="alert" aria-live="assertive">
          {errorMessage}
        </div>
      )}
      <h1>{S.login.heading}</h1>
      <form onSubmit={handleSubmit}>
        <p>{S.login.allFieldsRequired}</p>
        <div>
          <label htmlFor="username">{S.login.usernameLabel}</label>
          <input
            id="username"
            name="username"
            type="text"
            required
            aria-required="true"
            autoComplete="username"
            aria-disabled={isBusy}
            readOnly={isBusy}
            onChange={clearFieldError}
          />
        </div>
        <div>
          <label htmlFor="password">{S.login.passwordLabel}</label>
          <input
            id="password"
            name="password"
            ref={passwordRef}
            type={showPassword ? "text" : "password"}
            required
            aria-required="true"
            autoComplete="current-password"
            aria-disabled={isBusy}
            readOnly={isBusy}
            aria-invalid={passwordHasError ? "true" : undefined}
            aria-describedby={passwordHasError ? "login-error" : undefined}
            onChange={clearFieldError}
          />
          <button type="button" onClick={() => setShowPassword((value) => !value)}>
            {showPassword ? S.login.hidePassword : S.login.showPassword}
          </button>
        </div>
        <div role="status" aria-live="polite">
          <button type="submit" aria-disabled={isBusy}>
            {isSubmitting
              ? S.login.submitting
              : isRateLimited
                ? `${S.login.rateLimitedPrefix}${rateLimitSeconds ?? 0}${S.login.rateLimitedSuffix}`
                : S.login.submit}
          </button>
        </div>
      </form>
    </div>
  );
}
