const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/v1";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("outlawer-token");
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem("outlawer-token", token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("outlawer-token");
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = new Headers(init?.headers || {});
  headers.set("Content-Type", headers.get("Content-Type") || "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  const payload = await response.json();
  if (!response.ok || payload.code !== 0) {
    throw new Error(payload.detail || payload.message || "Request failed");
  }
  return payload.data as T;
}

export async function apiFormFetch<T>(path: string, formData: FormData): Promise<T> {
  const token = getToken();
  const headers = new Headers();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });
  const payload = await response.json();
  if (!response.ok || payload.code !== 0) {
    throw new Error(payload.detail || payload.message || "Request failed");
  }
  return payload.data as T;
}
