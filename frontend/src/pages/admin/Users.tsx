import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiGet, apiPatch, ApiError } from "../../api/client";
import LoadingState from "../../components/LoadingState";
import ErrorState from "../../components/ErrorState";
import EmptyState from "../../components/EmptyState";
import type { Role, AccountStatus } from "../../auth/AuthContext";

interface UserListItem {
  id: string;
  email: string;
  role: Role;
  status: AccountStatus;
  created_at: string;
}

interface UserListResponse {
  items: UserListItem[];
  total: number;
  page: number;
  page_size: number;
}

const QUERY_KEY = "admin-users";

function UserRow({ item }: { item: UserListItem }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const roleMutation = useMutation({
    mutationFn: (role: string) =>
      apiPatch<{ id: string; role: string }>(`/admin/users/${item.id}/role`, { role }),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.code : "error"),
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) =>
      apiPatch<{ id: string; status: string }>(`/admin/users/${item.id}/status`, { status }),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.code : "error"),
  });

  const nextStatus = item.status === "active" ? "disabled" : "active";

  return (
    <tr className="border-t border-gray-100">
      <td className="py-2">{item.email}</td>
      <td className="py-2">
        <label htmlFor={`role-${item.id}`} className="sr-only">
          Role for {item.email}
        </label>
        <select
          id={`role-${item.id}`}
          aria-label={`Role for ${item.email}`}
          value={item.role}
          onChange={(e) => roleMutation.mutate(e.target.value)}
          className="rounded border border-gray-300 px-1 py-0.5"
        >
          <option value="citizen">Citizen</option>
          <option value="officer">Officer</option>
          <option value="admin">Admin</option>
        </select>
      </td>
      <td className="py-2">{item.status}</td>
      <td className="py-2">{new Date(item.created_at).toLocaleDateString()}</td>
      <td className="py-2">
        <button
          type="button"
          onClick={() => statusMutation.mutate(nextStatus)}
          className="rounded border border-gray-300 px-2 py-1 text-xs"
        >
          {item.status === "active" ? "Disable" : "Enable"}
        </button>
        {error && <p role="alert" className="text-xs text-red-600">{error}</p>}
      </td>
    </tr>
  );
}

export default function AdminUsers() {
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: [QUERY_KEY, search, role, status, page],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page) });
      if (search) params.set("search", search);
      if (role) params.set("role", role);
      if (status) params.set("status", status);
      return apiGet<UserListResponse>(`/admin/users?${params.toString()}`);
    },
    retry: false,
  });

  if (isLoading) return <LoadingState />;
  if (error instanceof ApiError && error.status === 403) {
    return <ErrorState message="You don't have permission for this." />;
  }
  if (isError || !data) return <ErrorState onRetry={() => void refetch()} />;

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-4 text-xl font-semibold">Users</h1>

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          type="text"
          aria-label="Search by email"
          placeholder="Search by email"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
          className="rounded border border-gray-300 px-2 py-1"
        />
        <select
          aria-label="Filter by role"
          value={role}
          onChange={(e) => {
            setPage(1);
            setRole(e.target.value);
          }}
          className="rounded border border-gray-300 px-2 py-1"
        >
          <option value="">All roles</option>
          <option value="citizen">Citizen</option>
          <option value="officer">Officer</option>
          <option value="admin">Admin</option>
        </select>
        <select
          aria-label="Filter by status"
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value);
          }}
          className="rounded border border-gray-300 px-2 py-1"
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="disabled">Disabled</option>
        </select>
      </div>

      {data.items.length === 0 ? (
        <EmptyState message="Nothing to show yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr>
                <th className="pb-2">Email</th>
                <th className="pb-2">Role</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Created</th>
                <th className="pb-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <UserRow key={item.id} item={item} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex items-center gap-3 text-sm">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
          className="rounded border border-gray-300 px-2 py-1 disabled:opacity-50"
        >
          Previous
        </button>
        <span>
          Page {data.page} of {totalPages}
        </span>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => setPage((p) => p + 1)}
          className="rounded border border-gray-300 px-2 py-1 disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
