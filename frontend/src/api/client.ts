/**
 * Typed fetch wrapper for the LocalFix API (Feature 002 FE-018/FE-019/FE-020).
 *
 * - Always sends `credentials: "include"` so the HttpOnly session cookie is attached.
 * - Automatically attaches `X-CSRF-Token` (read from the non-HttpOnly `csrf_token` cookie) on
 *   every mutating request - no per-call-site code needed (Feature 002 BE-005/FE-021).
 * - Normalizes every non-2xx response into an `ApiError` with a `status` and the backend's
 *   `error` code, so callers can switch on it consistently instead of re-parsing bodies.
 * - On 401, notifies any registered "unauthorized" listener (the auth context subscribes to
 *   this to clear local state and redirect to login) before throwing.
 */

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string) {
    super(code);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

type Listener = () => void;

const unauthorizedListeners = new Set<Listener>();

export function onUnauthorized(listener: Listener): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

function getCookie(name: string): string | null {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

const CSRF_COOKIE_NAME = "csrf_token";
const CSRF_HEADER_NAME = "X-CSRF-Token";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);

  if (!SAFE_METHODS.has(method)) {
    const csrfToken = getCookie(CSRF_COOKIE_NAME);
    if (csrfToken) {
      headers.set(CSRF_HEADER_NAME, csrfToken);
    }
  }

  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`/api${path}`, {
    ...init,
    method,
    headers,
    credentials: "include",
  });

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // No JSON body (e.g. a 204) - fine, leave body as null.
  }

  if (response.status === 401) {
    for (const listener of unauthorizedListeners) listener();
    throw new ApiError(401, errorCodeOf(body));
  }

  if (!response.ok) {
    throw new ApiError(response.status, errorCodeOf(body));
  }

  return body as T;
}

function errorCodeOf(body: unknown): string {
  if (body && typeof body === "object" && "error" in body && typeof (body as { error: unknown }).error === "string") {
    return (body as { error: string }).error;
  }
  return "error";
}

export function apiGet<T>(path: string): Promise<T> {
  return apiFetch<T>(path);
}

export function apiPost<T>(path: string, data?: unknown): Promise<T> {
  return apiFetch<T>(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });
}

export function apiPatch<T>(path: string, data?: unknown): Promise<T> {
  return apiFetch<T>(path, { method: "PATCH", body: data === undefined ? undefined : JSON.stringify(data) });
}
