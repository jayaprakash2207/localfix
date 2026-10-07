import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import Profile from "../../src/pages/Profile";
import { apiGet } from "../../src/api/client";

vi.mock("../../src/api/client", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/client")>(
    "../../src/api/client",
  );
  return { ...actual, apiGet: vi.fn() };
});

function renderProfile() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Profile />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Profile page", () => {
  beforeEach(() => {
    vi.mocked(apiGet).mockResolvedValue({
      id: "1",
      email: "alice@example.com",
      role: "citizen",
      status: "active",
      created_at: "2026-01-01T00:00:00Z",
    });
  });

  it("renders the current user's own email, role, status, and created_at", async () => {
    renderProfile();

    await screen.findByText("alice@example.com");
    expect(screen.getByText(/citizen/i)).toBeInTheDocument();
    expect(screen.getByText(/active/i)).toBeInTheDocument();
  });
});
