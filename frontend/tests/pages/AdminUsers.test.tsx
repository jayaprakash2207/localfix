import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import AdminUsers from "../../src/pages/admin/Users";
import { apiGet, ApiError } from "../../src/api/client";

vi.mock("../../src/api/client", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/client")>(
    "../../src/api/client",
  );
  return { ...actual, apiGet: vi.fn() };
});

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminUsers />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Admin Users page", () => {
  it("renders a result row per item", async () => {
    vi.mocked(apiGet).mockResolvedValue({
      items: [
        { id: "1", email: "alice@example.com", role: "citizen", status: "active", created_at: "2026-01-01T00:00:00Z" },
        { id: "2", email: "bob@example.com", role: "officer", status: "active", created_at: "2026-01-02T00:00:00Z" },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    });
    renderPage();

    await screen.findByText("alice@example.com");
    expect(screen.getByText("bob@example.com")).toBeInTheDocument();
  });

  it("shows the empty state on no matches", async () => {
    vi.mocked(apiGet).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    renderPage();

    await screen.findByText(/nothing to show/i);
  });

  it("shows pagination controls reflecting total/page/page_size", async () => {
    vi.mocked(apiGet).mockResolvedValue({
      items: [
        { id: "1", email: "alice@example.com", role: "citizen", status: "active", created_at: "2026-01-01T00:00:00Z" },
      ],
      total: 45,
      page: 2,
      page_size: 20,
    });
    renderPage();

    await screen.findByText(/page 2 of 3/i);
  });

  it("shows an explicit not-permitted message on a 403 response", async () => {
    vi.mocked(apiGet).mockImplementation(() =>
      Promise.reject(new ApiError(403, "forbidden")),
    );
    renderPage();

    await screen.findByText(/don't have permission/i);
  });
});
