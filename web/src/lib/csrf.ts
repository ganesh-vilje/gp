/**
 * CSRF token storage (frontend-architecture.md §4 "CSRF seed lifecycle").
 *
 * The API is the security boundary; this module is UX plumbing only, never
 * enforcement (frontend-architecture.md line 6).
 *
 * How this matches `app/middleware/csrf.py`:
 * - The server issues an httpOnly `__Host-csrfseed` cookie (anonymous) or a
 *   session-bound CSRF token (authenticated) and returns the *comparison*
 *   value — `csrf_token` — in the body of `GET /api/session`, `POST
 *   /api/login`, and `POST /api/logout`. The client never reads or sets any
 *   cookie itself (the seed cookie is httpOnly and invisible to JS by
 *   design) — it only remembers whatever `csrf_token` string the last
 *   response body carried and echoes it back verbatim as `X-CSRF-Token` on
 *   every unsafe request, alongside `credentials: "include"` so the
 *   matching cookie rides along automatically. This is *not* a classic
 *   double-submit-cookie pattern (the client cannot read the cookie to
 *   "submit" it) — it is a server-issued bearer-style token the server
 *   re-derives from the cookie it already has.
 * - `GET`/`HEAD`/`OPTIONS` never send the header (the server does not check
 *   it on safe methods either).
 * - After login, logout, or a password change, the client MUST replace its
 *   stored token from that response's body before issuing the next unsafe
 *   request — the old token no longer matches (ARCH-F4).
 */

let currentCsrfToken: string | null = null;

/** Replace the remembered CSRF token — call with the `csrf_token` field from
 * any `GET /api/session`, `POST /api/login`, or `POST /api/logout` response
 * body. */
export function setCsrfToken(token: string): void {
  currentCsrfToken = token;
}

/** The token to send as `X-CSRF-Token` on the next unsafe request, or `null`
 * if none has been obtained yet (the caller must fetch `GET /api/session`
 * first). */
export function getCsrfToken(): string | null {
  return currentCsrfToken;
}

/** Test-only: reset in-memory state between Vitest cases. */
export function resetCsrfTokenForTests(): void {
  currentCsrfToken = null;
}
