import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { apiPost, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

interface SessionResponse {
  expires_at: string;
}

export default function Login() {
  const navigate = useNavigate();
  const { refetchUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const mutation = useMutation({
    mutationFn: () => apiPost<SessionResponse>("/auth/session", { email, password }),
    onSuccess: () => {
      refetchUser();
      navigate("/dashboard");
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.reset();
    mutation.mutate();
  }

  const errorMessage =
    mutation.isError && mutation.error instanceof ApiError && mutation.error.status === 401
      ? "Invalid email or password."
      : mutation.isError
        ? "Something went wrong. Please try again."
        : null;

  return (
    <div className="mx-auto max-w-sm p-6">
      <h1 className="mb-4 text-xl font-semibold">Log in</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label htmlFor="login-email" className="text-sm font-medium">
          Email
        </label>
        <input
          id="login-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="rounded border border-gray-300 px-2 py-1"
        />

        <label htmlFor="login-password" className="text-sm font-medium">
          Password
        </label>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="rounded border border-gray-300 px-2 py-1"
        />

        {errorMessage && (
          <p role="alert" className="text-sm text-red-600">
            {errorMessage}
          </p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="mt-2 rounded bg-blue-600 px-3 py-2 text-white disabled:opacity-50"
        >
          Log in
        </button>
      </form>
      <p className="mt-4 text-sm">
        No account? <Link to="/register">Register</Link>
      </p>
      <p className="mt-1 text-sm">
        <Link to="/forgot-password">Forgot password?</Link>
      </p>
    </div>
  );
}
