import type { CurrentUser } from "../auth/AuthContext";

interface BasicDashboardProps {
  currentUser: CurrentUser;
}

export default function BasicDashboard({ currentUser }: BasicDashboardProps) {
  return (
    <div className="mx-auto max-w-md p-6">
      <h1 className="mb-4 text-xl font-semibold">Your account</h1>
      <dl className="flex flex-col gap-2 text-sm">
        <div>
          <dt className="font-medium">Email</dt>
          <dd>{currentUser.email}</dd>
        </div>
        <div>
          <dt className="font-medium">Role</dt>
          <dd>{currentUser.role}</dd>
        </div>
        <div>
          <dt className="font-medium">Status</dt>
          <dd>{currentUser.status}</dd>
        </div>
        <div>
          <dt className="font-medium">Member since</dt>
          <dd>{new Date(currentUser.created_at).toLocaleDateString()}</dd>
        </div>
      </dl>
    </div>
  );
}
