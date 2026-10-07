/**
 * Auth-context layer (Feature 002 SEC-001): holds only the current user and an
 * isAuthenticated flag - never a raw session token, since the browser-based login flow never
 * hands one to frontend JavaScript at all (POST /auth/session returns {expires_at} only).
 */

import { createContext, useContext, useEffect, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiGet, onUnauthorized } from "../api/client";

export type Role = "citizen" | "officer" | "admin";
export type AccountStatus = "active" | "disabled";

export interface CurrentUser {
  id: string;
  email: string;
  role: Role;
  status: AccountStatus;
  created_at: string;
}

interface AuthContextValue {
  currentUser: CurrentUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  refetchUser: () => void;
  clearUser: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const CURRENT_USER_QUERY_KEY = ["currentUser"] as const;

async function fetchCurrentUser(): Promise<CurrentUser | null> {
  try {
    return await apiGet<CurrentUser>("/users/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      // Not logged in - a normal, expected state, not a query error.
      return null;
    }
    throw error;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: CURRENT_USER_QUERY_KEY,
    queryFn: fetchCurrentUser,
    retry: false,
  });

  useEffect(
    () =>
      onUnauthorized(() => {
        queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null);
      }),
    [queryClient],
  );

  const value: AuthContextValue = {
    currentUser: data ?? null,
    isAuthenticated: Boolean(data),
    isLoading,
    refetchUser: () => void refetch(),
    clearUser: () => queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
