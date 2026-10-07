import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import BasicDashboard from "../../src/components/BasicDashboard";
import type { CurrentUser } from "../../src/auth/AuthContext";

const citizen: CurrentUser = {
  id: "1",
  email: "citizen@example.com",
  role: "citizen",
  status: "active",
  created_at: "2026-01-01T00:00:00Z",
};

const officer: CurrentUser = {
  id: "2",
  email: "officer@example.com",
  role: "officer",
  status: "active",
  created_at: "2026-01-02T00:00:00Z",
};

describe("BasicDashboard", () => {
  it("renders an identical structure for a Citizen and an Officer, each showing only their own data", () => {
    const { container: citizenContainer } = render(<BasicDashboard currentUser={citizen} />);
    const citizenHeadings = Array.from(citizenContainer.querySelectorAll("dt")).map(
      (el) => el.textContent,
    );
    citizenContainer.remove();

    const { container: officerContainer } = render(<BasicDashboard currentUser={officer} />);
    const officerHeadings = Array.from(officerContainer.querySelectorAll("dt")).map(
      (el) => el.textContent,
    );

    expect(citizenHeadings).toEqual(officerHeadings);
    expect(screen.getByText("officer@example.com")).toBeInTheDocument();
    expect(screen.queryByText("citizen@example.com")).not.toBeInTheDocument();
  });

  it("shows only the given user's own profile and account information", () => {
    render(<BasicDashboard currentUser={citizen} />);

    expect(screen.getByText("citizen@example.com")).toBeInTheDocument();
    expect(screen.getByText("citizen")).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
  });
});
