import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { apiPost, ApiError } from "../api/client";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [newPassword, setNewPassword] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      apiPost<{ message: string }>("/auth/password-reset/confirm", {
        token,
        new_password: newPassword,
      }),
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.reset();
    mutation.mutate();
  }

  let errorMessage: string | null = null;
  if (mutation.isError) {
    errorMessage =
      mutation.error instanceof ApiError && mutation.error.status === 422
        ? "Password must be between 8 and 128 characters."
        : "This reset link is invalid or has expired.";
  }

  return (
    <div className="mx-auto max-w-sm p-6">
      <h1 className="mb-4 text-xl font-semibold">Reset password</h1>

      {mutation.isSuccess ? (
        <p>{mutation.data.message}</p>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label htmlFor="reset-new-password" className="text-sm font-medium">
            New password
          </label>
          <input
            id="reset-new-password"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={8}
            maxLength={128}
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
            Reset password
          </button>
        </form>
      )}

      <p className="mt-4 text-sm">
        <Link to="/login">Back to log in</Link>
      </p>
    </div>
  );
}
