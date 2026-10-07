import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import Login from "../../src/pages/Login";
import { AuthProvider } from "../../src/auth/AuthContext";
import { ApiError, apiGet, apiPost } from "../../src/api/client";

vi.mock("../../src/api/client", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/client")>(
    "../../src/api/client",
  );
  return {
    ...actual,
    apiGet: vi.fn(),
    apiPost: vi.fn(),
  };
});

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderLogin() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("Login page", () => {
  beforeEach(() => {
    vi.mocked(apiGet).mockResolvedValue(null);
    mockNavigate.mockClear();
  });

  it("redirects to the dashboard on valid submit", async () => {
    vi.mocked(apiPost).mockResolvedValue({ expires_at: "2099-01-01T00:00:00Z" });
    renderLogin();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/password/i), "Str0ngP@ssw0rd!");
    await user.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/dashboard"));
  });

  it("shows a generic error message on invalid credentials", async () => {
    vi.mocked(apiPost).mockRejectedValue(new ApiError(401, "invalid_credentials"));
    renderLogin();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /log in/i }));

    await screen.findByText(/invalid email or password/i);
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
