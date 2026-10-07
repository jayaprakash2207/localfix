import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiGet, ApiError } from "../../api/client";
import LoadingState from "../../components/LoadingState";
import ErrorState from "../../components/ErrorState";
import EmptyState from "../../components/EmptyState";

interface AuditRecord {
  id: string;
  actor_user_id: string | null;
  action: string;
  affected_user_id: string;
  occurred_at: string;
  detail: Record<string, unknown> | null;
}

interface AuditLogResponse {
  items: AuditRecord[];
}

interface UserListResponse {
  items: { id: string }[];
}

export default function AdminAuditLog() {
  const [affectedUser, setAffectedUser] = useState("");
  const [action, setAction] = useState("");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["admin-audit-log", affectedUser, action, since, until],
    queryFn: async () => {
      const params = new URLSearchParams();

      // Feature 002 T086: an Admin identifies a user by email, not the raw UUID the
      // audit-log endpoint actually filters on - resolve it via the existing user-search
      // endpoint before querying, rather than requiring the Admin to already know the id.
      if (affectedUser) {
        const matches = await apiGet<UserListResponse>(
          `/admin/users?search=${encodeURIComponent(affectedUser)}&page_size=1`,
        );
        const matchedId = matches.items[0]?.id;
        if (!matchedId) {
          return { items: [] } as AuditLogResponse;
        }
        params.set("user_id", matchedId);
      }
      if (action) params.set("action", action);
      if (since) params.set("since", since);
      if (until) params.set("until", until);
      const query = params.toString();
      return apiGet<AuditLogResponse>(`/admin/audit-log${query ? `?${query}` : ""}`);
    },
    retry: false,
  });

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-4 text-xl font-semibold">Audit Log</h1>

      <div className="mb-4 flex flex-wrap gap-3">
        <label htmlFor="audit-affected-user" className="flex flex-col text-xs">
          Affected user
          <input
            id="audit-affected-user"
            type="email"
            placeholder="user@example.com"
            value={affectedUser}
            onChange={(e) => setAffectedUser(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </label>
        <label htmlFor="audit-action" className="flex flex-col text-xs">
          Action
          <input
            id="audit-action"
            value={action}
            onChange={(e) => setAction(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </label>
        <label htmlFor="audit-since" className="flex flex-col text-xs">
          Since
          <input
            id="audit-since"
            type="datetime-local"
            value={since}
            onChange={(e) => setSince(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </label>
        <label htmlFor="audit-until" className="flex flex-col text-xs">
          Until
          <input
            id="audit-until"
            type="datetime-local"
            value={until}
            onChange={(e) => setUntil(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </label>
      </div>

      {isLoading ? (
        <LoadingState />
      ) : error instanceof ApiError && error.status === 403 ? (
        <ErrorState message="You don't have permission for this." />
      ) : isError || !data ? (
        <ErrorState onRetry={() => void refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState message="Nothing to show yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr>
                <th className="pb-2">Actor</th>
                <th className="pb-2">Action</th>
                <th className="pb-2">Affected user</th>
                <th className="pb-2">Occurred at</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((record) => (
                <tr key={record.id} className="border-t border-gray-100">
                  <td className="py-2">{record.actor_user_id ?? "-"}</td>
                  <td className="py-2">{record.action}</td>
                  <td className="py-2">{record.affected_user_id}</td>
                  <td className="py-2">{new Date(record.occurred_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
