import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LookupIsland } from "@/islands/LookupIsland";
import { ApiError } from "@/lib/api";
import { S } from "@/strings/en";

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

describe("LookupIsland", () => {
  beforeEach(() => {
    apiPostMock.mockReset();
    apiGetMock.mockReset();
    apiGetMock.mockResolvedValue({ authenticated: false, csrf_token: "csrf-anon" });
  });

  afterEach(() => {
    cleanup();
  });

  // TC-COMP-001: blank/whitespace input, submit -> instant client-side
  // error, no network call fired.
  it("blocks submission on blank input with no network call", async () => {
    render(<LookupIsland />);

    const input = (await screen.findByLabelText(S.lookup.inputLabel)) as HTMLInputElement;
    await waitFor(() => {
      expect(screen.getByRole("button", { name: S.lookup.checkStatus })).not.toBeNull();
    });

    fireEvent.change(input, { target: { value: "   " } });
    const form = input.closest("form") as HTMLFormElement;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(screen.getByText(S.lookup.invalidInput).textContent).toBe(S.lookup.invalidInput);
    });
    expect(apiPostMock).not.toHaveBeenCalled();
  });

  // TC-COMP-002: submit a valid number, mocked response never resolves in
  // time (simulated here via the same synthetic "timeout" ApiError src/lib/api.ts
  // itself would throw after its 10s AbortController fires) -> generic
  // network/timeout message rendered, button re-enabled.
  it("shows a timeout message and re-enables the button", async () => {
    apiPostMock.mockRejectedValueOnce(new ApiError({ code: "timeout", status: null }));

    render(<LookupIsland />);

    const input = (await screen.findByLabelText(S.lookup.inputLabel)) as HTMLInputElement;
    await waitFor(() => {
      expect(screen.getByRole("button", { name: S.lookup.checkStatus })).not.toBeNull();
    });

    fireEvent.change(input, { target: { value: "4T9K-M2XQ8" } });
    const form = input.closest("form") as HTMLFormElement;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(screen.getByText(S.errors.network).textContent).toBe(S.errors.network);
    });

    const button = screen.getByRole("button", { name: S.lookup.checkStatus });
    expect(button.getAttribute("aria-disabled")).toBe("false");
  });

  // TC-COMP-003: GET /api/session mocked slow (>4s) -> "Preparing…" label,
  // then an inline "Retry" affordance appears once the 4s threshold passes.
  it("shows Preparing then a retry affordance when the session seed is slow", async () => {
    let resolveSession: (value: { authenticated: false; csrf_token: string }) => void = () => {};
    apiGetMock.mockReset();
    apiGetMock.mockReturnValue(
      new Promise((resolve) => {
        resolveSession = resolve;
      }),
    );

    vi.useFakeTimers();
    try {
      render(<LookupIsland />);

      let button = screen.getByRole("button", { name: S.lookup.preparing });
      expect(button.getAttribute("aria-disabled")).toBe("true");

      await vi.advanceTimersByTimeAsync(4000);
      await vi.advanceTimersByTimeAsync(0);

      expect(screen.getByRole("button", { name: S.lookup.retryPreparing })).not.toBeNull();
      button = screen.getByRole("button", { name: S.lookup.preparing });
      expect(button.getAttribute("aria-disabled")).toBe("true");

      resolveSession({ authenticated: false, csrf_token: "csrf-anon" });
      await vi.advanceTimersByTimeAsync(0);
    } finally {
      vi.useRealTimers();
    }
  });
});
