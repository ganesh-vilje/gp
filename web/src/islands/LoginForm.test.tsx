import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LoginForm } from "@/islands/LoginForm";
import { ApiError } from "@/lib/api";
import { S } from "@/strings/en";

const pushMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
  useSearchParams: () => new URLSearchParams(),
}));

const apiPostMock = vi.fn();
const apiGetMock = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    apiPost: (...args: unknown[]) => apiPostMock(...args),
    apiGet: (...args: unknown[]) => apiGetMock(...args),
  };
});

describe("LoginForm", () => {
  beforeEach(() => {
    apiPostMock.mockReset();
    pushMock.mockReset();
    replaceMock.mockReset();
    apiGetMock.mockReset();
    // Default: anonymous session, so the form renders in every existing test.
    apiGetMock.mockResolvedValue({ authenticated: false, csrf_token: "csrf-anon" });
  });

  afterEach(() => {
    cleanup();
  });

  // TC-COMP-004: submit with fields empty — native required/aria-required
  // block submission; no request fired.
  it("blocks submission and fires no request when fields are empty", async () => {
    render(<LoginForm />);

    const usernameInput = (await screen.findByLabelText(S.login.usernameLabel)) as HTMLInputElement;
    const passwordInput = screen.getByLabelText(S.login.passwordLabel) as HTMLInputElement;

    expect(usernameInput.required).toBe(true);
    expect(usernameInput.getAttribute("aria-required")).toBe("true");
    expect(passwordInput.required).toBe(true);
    expect(passwordInput.getAttribute("aria-required")).toBe("true");

    const form = usernameInput.closest("form") as HTMLFormElement;
    expect(form.checkValidity()).toBe(false);

    // Submitting via a real click on the submit button (rather than firing a
    // synthetic "submit" event directly) exercises jsdom's native
    // constraint-validation blocking, matching real-browser behaviour.
    const submitButton = screen.getByRole("button", { name: S.login.submit });
    fireEvent.click(submitButton);

    expect(apiPostMock).not.toHaveBeenCalled();
  });

  // TC-COMP-005: mocked 401 response on submit — generic message shown,
  // password field cleared and focused.
  it("shows a generic error and clears+focuses password on a 401", async () => {
    apiPostMock.mockRejectedValueOnce(new ApiError({ code: "invalid_credentials", status: 401 }));

    render(<LoginForm />);

    const usernameInput = (await screen.findByLabelText(S.login.usernameLabel)) as HTMLInputElement;
    const passwordInput = screen.getByLabelText(S.login.passwordLabel) as HTMLInputElement;

    fireEvent.change(usernameInput, { target: { value: "clerk1" } });
    fireEvent.change(passwordInput, { target: { value: "wrong-password" } });

    const form = usernameInput.closest("form") as HTMLFormElement;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toBe(S.login.invalidCredentials);
    });

    expect(passwordInput.value).toBe("");
    expect(document.activeElement).toBe(passwordInput);
    expect(pushMock).not.toHaveBeenCalled();
    expect(passwordInput.getAttribute("aria-invalid")).toBe("true");
    expect(passwordInput.getAttribute("aria-describedby")).toBe("login-error");
  });

  // Fix 2: an already-authenticated session redirects to /complaints and the
  // login form is never rendered.
  it("redirects to /complaints without rendering the form when already authenticated", async () => {
    apiGetMock.mockReset();
    apiGetMock.mockResolvedValue({
      authenticated: true,
      csrf_token: "csrf-auth",
      user: { id: 1, username: "clerk1", must_change_password: false },
    });

    render(<LoginForm />);

    await waitFor(() => {
      expect(pushMock).not.toHaveBeenCalled(); // uses router.replace, not push
    });
    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/complaints");
    });

    expect(screen.queryByLabelText(S.login.usernameLabel)).toBeNull();
  });

  // Fix 1: a 429 keeps the submit control disabled for the full countdown
  // window and only re-enables it once the countdown reaches zero.
  it("keeps the submit button disabled and counts down on a 429", async () => {
    apiPostMock.mockRejectedValueOnce(
      new ApiError({ code: "rate_limited", status: 429, retryAfterSeconds: 3 }),
    );

    render(<LoginForm />);

    const usernameInput = (await screen.findByLabelText(S.login.usernameLabel)) as HTMLInputElement;
    const passwordInput = screen.getByLabelText(S.login.passwordLabel) as HTMLInputElement;

    vi.useFakeTimers();
    try {
      fireEvent.change(usernameInput, { target: { value: "clerk1" } });
      fireEvent.change(passwordInput, { target: { value: "some-password" } });

      const form = usernameInput.closest("form") as HTMLFormElement;
      fireEvent.submit(form);

      // Flush the rejected apiPost promise's microtasks without advancing
      // the countdown's setInterval.
      await vi.advanceTimersByTimeAsync(0);
      await vi.advanceTimersByTimeAsync(0);

      let submitButton = screen.getByRole("button", { name: /Try again in 3s\./ });
      expect(submitButton.getAttribute("aria-disabled")).toBe("true");

      await vi.advanceTimersByTimeAsync(1000);
      await vi.advanceTimersByTimeAsync(0);
      submitButton = screen.getByRole("button", { name: /Try again in 2s\./ });
      expect(submitButton.getAttribute("aria-disabled")).toBe("true");

      await vi.advanceTimersByTimeAsync(2000);
      await vi.advanceTimersByTimeAsync(0);
      await vi.advanceTimersByTimeAsync(0);

      submitButton = screen.getByRole("button", { name: S.login.submit });
      expect(submitButton.getAttribute("aria-disabled")).toBe("false");
    } finally {
      vi.useRealTimers();
    }

    // A submission during the countdown must not have fired a second request.
    expect(apiPostMock).toHaveBeenCalledTimes(1);
  });
});
