import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="mx-auto max-w-2xl p-8 text-center">
      <h1 className="text-3xl font-bold">LocalFix</h1>
      <p className="mt-2 text-gray-600">Civic services, made simple.</p>
      <div className="mt-6 flex justify-center gap-4">
        <Link to="/login" className="rounded bg-blue-600 px-4 py-2 text-white">
          Log in
        </Link>
        <Link to="/register" className="rounded border border-blue-600 px-4 py-2 text-blue-600">
          Register
        </Link>
      </div>
    </div>
  );
}
