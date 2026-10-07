import { describe, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import ForgotPassword from "../../src/pages/ForgotPassword";
import { apiPost, ApiError } from "../../src/api/client";

vi.mock("../../src/api/client", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/client")>(
    "../../src/api/client",
  );
  return { ...actual, apiPost: vi.fn() };
});

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Forgot Password page", () => {
  it("shows the generic confirmation when the email exists", async () => {
    vi.mocked(apiPost).mockResolvedValue({ message: "ok" });
    renderPage();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/email/i), "alice@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    await screen.findByText(/if that email is registered/i);
  });

  it("shows the identical generic confirmation whether or not the email is registered", async () => {
    vi.mocked(apiPost).mockResolvedValue({ message: "ok" });
    renderPage();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/email/i), "nobody@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    await screen.findByText(/if that email is registered/i);
  });

  it("surfaces a distinct message when rate-limited", async () => {
    vi.mocked(apiPost).mockImplementation(() =>
      Promise.reject(new ApiError(429, "rate_limit_exceeded")),
    );
    renderPage();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/email/i), "alice@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    await screen.findByText(/too many attempts/i);
  });
});
