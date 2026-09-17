/**
 * The single fetch wrapper (frontend-architecture.md §4): "`src/lib/api.ts`
 * is the **only** module that calls `fetch`." No component, island, or hook
 * may call `fetch` directly — that is enforced by code review, not a CI
 * grep, per coding-guidelines.md's naming section.
 *
 * Every call:
 * - targets `${NEXT_PUBLIC_API_BASE_URL}` (build-time public value);
 * - sets `credentials: "include"`;
 * - sends `X-CSRF-Token` on every unsafe method (GET/HEAD/OPTIONS excluded);
 * - wraps an `AbortController` with a 10 s timeout (NFR-011);
 * - is typed against `src/api-types.ts` — a field the schema does not
 *   declare cannot be read;
 * - throws an `ApiError` carrying the envelope's `code`/`fields`/`request_id`
 *   (or a synthetic `network_error`/`timeout` code for a transport failure)
 *   so callers map `code` to a `src/strings/en.ts` key themselves — this
 *   module does not know about strings (frontend-architecture.md §5 keeps
 *   that mapping in `src/lib/errors.ts`, a later task).
 */

import type { paths } from "@/api-types";
import { getCsrfToken } from "@/lib/csrf";

const REQUEST_TIMEOUT_MS = 10_000;

type GetPaths = {
  [K in keyof paths]: paths[K] extends { get: unknown } ? K : never;
}[keyof paths];

type PostPaths = {
  [K in keyof paths]: paths[K] extends { post: unknown } ? K : never;
}[keyof paths];

type SuccessBody<Op> = Op extends {
  responses: infer R;
}
  ? R extends { 200: { content: { "application/json": infer Body } } }
    ? Body
    : never
  : never;

type RequestBody<Op> = Op extends {
  requestBody: { content: { "application/json": infer Body } };
}
  ? Body
  : never;

/** Every non-2xx response from every route shares this shape
 * (error-catalog.md). */
export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    /** Closed set of short reason codes keyed by field name — e.g.
     * `"required"`, `"too_short"`, `"too_long"`, `"unexpected_field"`,
     * `"invalid_format"` (see api/app/api/exception_handlers.py's
     * `_VALIDATION_REASON_BY_PYDANTIC_TYPE`). Never raw server prose.
     * Callers must map each code through `src/strings/en.ts`; never render
     * a `fields` value directly. */
    fields?: Record<string, string> | null;
    request_id: string;
  };
}

function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (typeof value !== "object" || value === null) return false;
  const error = (value as { error?: unknown }).error;
  if (typeof error !== "object" || error === null) return false;
  return typeof (error as { code?: unknown }).code === "string";
}

/** A transport-level failure has no server envelope; these two synthetic
 * codes let callers use the same `switch (err.code)` for both cases. */
export type SyntheticErrorCode = "network_error" | "timeout" | "csrf_not_ready";

export class ApiError extends Error {
  readonly code: string | SyntheticErrorCode;
  readonly status: number | null;
  /** See `ApiErrorEnvelope.fields` — a closed set of short reason codes,
   * never raw server prose. Map through `src/strings/en.ts` before display. */
  readonly fields: Record<string, string> | null;
  readonly requestId: string | null;
  readonly retryAfterSeconds: number | null;

  constructor(params: {
    code: string | SyntheticErrorCode;
    status: number | null;
    fields?: Record<string, string> | null;
    requestId?: string | null;
    retryAfterSeconds?: number | null;
  }) {
    super(params.code);
    this.name = "ApiError";
    this.code = params.code;
    this.status = params.status;
    this.fields = params.fields ?? null;
    this.requestId = params.requestId ?? null;
    this.retryAfterSeconds = params.retryAfterSeconds ?? null;
  }
}

function apiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is not set at build time.");
  }
  return base;
}

function parseRetryAfter(response: Response): number | null {
  const header = response.headers.get("Retry-After");
  if (!header) return null;
  const seconds = Number.parseInt(header, 10);
  return Number.isNaN(seconds) ? null : seconds;
}

async function request<TBody = never>(
  method: "GET" | "POST",
  path: string,
  body?: TBody,
): Promise<unknown> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const headers: Record<string, string> = {};
  let requestBody: string | undefined;
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    requestBody = JSON.stringify(body);
  }
  if (method === "POST") {
    const csrfToken = getCsrfToken();
    if (!csrfToken) {
      clearTimeout(timeout);
      throw new ApiError({ code: "csrf_not_ready", status: null });
    }
    headers["X-CSRF-Token"] = csrfToken;
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      method,
      credentials: "include",
      headers,
      body: requestBody,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError({ code: "timeout", status: null });
    }
    throw new ApiError({ code: "network_error", status: null });
  } finally {
    clearTimeout(timeout);
  }

  if (response.status === 204) {
    return undefined;
  }

  const text = await response.text();
  let json: unknown;
  if (text.length > 0) {
    try {
      json = JSON.parse(text);
    } catch {
      throw new ApiError({ code: "network_error", status: response.status });
    }
  } else {
    json = undefined;
  }

  if (!response.ok) {
    if (isApiErrorEnvelope(json)) {
      throw new ApiError({
        code: json.error.code,
        status: response.status,
        fields: json.error.fields ?? null,
        requestId: json.error.request_id,
        retryAfterSeconds: parseRetryAfter(response),
      });
    }
    throw new ApiError({ code: "network_error", status: response.status });
  }

  return json;
}

/** Typed `GET` against a route declared in `src/api-types.ts`. */
export function apiGet<P extends GetPaths>(path: P): Promise<SuccessBody<paths[P]["get"]>> {
  return request("GET", path as string) as Promise<SuccessBody<paths[P]["get"]>>;
}

/** Typed `POST` against a route declared in `src/api-types.ts`. `body` is
 * required exactly when the route declares a request body. */
export function apiPost<P extends PostPaths>(
  path: P,
  ...args: RequestBody<paths[P]["post"]> extends never ? [] : [body: RequestBody<paths[P]["post"]>]
): Promise<SuccessBody<paths[P]["post"]>> {
  const body = args[0];
  return request("POST", path as string, body) as Promise<SuccessBody<paths[P]["post"]>>;
}
