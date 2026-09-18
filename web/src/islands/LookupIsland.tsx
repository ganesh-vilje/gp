"use client";

/**
 * Public status-lookup island (screen-inventory.md #1, AC-006/007/018,
 * NFR-011). This is the root, **unauthenticated** route — no `AuthProvider`,
 * no session requirement. It must still send `X-CSRF-Token` on its one
 * unsafe request (`POST /api/lookup`), per the anonymous-seed lifecycle
 * documented in `src/lib/csrf.ts` — so, exactly like T-012's `LoginForm`,
 * it fetches `GET /api/session` itself on mount to obtain that token before
 * the "Check status" control is usable.
 *
 * States implemented (screen-inventory.md #1 "States"):
 * - CSRF-seed pending ("Preparing…"), slow (>4s, retry affordance), failed
 *   ("Unavailable — reload the page"), and a cookies-disabled variant of the
 *   same failure (checked via `navigator.cookieEnabled`, TC-COMP-003).
 * - Empty/ready, invalid input (client-side, no network call — TC-COMP-001),
 *   loading ("Checking…"), success, not-found (404), rate-limited (429,
 *   countdown re-enable, same pattern as `LoginForm`), unavailable (503),
 *   timeout/network error (TC-COMP-002).
 * - `<noscript>` fallback lives in `src/app/page.tsx` (rendered without any
 *   script, per screen-inventory.md).
 *
 * The success response is PII-free by contract (api-contract.md §4: only
 * `complaint_number`, `status`, `public_update`, `date_logged`) — this
 * component never expects or reads a citizen name/phone/description field.
 * `public_update` is a fixed enum code, mapped through
 * `S.lookup.publicUpdateMessages` — never rendered raw (frontend-architecture
 * §4's "never render server-supplied text").
 */

import { type FormEvent, useEffect, useId, useRef, useState } from "react";
import { ApiError, apiGet, apiPost } from "@/lib/api";
import { setCsrfToken } from "@/lib/csrf";
import { S } from "@/strings/en";

type SessionState = "checking" | "slow" | "ready" | "unavailable" | "cookies-disabled";

type LookupPhase =
  | "idle"
  | "invalid"
  | "loading"
  | "success"
  | "not-found"
  | "rate-limited"
  | "unavailable"
  | "network-error";

interface LookupResult {
  complaintNumber: string;
  publicUpdateMessage: string;
  dateLogged: string;
}

const SLOW_SEED_THRESHOLD_MS = 4000;

/** Mirrors `api/app/core/complaint_number.py::normalise` closely enough for
 * an instant client-side format hint — the server remains the source of
 * truth for validity (checksum included); this only blocks obviously blank
 * input before firing a request (TC-COMP-001). */
function normaliseComplaintNumber(raw: string): string {
  return raw.trim().toUpperCase().replaceAll("-", "").replaceAll(" ", "");
}

export function LookupIsland() {
  const [sessionState, setSessionState] = useState<SessionState>("checking");
  const [phase, setPhase] = useState<LookupPhase>("idle");
  const [inputError, setInputError] = useState<string | null>(null);
  const [result, setResult] = useState<LookupResult | null>(null);
  const [rateLimitSeconds, setRateLimitSeconds] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const [seedAttempt, setSeedAttempt] = useState(0);

  const inputRef = useRef<HTMLInputElement>(null);
  const successHeadingRef = useRef<HTMLHeadingElement>(null);
  const inputId = useId();
  const errorId = useId();
  const hintId = useId();

  // Fix 2 (accessibility-reviewer, T-014 rework): move focus to the success
  // heading when it appears — mirrors LoginForm.tsx's mount-only focus
  // pattern (T-012) so keyboard/screen-reader users aren't stranded on
  // `<body>` after a successful lookup.
  useEffect(() => {
    if (phase === "success") {
      successHeadingRef.current?.focus();
    }
  }, [phase]);

  // Establish the anonymous CSRF token (frontend-architecture.md §4's
  // "CSRF seed lifecycle") on mount, and again whenever the citizen presses
  // the slow-seed retry affordance.
  // biome-ignore lint/correctness/useExhaustiveDependencies: re-run only on mount and explicit retry (seedAttempt).
  useEffect(() => {
    if (typeof navigator !== "undefined" && navigator.cookieEnabled === false) {
      setSessionState("cookies-disabled");
      return;
    }

    let cancelled = false;
    setSessionState("checking");

    const slowTimer = setTimeout(() => {
      if (!cancelled) setSessionState((current) => (current === "checking" ? "slow" : current));
    }, SLOW_SEED_THRESHOLD_MS);

    apiGet("/api/session")
      .then((response) => {
        if (cancelled) return;
        setCsrfToken(response.csrf_token);
        setSessionState("ready");
      })
      .catch(() => {
        if (!cancelled) setSessionState("unavailable");
      });

    return () => {
      cancelled = true;
      clearTimeout(slowTimer);
    };
  }, [seedAttempt]);

  // Rate-limit countdown (interaction-patterns.md "Rate-limit / backoff
  // countdown"): decrements once per second, only then re-enables the
  // control — same load-bearing guard as LoginForm's countdown.
  useEffect(() => {
    if (rateLimitSeconds === null) return;
    if (rateLimitSeconds <= 0) {
      setPhase("idle");
      setRateLimitSeconds(null);
      return;
    }
    const timer = setInterval(() => {
      setRateLimitSeconds((current) => (current === null ? null : current - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [rateLimitSeconds]);

  function clearFieldError() {
    if (inputError) setInputError(null);
    if (phase === "invalid" || phase === "not-found" || phase === "network-error") {
      setPhase("idle");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // Load-bearing guard: the button's `aria-disabled` is visual only, this
    // early return is what actually blocks a resubmission.
    if (phase === "loading" || phase === "rate-limited" || sessionState !== "ready") return;

    const raw = inputRef.current?.value ?? "";
    const normalised = normaliseComplaintNumber(raw);
    if (normalised.length === 0) {
      // TC-COMP-001: instant, no network call.
      setInputError(S.lookup.invalidInput);
      setPhase("invalid");
      return;
    }

    setInputError(null);
    setResult(null);
    setPhase("loading");

    try {
      const response = await apiPost("/api/lookup", { complaint_number: normalised });
      const message =
        response.public_update in S.lookup.publicUpdateMessages
          ? S.lookup.publicUpdateMessages[
              response.public_update as keyof typeof S.lookup.publicUpdateMessages
            ]
          : S.errors.generic;
      setResult({
        complaintNumber: response.complaint_number,
        publicUpdateMessage: message,
        dateLogged: response.date_logged,
      });
      setPhase("success");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 400) {
          setInputError(S.lookup.invalidInput);
          setPhase("invalid");
          return;
        }
        if (err.status === 404) {
          setPhase("not-found");
          return;
        }
        if (err.status === 429) {
          setPhase("rate-limited");
          setRateLimitSeconds(err.retryAfterSeconds ?? 60);
          return;
        }
        if (err.status === 503) {
          setPhase("unavailable");
          return;
        }
        // network_error / timeout / csrf_not_ready (TC-COMP-002).
        setPhase("network-error");
        return;
      }
      setPhase("network-error");
    }
  }

  async function handleCopyComplaintNumber() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.complaintNumber);
      setCopied(true);
    } catch {
      // Soft failure — the number is still visible/selectable on screen.
    }
  }

  function handleCheckAnother() {
    setResult(null);
    setPhase("idle");
    setCopied(false);
    setInputError(null);
    if (inputRef.current) inputRef.current.value = "";
    inputRef.current?.focus();
  }

  // "Preparing…"/slow/failed states share the button+message live region
  // (A11Y-12) — the field stays enterable throughout (screen-inventory.md #1
  // "Empty (initial), CSRF seed pending").
  let buttonLabel: string = S.lookup.checkStatus;
  let buttonDisabled = false;
  if (sessionState === "checking") {
    buttonLabel = S.lookup.preparing;
    buttonDisabled = true;
  } else if (sessionState === "slow") {
    buttonLabel = S.lookup.preparing;
    buttonDisabled = true;
  } else if (sessionState === "unavailable") {
    buttonLabel = S.lookup.unavailablePreparing;
    buttonDisabled = true;
  } else if (sessionState === "cookies-disabled") {
    buttonLabel = S.lookup.unavailablePreparing;
    buttonDisabled = true;
  } else if (phase === "loading") {
    buttonLabel = S.lookup.checking;
    buttonDisabled = true;
  } else if (phase === "rate-limited") {
    buttonLabel = `${S.lookup.rateLimitedPrefix}${rateLimitSeconds ?? 0}${S.lookup.rateLimitedSuffix}`;
    buttonDisabled = true;
  }

  const isSuccess = phase === "success" && result !== null;
  const describedByIds = [inputError ? errorId : null, hintId].filter(Boolean).join(" ");

  return (
    <div>
      <h1>{S.lookup.heading}</h1>

      {/* Fix 1 (accessibility-reviewer, T-014 rework): a single, always-mounted
          live region whose TEXT CONTENT toggles on `phase` — never an early
          return that swaps the whole subtree, so the live-region element is
          already present in the DOM before the success text is inserted and
          is reliably announced. */}
      <h2 ref={successHeadingRef} tabIndex={-1} role="status" aria-live="polite">
        {isSuccess ? S.lookup.successHeading : ""}
      </h2>

      {sessionState === "cookies-disabled" && (
        <div role="alert" aria-live="assertive">
          {S.lookup.cookiesDisabled}
        </div>
      )}

      {phase === "not-found" && (
        <div role="alert" aria-live="polite">
          {S.lookup.notFound}
        </div>
      )}

      {phase === "rate-limited" && (
        <div role="alert" aria-live="polite">
          {S.lookup.rateLimited}
        </div>
      )}

      {phase === "unavailable" && (
        <div role="alert" aria-live="polite">
          {S.lookup.unavailable}
        </div>
      )}

      {phase === "network-error" && (
        <div role="alert" aria-live="polite">
          {S.errors.network}
        </div>
      )}

      {isSuccess && result ? (
        <div>
          <p>
            {S.lookup.complaintNumberLabel}:{" "}
            <span className="complaint-number">{result.complaintNumber}</span>
          </p>
          <p>{result.publicUpdateMessage}</p>
          <p>
            {S.lookup.dateLoggedLabel}: {result.dateLogged}
          </p>
          <button type="button" onClick={handleCopyComplaintNumber}>
            {S.lookup.copyComplaintNumber}
          </button>
          <span aria-live="polite">{copied ? S.lookup.copiedConfirmation : ""}</span>
          <button type="button" onClick={handleCheckAnother}>
            {S.lookup.checkAnother}
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          <div>
            <label htmlFor={inputId}>{S.lookup.inputLabel}</label>
            <p id={hintId}>{S.lookup.inputHint}</p>
            <input
              id={inputId}
              name="complaint_number"
              type="text"
              required
              aria-required="true"
              ref={inputRef}
              placeholder={S.lookup.inputHint}
              aria-invalid={inputError ? "true" : undefined}
              aria-describedby={describedByIds || undefined}
              onChange={clearFieldError}
            />
            {inputError && (
              <p id={errorId} role="alert">
                {inputError}
              </p>
            )}
          </div>

          {sessionState === "slow" && (
            <p>
              <button type="button" onClick={() => setSeedAttempt((attempt) => attempt + 1)}>
                {S.lookup.retryPreparing}
              </button>
            </p>
          )}

          <div role="status" aria-live="polite">
            <button type="submit" aria-disabled={buttonDisabled}>
              {buttonLabel}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
