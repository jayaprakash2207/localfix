import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import Register from "../../src/pages/Register";
import { ApiError, apiPost } from "../../src/api/client";

vi.mock("../../src/api/client", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/client")>(
    "../../src/api/client",
  );
  return { ...actual, apiPost: vi.fn() };
});

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderRegister() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Register page", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it("navigates to login on valid submit", async () => {
    vi.mocked(apiPost).mockResolvedValue({
      id: "1",
      email: "alice@example.com",
      role: "citizen",
      status: "active",
      created_at: "2026-01-01T00:00:00Z",
    });
    renderRegister();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/password/i), "Str0ngP@ssw0rd!");
    await user.click(screen.getByRole("button", { name: /register/i }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/login"));
  });

  it("shows a duplicate-email error distinctly from a password-policy error", async () => {
    vi.mocked(apiPost).mockRejectedValue(new ApiError(409, "email_already_registered"));
    renderRegister();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/password/i), "Str0ngP@ssw0rd!");
    await user.click(screen.getByRole("button", { name: /register/i }));

    await screen.findByText(/already registered/i);
  });

  it("shows a password-length-policy error distinctly from a duplicate-email error", async () => {
    vi.mocked(apiPost).mockRejectedValue(new ApiError(422, "error"));
    renderRegister();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/email/i), "bob@example.com");
    await user.type(screen.getByLabelText(/password/i), "short");
    await user.click(screen.getByRole("button", { name: /register/i }));

    await screen.findByText(/8 and 128 characters/i);
  });

  it("shows a specific 'too many attempts' message on a 429 response", async () => {
    vi.mocked(apiPost).mockRejectedValue(new ApiError(429, "rate_limit_exceeded"));
    renderRegister();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/email/i), "carol@example.com");
    await user.type(screen.getByLabelText(/password/i), "Str0ngP@ssw0rd!");
    await user.click(screen.getByRole("button", { name: /register/i }));

    await screen.findByText(/too many attempts/i);
  });
});
