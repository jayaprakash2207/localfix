import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import AdminUsers from "../../src/pages/admin/Users";
import { apiGet, apiPatch, ApiError } from "../../src/api/client";

vi.mock("../../src/api/client", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/client")>(
    "../../src/api/client",
  );
  return { ...actual, apiGet: vi.fn(), apiPatch: vi.fn() };
});

const baseList = {
  items: [
    {
      id: "1",
      email: "alice@example.com",
      role: "citizen",
      status: "active",
      created_at: "2026-01-01T00:00:00Z",
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
};

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

describe("Admin Users page actions", () => {
  beforeEach(() => {
    vi.mocked(apiGet).mockReset();
    vi.mocked(apiPatch).mockReset();
    vi.mocked(apiGet).mockResolvedValue(baseList);
  });

  it("changing a user's role succeeds and the updated value is reflected immediately", async () => {
    vi.mocked(apiPatch).mockResolvedValue({ id: "1", role: "officer" });
    renderPage();
    await screen.findByText("alice@example.com");

    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText(/role for alice@example.com/i), "officer");

    await waitFor(() =>
      expect(apiPatch).toHaveBeenCalledWith("/admin/users/1/role", { role: "officer" }),
    );
  });

  it("changing a user's status succeeds and the updated value is reflected immediately", async () => {
    vi.mocked(apiPatch).mockResolvedValue({ id: "1", status: "disabled" });
    renderPage();
    await screen.findByText("alice@example.com");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /disable/i }));

    await waitFor(() =>
      expect(apiPatch).toHaveBeenCalledWith("/admin/users/1/status", { status: "disabled" }),
    );
  });

  it("displays the specific backend-provided reason for a last-admin-violating attempt", async () => {
    vi.mocked(apiPatch).mockRejectedValue(new ApiError(409, "last_admin_invariant"));
    renderPage();
    await screen.findByText("alice@example.com");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /disable/i }));

    await screen.findByText(/last_admin_invariant/i);
  });

  it("displays the specific backend-provided reason for a self-targeted attempt", async () => {
    vi.mocked(apiPatch).mockRejectedValue(new ApiError(403, "self_status_change_not_allowed"));
    renderPage();
    await screen.findByText("alice@example.com");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /disable/i }));

    await screen.findByText(/self_status_change_not_allowed/i);
  });
});
