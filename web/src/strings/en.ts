/**
 * The one user-facing strings module (frontend-architecture.md §5, ADR-014
 * Q1). Every user-visible string in the app is a key here — never a literal
 * in a component or island. A CI grep (assertion 19 family) enforces this
 * once components exist; this task only establishes the shape.
 *
 * `S` is a flat, typed record exported `as const` so a lookup like
 * `S.errors.notAuthenticated` is a compile-time-checked string, not a raw
 * object traversal. Adding a language later (e.g. Telugu) is a second file
 * of the same shape plus a resolver — no component changes.
 *
 * Screens, forms, and their strings are added by the tasks that build them
 * (T-012 onward). This skeleton exists so `src/lib/api.ts` and later
 * `src/lib/errors.ts` have a stable import target from the start.
 */

export const S = {
  common: {
    loading: "Loading…",
    retry: "Retry",
  },
  errors: {
    /** Generic fallback for any error code the client does not recognise —
     * never render server-supplied text (frontend-architecture.md §4). */
    generic: "Something went wrong. Please try again.",
    network: "The server is taking too long. Please try again.",
    timeout: "The server is taking too long. Please try again.",
    sessionExpired: "Your session has expired.",
    unavailable: "The service is temporarily unavailable…",
  },
} as const;

export type Strings = typeof S;
