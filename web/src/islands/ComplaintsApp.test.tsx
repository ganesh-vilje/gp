import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ComplaintsApp } from "@/islands/ComplaintsApp";
import { ApiError } from "@/lib/api";
import { S } from "@/strings/en";

const apiPostMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: replaceMock }),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    apiPost: (...args: unknown[]) => apiPostMock(...args),
  };
});

describe("ComplaintsApp new-complaint form", () => {
  beforeEach(() => {
    apiPostMock.mockReset();
    replaceMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  // TC-COMP-011: native required/aria-required markup is present on every
  // required field.
  it("marks citizen name, phone, and description as required", () => {
    render(<ComplaintsApp />);

    const name = screen.getByLabelText(new RegExp(S.complaints.nameLabel)) as HTMLInputElement;
    const phone = screen.getByLabelText(new RegExp(S.complaints.phoneLabel)) as HTMLInputElement;
    const description = screen.getByLabelText(
      new RegExp(S.complaints.descriptionLabel),
    ) as HTMLTextAreaElement;

    for (const field of [name, phone, description]) {
      expect(field.required).toBe(true);
      expect(field.getAttribute("aria-required")).toBe("true");
    }

    const form = name.closest("form") as HTMLFormElement;
    expect(form.checkValidity()).toBe(false);
  });

  // TC-COMP-011: a real click respects native constraint validation — no
  // request is fired while required fields are empty.
  it("fires no request on a normal click while fields are empty", () => {
    render(<ComplaintsApp />);

    const submitButton = screen.getByRole("button", { name: S.complaints.submit });
    fireEvent.click(submitButton);

    expect(apiPostMock).not.toHaveBeenCalled();
  });

  // TC-COMP-011: on a forced (programmatic) submit that bypasses native
  // constraint validation, a top-of-form error summary lists every invalid
  // field, each item focusing its field, and no network call is fired.
  it("shows a top-of-form error summary on a forced submit with empty fields", () => {
    render(<ComplaintsApp />);

    const name = screen.getByLabelText(new RegExp(S.complaints.nameLabel)) as HTMLInputElement;
    const form = name.closest("form") as HTMLFormElement;

    fireEvent.submit(form);

    expect(apiPostMock).not.toHaveBeenCalled();

    const summary = screen.getByRole("alert");
    expect(summary.textContent).toContain(S.complaints.errorSummaryHeadingManySuffix.trim());

    const nameLink = screen.getByRole("link", { name: new RegExp(S.complaints.requiredName) });
    fireEvent.click(nameLink);
    expect(document.activeElement).toBe(name);
  });

  function fillAndSubmit() {
    const name = screen.getByLabelText(new RegExp(S.complaints.nameLabel)) as HTMLInputElement;
    const phone = screen.getByLabelText(new RegExp(S.complaints.phoneLabel)) as HTMLInputElement;
    const description = screen.getByLabelText(
      new RegExp(S.complaints.descriptionLabel),
    ) as HTMLTextAreaElement;
    fireEvent.change(name, { target: { value: "Asha" } });
    fireEvent.change(phone, { target: { value: "9876543210" } });
    fireEvent.change(description, { target: { value: "Pothole on main road" } });
    const form = name.closest("form") as HTMLFormElement;
    fireEvent.submit(form);
  }

  // Fix 1/3/6: on success, focus moves to a status region announcing the
  // outcome, and the complaint number is shown with a copy control.
  it("announces success, focuses the heading, and offers a copy button", async () => {
    apiPostMock.mockResolvedValueOnce({ complaint_number: "PCT-0001", duplicate: false });
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });

    render(<ComplaintsApp />);
    fillAndSubmit();

    const heading = await screen.findByRole("heading", { name: S.complaints.successHeading });
    expect(document.activeElement).toBe(heading);
    expect(heading.closest('[role="status"]')).not.toBeNull();

    const copyButton = screen.getByRole("button", { name: S.complaints.copyComplaintNumber });
    fireEvent.click(copyButton);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("PCT-0001");
    await screen.findByText(S.complaints.copiedConfirmation);
  });

  // Fix 6: a duplicate result uses a duplicate-specific heading.
  it("shows a duplicate-specific heading when the result is a duplicate", async () => {
    apiPostMock.mockResolvedValueOnce({ complaint_number: "PCT-0002", duplicate: true });

    render(<ComplaintsApp />);
    fillAndSubmit();

    await screen.findByRole("heading", { name: S.complaints.successHeadingDuplicate });
  });

  // Fix 2: the "Check the list" control is disabled, not a dead-looking
  // clickable button, while the list view does not exist yet.
  it("disables the Check the list control during may-be-saved", async () => {
    apiPostMock.mockRejectedValueOnce(new ApiError({ code: "timeout", status: null }));

    render(<ComplaintsApp />);
    fillAndSubmit();

    const checkListButton = await screen.findByRole("button", { name: S.complaints.checkTheList });
    expect((checkListButton as HTMLButtonElement).disabled).toBe(true);
  });

  // Fix 5: fields are locked during may-be-saved so "Try again" cannot
  // silently resubmit edited content under the same client_request_id.
  it("locks fields during the may-be-saved state", async () => {
    apiPostMock.mockRejectedValueOnce(new ApiError({ code: "timeout", status: null }));

    render(<ComplaintsApp />);
    fillAndSubmit();

    const name = (await screen.findByLabelText(
      new RegExp(S.complaints.nameLabel),
    )) as HTMLInputElement;
    expect(name.readOnly).toBe(true);
  });

  // Fix 4: a 401 during submission clears state and redirects to /login.
  it("redirects to /login on a 401 during submission", async () => {
    apiPostMock.mockRejectedValueOnce(new ApiError({ code: "not_authenticated", status: 401 }));

    render(<ComplaintsApp />);
    fillAndSubmit();

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login?expired=1");
    });
  });

  // Fix 4: a must_change_password 403 during submission redirects to
  // /change-password.
  it("redirects to /change-password on a must_change_password 403", async () => {
    apiPostMock.mockRejectedValueOnce(new ApiError({ code: "must_change_password", status: 403 }));

    render(<ComplaintsApp />);
    fillAndSubmit();

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/change-password");
    });
  });
});
