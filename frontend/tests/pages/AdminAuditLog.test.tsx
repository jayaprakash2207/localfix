import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import AdminAuditLog from "../../src/pages/admin/AuditLog";
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
        <AdminAuditLog />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const SAMPLE_ENTRY = {
  items: [
    {
      id: "r1",
      actor_user_id: "u1",
      action: "LOGIN_SUCCESS",
      affected_user_id: "u1",
      occurred_at: "2026-01-01T00:00:00Z",
      detail: null,
    },
  ],
};

describe("Admin Audit Log page", () => {
  it("renders entries with actor/action/affected-user/timestamp", async () => {
    vi.mocked(apiGet).mockResolvedValue(SAMPLE_ENTRY);
    renderPage();

    await screen.findByText("LOGIN_SUCCESS");
    expect(screen.getAllByText("u1").length).toBeGreaterThan(0);
  });

  it("supports filtering by affected user, action type, and time range", async () => {
    vi.mocked(apiGet).mockResolvedValue(SAMPLE_ENTRY);
    renderPage();
    await screen.findByText("LOGIN_SUCCESS");

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/affected user/i), "alice@example.com");
    await user.type(screen.getByLabelText(/action/i), "LOGIN_SUCCESS");
    await user.type(screen.getByLabelText(/^since$/i), "2026-01-01T00:00");
    await user.type(screen.getByLabelText(/^until$/i), "2026-01-02T00:00");

    expect(screen.getByLabelText(/affected user/i)).toHaveValue("alice@example.com");
    expect(screen.getByLabelText(/action/i)).toHaveValue("LOGIN_SUCCESS");
  });

  it("resolves the affected-user filter by email before querying the audit log", async () => {
    vi.mocked(apiGet).mockImplementation((path: string) => {
      if (path.startsWith("/admin/users")) {
        return Promise.resolve({
          items: [
            {
              id: "u1",
              email: "alice@example.com",
              role: "citizen",
              status: "active",
              created_at: "2026-01-01T00:00:00Z",
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        });
      }
      return Promise.resolve(SAMPLE_ENTRY);
    });
    renderPage();
    await screen.findByText("LOGIN_SUCCESS");

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/affected user/i), "alice@example.com");

    await waitFor(() => {
      const calls = vi.mocked(apiGet).mock.calls.map(([p]) => p as string);
      expect(calls.some((p) => p.includes("user_id=u1"))).toBe(true);
    });
  });

  it("shows an empty state when no user matches the affected-user email filter", async () => {
    vi.mocked(apiGet).mockImplementation((path: string) => {
      if (path.startsWith("/admin/users")) {
        return Promise.resolve({ items: [], total: 0, page: 1, page_size: 20 });
      }
      return Promise.resolve(SAMPLE_ENTRY);
    });
    renderPage();
    await screen.findByText("LOGIN_SUCCESS");

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/affected user/i), "nobody@example.com");

    await screen.findByText(/nothing to show/i);
  });

  it("shows an explicit not-permitted message on a 403 response", async () => {
    vi.mocked(apiGet).mockImplementation(() =>
      Promise.reject(new ApiError(403, "forbidden")),
    );
    renderPage();

    await screen.findByText(/don't have permission/i);
  });
});
