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
    checkingSession: "Checking your session…",
    requiredSuffix: " (required)",
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
  login: {
    heading: "Log in",
    usernameLabel: "Username",
    passwordLabel: "Password",
    allFieldsRequired: "All fields are required",
    showPassword: "Show password",
    hidePassword: "Hide password",
    submit: "Log in",
    submitting: "Signing in…",
    /** Generic on purpose (R4-4 in coding-guidelines.md) — never distinguish
     * "unknown username" from "wrong password". */
    invalidCredentials: "Incorrect username or password.",
    rateLimitedPrefix: "Too many attempts. Try again in ",
    rateLimitedSuffix: "s.",
    sessionExpiredBanner: "Your session has expired. Please log in again.",
    checkingSession: "Checking your session…",
  },
  complaints: {
    newComplaintHeading: "New complaint",
    nameLabel: "Citizen name",
    phoneLabel: "Citizen phone",
    descriptionLabel: "Description",
    submit: "Submit complaint",
    submitting: "Submitting…",
    startNewComplaint: "Log another complaint",
    checkTheList: "Check the list",
    tryAgain: "Try again",
    /** Form Error Summary (component-spec.md #8) heading — singular/plural
     * split, following the login rate-limit prefix/suffix pattern. */
    errorSummaryHeadingOne: "There is 1 problem with this form",
    errorSummaryHeadingManyPrefix: "There are ",
    errorSummaryHeadingManySuffix: " problems with this form",
    /** Required-field messages (BR-006/007/012/014) — never raw server
     * prose; every reason code from `ApiError.fields` is mapped through
     * `fieldReasonMessages` below instead. */
    requiredName: "Enter the citizen's name.",
    requiredPhone: "Enter the citizen's phone number.",
    requiredDescription: "Enter a description of the complaint.",
    /** Closed set of reason codes the API may return in `fields`
     * (api/app/api/exception_handlers.py's
     * `_VALIDATION_REASON_BY_PYDANTIC_TYPE`, src/lib/api.ts's doc comment).
     * Never render `err.fields[field]` directly. */
    fieldReasonMessages: {
      required: "This field is required.",
      too_short: "This value is too short.",
      too_long: "This value is too long.",
      invalid_format: "This value is not in the expected format.",
      unexpected_field: "This field is not allowed.",
    },
    /** REL-F1/ADR-022 — an aborted/timed-out create whose outcome is
     * unknown; never a bare Retry (frontend-architecture.md §4). Full
     * duplicate/retry hardening lands at T-041; this is the base state. */
    mayBeSavedMessage:
      "We didn't get a confirmation — your complaint may already have been saved. Check the complaints list before entering it again.",
    duplicateNotice: "This complaint was already saved — showing the existing record.",
    successHeading: "Complaint saved",
    successHeadingDuplicate: "Complaint already logged",
    successNumberLabel: "Complaint number",
    copyComplaintNumber: "Copy complaint number",
    copiedConfirmation: "Copied!",
    checkTheListUnavailable: "The complaints list isn't available yet.",
    browserNotSupported:
      "Your browser doesn't support a required security feature. Please use an up-to-date browser.",
    sessionExpiredRedirect: "Your session has expired. Redirecting you to log in…",
    mustChangePasswordRedirect: "You must change your password before continuing. Redirecting…",
  },
  lookup: {
    heading: "Check complaint status",
    inputLabel: "Complaint number",
    checkStatus: "Check status",
    checking: "Checking…",
    preparing: "Preparing…",
    retryPreparing: "Taking longer than expected. Retry",
    unavailablePreparing: "Unavailable — reload the page",
    cookiesDisabled:
      "This page needs cookies enabled to check your complaint status. Please enable cookies in your browser and reload the page.",
    inputHint: "e.g. 4T9K-M2XQ8",
    invalidInput: "Enter a valid complaint number",
    notFound:
      "We couldn't find a complaint with that number. Please check the number and try again, or contact the panchayat office.",
    rateLimited: "Too many attempts from this network. Please wait a minute and try again.",
    rateLimitedPrefix: "Try again in ",
    rateLimitedSuffix: "s.",
    unavailable: "The service is temporarily unavailable. Please try again in a few minutes.",
    successHeading: "Complaint found",
    complaintNumberLabel: "Complaint number",
    dateLoggedLabel: "Date logged",
    copyComplaintNumber: "Copy complaint number",
    copiedConfirmation: "Copied!",
    checkAnother: "Check another complaint",
    noscript:
      "This page requires JavaScript to check your complaint status. Please contact the panchayat office for help.",
    /** ADR-013/api-contract.md §4 — the fixed, enumerated citizen-facing
     * sentence per `public_update` code. Never render the raw code or the
     * clerk's free-text note. */
    publicUpdateMessages: {
      received: "We've received your complaint.",
      in_progress: "Your complaint is being worked on.",
      resolved: "Your complaint has been resolved.",
      not_accepted: "Your complaint was not accepted.",
      closed: "Your complaint is closed.",
    },
  },
} as const;

export type Strings = typeof S;
