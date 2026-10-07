import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { useAuth } from "../auth/AuthContext";
import { apiPost } from "../api/client";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const { currentUser, clearUser } = useAuth();
  const navigate = useNavigate();

  const logoutMutation = useMutation({
    mutationFn: () => apiPost<void>("/auth/logout"),
    onSuccess: () => {
      clearUser();
      navigate("/login");
    },
  });

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 px-4 py-3">
        <nav className="flex flex-wrap items-center gap-4 text-sm">
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/profile">Profile</Link>
          {currentUser?.role === "admin" && (
            <>
              <Link to="/admin/users">Users</Link>
              <Link to="/admin/audit-log">Audit Log</Link>
            </>
          )}
        </nav>
        <div className="flex flex-wrap items-center gap-3">
          {currentUser && <span className="text-sm text-gray-500 break-all">{currentUser.email}</span>}
          <button
            type="button"
            onClick={() => logoutMutation.mutate()}
            disabled={logoutMutation.isPending}
            className="rounded border border-gray-300 px-2 py-1 text-sm disabled:opacity-50"
          >
            Log out
          </button>
        </div>
      </header>
      <main className="flex-1 p-4">{children}</main>
    </div>
  );
}
