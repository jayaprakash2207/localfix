import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { apiPost, ApiError } from "../api/client";

interface UserPublic {
  id: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

export default function Register() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const mutation = useMutation({
    mutationFn: () => apiPost<UserPublic>("/auth/register", { email, password }),
    onSuccess: () => navigate("/login"),
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.reset();
    mutation.mutate();
  }

  let errorMessage: string | null = null;
  if (mutation.isError && mutation.error instanceof ApiError) {
    if (mutation.error.status === 409) {
      errorMessage = "That email is already registered.";
    } else if (mutation.error.status === 422) {
      errorMessage = "Password must be between 8 and 128 characters.";
    } else if (mutation.error.status === 429) {
      errorMessage = "Too many attempts. Please try again later.";
    } else {
      errorMessage = "Something went wrong. Please try again.";
    }
  } else if (mutation.isError) {
    errorMessage = "Something went wrong. Please try again.";
  }

  return (
    <div className="mx-auto max-w-sm p-6">
      <h1 className="mb-4 text-xl font-semibold">Register</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label htmlFor="register-email" className="text-sm font-medium">
          Email
        </label>
        <input
          id="register-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="rounded border border-gray-300 px-2 py-1"
        />

        <label htmlFor="register-password" className="text-sm font-medium">
          Password
        </label>
        <input
          id="register-password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
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
          Register
        </button>
      </form>
      <p className="mt-4 text-sm">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
