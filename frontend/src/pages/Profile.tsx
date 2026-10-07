import { useQuery } from "@tanstack/react-query";

import { apiGet } from "../api/client";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import type { CurrentUser } from "../auth/AuthContext";

export default function Profile() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["profile"],
    queryFn: () => apiGet<CurrentUser>("/users/me"),
  });

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState onRetry={() => void refetch()} />;

  return (
    <div className="mx-auto max-w-md p-6">
      <h1 className="mb-4 text-xl font-semibold">Profile</h1>
      <dl className="flex flex-col gap-2 text-sm">
        <div>
          <dt className="font-medium">Email</dt>
          <dd>{data.email}</dd>
        </div>
        <div>
          <dt className="font-medium">Role</dt>
          <dd>{data.role}</dd>
        </div>
        <div>
          <dt className="font-medium">Status</dt>
          <dd>{data.status}</dd>
        </div>
        <div>
          <dt className="font-medium">Member since</dt>
          <dd>{new Date(data.created_at).toLocaleDateString()}</dd>
        </div>
      </dl>
    </div>
  );
}
