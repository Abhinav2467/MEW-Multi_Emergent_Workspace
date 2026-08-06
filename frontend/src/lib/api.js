/**
 * Central API base URL helper.
 *
 * In production (Vercel), NEXT_PUBLIC_API_URL is set to the Railway backend URL.
 * In local dev, it falls back to http://127.0.0.1:8000.
 */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

/**
 * Convenience wrapper around fetch that prepends API_BASE and attaches
 * the JWT auth token from localStorage (if present).
 */
export async function apiFetch(path, options = {}) {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("mew_access_token")
      : null;

  const headers = {
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  return fetch(`${API_BASE}${path}`, { ...options, headers });
}
