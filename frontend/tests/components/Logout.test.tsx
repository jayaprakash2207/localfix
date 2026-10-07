import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import AppShell from "../../src/components/AppShell";
import { AuthProvider } from "../../src/auth/AuthContext";
import { apiGet, apiPost } from "../../src/api/client";

vi.mock("../../src/api/client", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/client")>(
    "../../src/api/client",
  );
  return { ...actual, apiGet: vi.fn(), apiPost: vi.fn() };
});

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderShell() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter>
          <AppShell>
            <div>content</div>
          </AppShell>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("Logout action", () => {
  beforeEach(() => {
    vi.mocked(apiGet).mockResolvedValue({
      id: "1",
      email: "alice@example.com",
      role: "citizen",
      status: "active",
      created_at: "2026-01-01T00:00:00Z",
    });
    vi.mocked(apiPost).mockResolvedValue(undefined);
    mockNavigate.mockClear();
  });

  it("clears local auth state and redirects to login", async () => {
    renderShell();
    await screen.findByText("alice@example.com");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /log out/i }));

    await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/auth/logout"));
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("alice@example.com")).not.toBeInTheDocument();
  });
});
