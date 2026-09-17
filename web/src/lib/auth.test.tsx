import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "@/lib/auth";
import { S } from "@/strings/en";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: replaceMock }),
}));

const apiGetMock = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    apiGet: (...args: unknown[]) => apiGetMock(...args),
  };
});

function Child() {
  const { username, isAdminClerk } = useAuth();
  return (
    <div>
      username: {username}, isAdminClerk: {String(isAdminClerk)}
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    replaceMock.mockReset();
    apiGetMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("redirects an anonymous session to /login without rendering children", async () => {
    apiGetMock.mockResolvedValue({ authenticated: false });

    render(
      <AuthProvider>
        <Child />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });
    expect(screen.queryByText(/username:/)).toBeNull();
  });

  it("redirects a must_change_password session to /change-password without rendering children", async () => {
    apiGetMock.mockResolvedValue({
      authenticated: true,
      csrf_token: "csrf-1",
      user: { id: 1, username: "clerk1", is_admin_clerk: false, must_change_password: true },
    });

    render(
      <AuthProvider>
        <Child />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/change-password");
    });
    expect(screen.queryByText(/username:/)).toBeNull();
  });

  it("renders children with the session's identity when authenticated", async () => {
    apiGetMock.mockResolvedValue({
      authenticated: true,
      csrf_token: "csrf-2",
      user: { id: 1, username: "clerk1", is_admin_clerk: true, must_change_password: false },
    });

    render(
      <AuthProvider>
        <Child />
      </AuthProvider>,
    );

    await screen.findByText("username: clerk1, isAdminClerk: true");
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("fails safe to /login when the session check errors", async () => {
    apiGetMock.mockRejectedValue(new Error("network down"));

    render(
      <AuthProvider>
        <Child />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });
    expect(screen.queryByText(/username:/)).toBeNull();
  });

  it("shows a checking-session status while the check is in flight", () => {
    apiGetMock.mockReturnValue(new Promise(() => {}));

    render(
      <AuthProvider>
        <Child />
      </AuthProvider>,
    );

    expect(screen.getByText(S.common.checkingSession)).not.toBeNull();
  });
});
