"use client";

/**
 * Complaints island (screen-inventory.md #4). **Partial (T-013): the
 * new-complaint form only** — the list and inline detail views are built by
 * later tasks (T-018+); this component renders nothing else yet.
 *
 * States implemented (screen-inventory.md #4 "States (new-complaint
 * form)"): empty, validating (inline + top-of-form summary), submitting,
 * server-error (incl. the REL-F1 "may already be saved" abort/timeout
 * state), success (complaint-number confirmation). Full duplicate/retry
 * hardening (double-submit races) lands at T-041 (TC-COMP-014); this task
 * covers the base path plus the one documented retry action.
 *
 * `client_request_id` (ADR-022/R2-6/REL-F1, frontend-architecture.md §4):
 * generated once via `crypto.randomUUID()` when this form mounts, kept in
 * state across every retry of the *same* submission, and only replaced
 * after a confirmed success or an explicit "Log another complaint" — never
 * regenerated per keystroke or per retry, which is what makes the server's
 * idempotent-insert (T-009) actually de-duplicate a client-side retry.
 */

import { useRouter } from "next/navigation";
import type { FormEvent, RefObject } from "react";
import { useEffect, useId, useRef, useState } from "react";
import { ApiError, apiPost } from "@/lib/api";
import { S } from "@/strings/en";

type RequiredField = "citizen_name" | "citizen_phone" | "description";

const FIELD_LABELS: Record<RequiredField, string> = {
  citizen_name: S.complaints.nameLabel,
  citizen_phone: S.complaints.phoneLabel,
  description: S.complaints.descriptionLabel,
};

const REQUIRED_MESSAGES: Record<RequiredField, string> = {
  citizen_name: S.complaints.requiredName,
  citizen_phone: S.complaints.requiredPhone,
  description: S.complaints.requiredDescription,
};

type FieldReasonCode = keyof typeof S.complaints.fieldReasonMessages;

function reasonMessage(reason: string): string {
  if (Object.hasOwn(S.complaints.fieldReasonMessages, reason)) {
    return S.complaints.fieldReasonMessages[reason as FieldReasonCode];
  }
  return S.errors.generic;
}

type FormStatus = "idle" | "submitting" | "may-be-saved" | "success";

/** `crypto.randomUUID()` must never fall back to a guessable id (an
 * unguessable client_request_id is a real security property here) — if it
 * is unavailable, the form must refuse to render rather than crash or fall
 * back to something predictable. */
function generateClientRequestId(): string | null {
  try {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
  } catch {
    // fall through to null below
  }
  return null;
}

interface SuccessResult {
  complaintNumber: string;
  duplicate: boolean;
}

export function ComplaintsApp() {
  return <NewComplaintForm />;
}

function NewComplaintForm() {
  const router = useRouter();
  const [clientRequestId, setClientRequestId] = useState<string | null>(() =>
    generateClientRequestId(),
  );
  const [status, setStatus] = useState<FormStatus>("idle");
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<RequiredField, string>>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [result, setResult] = useState<SuccessResult | null>(null);
  const [copied, setCopied] = useState(false);

  const nameRef = useRef<HTMLInputElement>(null);
  const phoneRef = useRef<HTMLInputElement>(null);
  const descriptionRef = useRef<HTMLTextAreaElement>(null);
  const summaryHeadingRef = useRef<HTMLHeadingElement>(null);
  const successHeadingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    if (status === "success") {
      successHeadingRef.current?.focus();
    }
  }, [status]);

  const nameId = useId();
  const phoneId = useId();
  const descriptionId = useId();

  const fieldRefs: Record<
    RequiredField,
    RefObject<HTMLInputElement | HTMLTextAreaElement | null>
  > = {
    citizen_name: nameRef,
    citizen_phone: phoneRef,
    description: descriptionRef,
  };
  const fieldIds: Record<RequiredField, string> = {
    citizen_name: nameId,
    citizen_phone: phoneId,
    description: descriptionId,
  };

  function focusField(field: RequiredField) {
    fieldRefs[field].current?.focus();
  }

  function readFormValues(form: HTMLFormElement) {
    return {
      citizen_name: (form.elements.namedItem("citizen_name") as HTMLInputElement).value,
      citizen_phone: (form.elements.namedItem("citizen_phone") as HTMLInputElement).value,
      description: (form.elements.namedItem("description") as HTMLTextAreaElement).value,
    };
  }

  function validate(values: Record<RequiredField, string>): Partial<Record<RequiredField, string>> {
    const errors: Partial<Record<RequiredField, string>> = {};
    (Object.keys(values) as RequiredField[]).forEach((field) => {
      if (values[field].trim().length === 0) {
        errors[field] = REQUIRED_MESSAGES[field];
      }
    });
    return errors;
  }

  async function submit(values: Record<RequiredField, string>) {
    if (clientRequestId === null) return;
    setStatus("submitting");
    setServerError(null);
    try {
      const response = await apiPost("/api/complaints", {
        client_request_id: clientRequestId,
        citizen_name: values.citizen_name,
        citizen_phone: values.citizen_phone,
        description: values.description,
      });
      setResult({ complaintNumber: response.complaint_number, duplicate: response.duplicate });
      setStatus("success");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "network_error" || err.code === "timeout") {
          // REL-F1: outcome unknown, never a bare Retry. The same
          // client_request_id is reused on "Try again" below.
          setStatus("may-be-saved");
          return;
        }
        if (err.status === 401) {
          // frontend-architecture.md §4: clear client state, show the
          // non-dismissible session-expired signal, then redirect to
          // /login — never leave citizen PII on screen past a 401.
          setResult(null);
          setFieldErrors({});
          setServerError(S.complaints.sessionExpiredRedirect);
          setStatus("idle");
          router.replace("/login?expired=1");
          return;
        }
        if (err.status === 403 && err.code === "must_change_password") {
          setResult(null);
          setFieldErrors({});
          setServerError(S.complaints.mustChangePasswordRedirect);
          setStatus("idle");
          router.replace("/change-password");
          return;
        }
        if (err.status === 422 && err.fields) {
          const errors: Partial<Record<RequiredField, string>> = {};
          for (const [field, reason] of Object.entries(err.fields)) {
            if (Object.hasOwn(FIELD_LABELS, field)) {
              errors[field as RequiredField] = reasonMessage(reason);
            }
          }
          setFieldErrors(errors);
          setStatus("idle");
          summaryHeadingRef.current?.focus();
          return;
        }
        setStatus("idle");
        setServerError(S.errors.generic);
        return;
      }
      setStatus("idle");
      setServerError(S.errors.generic);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (status === "submitting") return;

    const values = readFormValues(event.currentTarget);
    const errors = validate(values);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      // Focus moves to the summary heading on first appearance
      // (component-spec.md #8) so screen-reader users hear it immediately.
      requestAnimationFrame(() => summaryHeadingRef.current?.focus());
      return;
    }
    setFieldErrors({});
    void submit(values);
  }

  function handleTryAgain() {
    const form = document.getElementById("new-complaint-form") as HTMLFormElement | null;
    if (!form) return;
    const values = readFormValues(form);
    void submit(values);
  }

  function handleStartNewComplaint() {
    setClientRequestId(generateClientRequestId());
    setResult(null);
    setStatus("idle");
    setFieldErrors({});
    setServerError(null);
    setCopied(false);
  }

  async function handleCopyComplaintNumber() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.complaintNumber);
      setCopied(true);
    } catch {
      // Clipboard access can fail (permissions/unsupported context) — the
      // number is still shown on screen and can be selected/copied
      // manually, so this is a soft failure with no error state needed.
    }
  }

  if (clientRequestId === null) {
    return (
      <div role="alert" aria-live="assertive">
        {S.complaints.browserNotSupported}
      </div>
    );
  }

  if (status === "success" && result) {
    return (
      <div role="status" aria-live="polite">
        <h2 tabIndex={-1} ref={successHeadingRef}>
          {result.duplicate ? S.complaints.successHeadingDuplicate : S.complaints.successHeading}
        </h2>
        {result.duplicate && (
          <p role="status" aria-live="polite">
            {S.complaints.duplicateNotice}
          </p>
        )}
        <p>
          {S.complaints.successNumberLabel}:{" "}
          <span style={{ fontFamily: "monospace", letterSpacing: "0.1em", fontSize: "1.25rem" }}>
            {result.complaintNumber}
          </span>
        </p>
        <button type="button" onClick={handleCopyComplaintNumber}>
          {S.complaints.copyComplaintNumber}
        </button>
        <span aria-live="polite">{copied ? S.complaints.copiedConfirmation : ""}</span>
        <button type="button" onClick={handleStartNewComplaint}>
          {S.complaints.startNewComplaint}
        </button>
      </div>
    );
  }

  const errorFieldNames = Object.keys(fieldErrors) as RequiredField[];
  const isSubmitting = status === "submitting";
  const isFieldsLocked = status === "submitting" || status === "may-be-saved";

  return (
    <div>
      <h1>{S.complaints.newComplaintHeading}</h1>

      {status === "may-be-saved" && (
        <div role="alert" aria-live="assertive">
          <p>{S.complaints.mayBeSavedMessage}</p>
          {/* TODO(T-018): wire this to the complaints list view once it
              exists — until then a disabled control with an explanation
              reads better than a button that looks live but does nothing. */}
          <button
            type="button"
            disabled
            title={S.complaints.checkTheListUnavailable}
            aria-describedby="check-list-note"
          >
            {S.complaints.checkTheList}
          </button>
          <p id="check-list-note">{S.complaints.checkTheListUnavailable}</p>
          <button type="button" onClick={handleTryAgain}>
            {S.complaints.tryAgain}
          </button>
        </div>
      )}

      {serverError && (
        <div role="alert" aria-live="assertive">
          {serverError}
        </div>
      )}

      {errorFieldNames.length > 0 && (
        // Form Error Summary (component-spec.md #8, TC-COMP-011): heading +
        // one link per invalid field, each focusing its field on activation.
        <div role="alert" aria-live="assertive">
          <h2 tabIndex={-1} ref={summaryHeadingRef}>
            {errorFieldNames.length === 1
              ? S.complaints.errorSummaryHeadingOne
              : `${S.complaints.errorSummaryHeadingManyPrefix}${errorFieldNames.length}${S.complaints.errorSummaryHeadingManySuffix}`}
          </h2>
          <ul>
            {errorFieldNames.map((field) => (
              <li key={field}>
                <a
                  href={`#${fieldIds[field]}`}
                  onClick={(event) => {
                    event.preventDefault();
                    focusField(field);
                  }}
                >
                  {FIELD_LABELS[field]}: {fieldErrors[field]}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      <form id="new-complaint-form" onSubmit={handleSubmit}>
        <div>
          <label htmlFor={nameId}>
            {S.complaints.nameLabel}
            {S.common.requiredSuffix}
          </label>
          <input
            id={nameId}
            name="citizen_name"
            type="text"
            required
            aria-required="true"
            ref={nameRef}
            aria-invalid={fieldErrors.citizen_name ? "true" : undefined}
            aria-describedby={fieldErrors.citizen_name ? `${nameId}-error` : undefined}
            aria-disabled={isFieldsLocked}
            readOnly={isFieldsLocked}
          />
          {fieldErrors.citizen_name && <p id={`${nameId}-error`}>{fieldErrors.citizen_name}</p>}
        </div>

        <div>
          <label htmlFor={phoneId}>
            {S.complaints.phoneLabel}
            {S.common.requiredSuffix}
          </label>
          <input
            id={phoneId}
            name="citizen_phone"
            type="text"
            inputMode="tel"
            required
            aria-required="true"
            ref={phoneRef}
            aria-invalid={fieldErrors.citizen_phone ? "true" : undefined}
            aria-describedby={fieldErrors.citizen_phone ? `${phoneId}-error` : undefined}
            aria-disabled={isFieldsLocked}
            readOnly={isFieldsLocked}
          />
          {fieldErrors.citizen_phone && <p id={`${phoneId}-error`}>{fieldErrors.citizen_phone}</p>}
        </div>

        <div>
          <label htmlFor={descriptionId}>
            {S.complaints.descriptionLabel}
            {S.common.requiredSuffix}
          </label>
          <textarea
            id={descriptionId}
            name="description"
            required
            aria-required="true"
            ref={descriptionRef}
            aria-invalid={fieldErrors.description ? "true" : undefined}
            aria-describedby={fieldErrors.description ? `${descriptionId}-error` : undefined}
            aria-disabled={isFieldsLocked}
            readOnly={isFieldsLocked}
          />
          {fieldErrors.description && (
            <p id={`${descriptionId}-error`}>{fieldErrors.description}</p>
          )}
        </div>

        <div role="status" aria-live="polite">
          <button type="submit" aria-disabled={isSubmitting}>
            {isSubmitting ? S.complaints.submitting : S.complaints.submit}
          </button>
        </div>
      </form>
    </div>
  );
}
