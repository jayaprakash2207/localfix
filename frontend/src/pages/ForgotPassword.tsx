import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { apiPost, ApiError } from "../api/client";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");

  const mutation = useMutation({
    mutationFn: () => apiPost<{ message: string }>("/auth/password-reset/request", { email }),
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.reset();
    mutation.mutate();
  }

  const isRateLimited =
    mutation.isError && mutation.error instanceof ApiError && mutation.error.status === 429;

  return (
    <div className="mx-auto max-w-sm p-6">
      <h1 className="mb-4 text-xl font-semibold">Forgot password</h1>

      {mutation.isSuccess && !isRateLimited ? (
        <p>If that email is registered, a reset link has been sent.</p>
      ) : isRateLimited ? (
        <p role="alert" className="text-sm text-red-600">
          Too many attempts. Please try again later.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label htmlFor="forgot-email" className="text-sm font-medium">
            Email
          </label>
          <input
            id="forgot-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="rounded border border-gray-300 px-2 py-1"
          />
          <button
            type="submit"
            disabled={mutation.isPending}
            className="mt-2 rounded bg-blue-600 px-3 py-2 text-white disabled:opacity-50"
          >
            Send reset link
          </button>
        </form>
      )}

      <p className="mt-4 text-sm">
        <Link to="/login">Back to log in</Link>
      </p>
    </div>
  );
}
