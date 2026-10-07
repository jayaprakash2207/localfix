import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import ResetPassword from "../../src/pages/ResetPassword";
import { apiPost, ApiError } from "../../src/api/client";

vi.mock("../../src/api/client", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/client")>(
    "../../src/api/client",
  );
  return { ...actual, apiPost: vi.fn() };
});

function renderPage(search: string) {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/reset-password${search}`]}>
        <ResetPassword />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Reset Password page", () => {
  it("reads the token from the URL and submits a new password", async () => {
    vi.mocked(apiPost).mockResolvedValue({ message: "Password updated." });
    renderPage("?token=abc123");
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/new password/i), "NewStr0ngP@ss!");
    await user.click(screen.getByRole("button", { name: /reset password/i }));

    await screen.findByText(/password updated/i);
    expect(apiPost).toHaveBeenCalledWith("/auth/password-reset/confirm", {
      token: "abc123",
      new_password: "NewStr0ngP@ss!",
    });
  });

  it("shows a specific error for an expired or used token", async () => {
    vi.mocked(apiPost).mockImplementation(() =>
      Promise.reject(new ApiError(400, "invalid_reset_token")),
    );
    renderPage("?token=expired-token");
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/new password/i), "NewStr0ngP@ss!");
    await user.click(screen.getByRole("button", { name: /reset password/i }));

    await screen.findByText(/link is invalid or has expired/i);
  });

  it("shows a distinct error for a password-policy violation, not the invalid-token message", async () => {
    vi.mocked(apiPost).mockImplementation(() => Promise.reject(new ApiError(422, "error")));
    renderPage("?token=abc123");
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/new password/i), "NewStr0ngP@ss!");
    await user.click(screen.getByRole("button", { name: /reset password/i }));

    await screen.findByText(/8 and 128 characters/i);
    expect(screen.queryByText(/link is invalid or has expired/i)).not.toBeInTheDocument();
  });
});
