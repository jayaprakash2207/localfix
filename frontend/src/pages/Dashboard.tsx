import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import BasicDashboard from "../components/BasicDashboard";

export default function Dashboard() {
  const { currentUser } = useAuth();

  if (!currentUser) return null;

  if (currentUser.role === "admin") {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <h1 className="text-xl font-semibold">Welcome, {currentUser.email}</h1>
        <p className="mt-2 text-sm text-gray-600">Signed in as admin.</p>
        <ul className="mt-4 flex flex-col gap-2 text-sm">
          <li>
            <Link to="/admin/users">Manage users</Link>
          </li>
          <li>
            <Link to="/admin/audit-log">View audit log</Link>
          </li>
          <li>
            <Link to="/profile">View your profile</Link>
          </li>
        </ul>
      </div>
    );
  }

  return <BasicDashboard currentUser={currentUser} />;
}
