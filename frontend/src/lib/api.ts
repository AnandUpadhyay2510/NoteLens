/**
 * API client for communicating with the FastAPI backend.
 * All endpoints are proxied through Vite's dev server (/api -> localhost:8001).
 */

const API_URL = "/api/v1";

/**
 * Get the stored JWT token from localStorage.
 */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

/**
 * Store the JWT token in localStorage.
 */
export function setToken(token: string) {
  localStorage.setItem("token", token);
}

/**
 * Remove the JWT token from localStorage.
 */
export function clearToken() {
  localStorage.removeItem("token");
}

/**
 * Fetch wrapper that auto-attaches the Authorization header.
 */
export async function fetchWithAuth(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetch(`${API_URL}${path}`, { ...options, headers });
}
